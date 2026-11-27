# SPDX-License-Identifier: AGPL-3.0-or-later
"""HA mirror derivation (``ha_derive``) and its signal hooks, against a real DB (no mocks).

Builds a primary the way the OMG WordPress fleet models one: a guest in the source cluster with a
netbox-guests profile, one interface with its primary IPv4, wordpress / mariadb / valkey instances
with config values, and a netbox-database server on the mariadb instance. Needs netbox-guests and
netbox-database installed (the gate's configuration lists both)."""
import unittest

from dcim.models import Site
from django.apps import apps
from django.core.exceptions import ValidationError
from django.test import TestCase
from extras.models import CustomField, Tag
from ipam.models import IPAddress, Prefix, VLAN
from netaddr import IPNetwork
from tenancy.models import Tenant
from utilities.testing import create_test_device
from virtualization.models import Cluster, ClusterType, VirtualMachine, VMInterface

from ..choices import HAStrategyChoices, MirrorModeChoices, ServiceInstanceStatusChoices
from ..ha_derive import derive_for_vm, derive_mirror, mirror_address
from ..models import (
    CatalogConfigParam, HAMirror, HAMirrorPolicy, ServiceInstance, ServiceInstanceConfigValue,
)
from .utils import make_catalog

NEEDS = unittest.skipUnless(
    apps.is_installed("netbox_guests") and apps.is_installed("netbox_database"),
    "needs netbox-guests and netbox-database installed",
)


def _cluster(name, site):
    ctype, _ = ClusterType.objects.get_or_create(name="PVE", slug="pve")
    return Cluster.objects.create(name=name, type=ctype, scope=site)


class _Fleet(TestCase):
    @classmethod
    def setUpTestData(cls):
        GuestProfile = apps.get_model("netbox_guests", "GuestProfile")
        DatabaseServer = apps.get_model("netbox_database", "DatabaseServer")
        omg = Site.objects.create(name="OMG", slug="omg")
        house = Site.objects.create(name="House", slug="house")
        cls.source = _cluster("omg-proxmox", omg)
        cls.target = _cluster("backup", house)
        cls.host = create_test_device("backup", site=house, cluster=cls.target)
        cls.vlan = VLAN.objects.create(vid=11, name="HA_OMG")
        cls.prefix = Prefix.objects.create(prefix=IPNetwork("198.18.0.0/24"), vlan=cls.vlan)
        cls.tenant = Tenant.objects.create(name="OMG Corporate", slug="omg-corporate")
        cls.tag = Tag.objects.create(name="prod", slug="prod")

        cls.wp = make_catalog("wordpress", ha_strategy=HAStrategyChoices.CONTENT_RSYNC)
        cls.db = make_catalog("mariadb", ha_strategy=HAStrategyChoices.MARIADB_MASTER_MASTER)
        cls.kv = make_catalog("valkey")
        cls.p_root = CatalogConfigParam.objects.create(catalog=cls.wp, key="wordpress_document_root", value_type="string")
        cls.p_slug = CatalogConfigParam.objects.create(
            catalog=cls.wp, key="wordpress_oidc_authentik_slug", value_type="string", mirror_mode=MirrorModeChoices.OMIT)
        cls.p_ssl = CatalogConfigParam.objects.create(
            catalog=cls.wp, key="wordpress_force_ssl_admin", value_type="bool",
            mirror_mode=MirrorModeChoices.FIXED, mirror_value="false")
        cls.p_mem = CatalogConfigParam.objects.create(catalog=cls.wp, key="wordpress_wp_memory_limit", value_type="string")
        cls.p_bind = CatalogConfigParam.objects.create(catalog=cls.db, key="mariadb_bind_address", value_type="string")

        cls.policy = HAMirrorPolicy.objects.create(
            name="omg-wordpress", source_cluster=cls.source, source_name_prefix="prod-wp-",
            mirror_name_prefix="mirror-wp-", vmid_offset=10700, target_cluster=cls.target, target_device=cls.host,
            vlan=cls.vlan, prefix=cls.prefix, gateway="198.18.0.254",
        )
        cls.policy.catalogs.set([cls.wp, cls.db, cls.kv])

        cls.vm = VirtualMachine.objects.create(
            name="prod-wp-chinook", cluster=cls.source, site=omg, status="staged", tenant=cls.tenant,
            vcpus=2, memory=4096, disk=10, custom_field_data={"guest_type": "container"},
        )
        cls.vm.tags.add(cls.tag)
        GuestProfile.objects.create(virtual_machine=cls.vm, guest_type="container", vmid=320, onboot=True,
                                    features=["keyctl", "nesting"], manage_journald=True)
        iface = VMInterface.objects.create(virtual_machine=cls.vm, name="eth0")
        ip = IPAddress.objects.create(address=IPNetwork("203.0.113.20/25"), assigned_object=iface)
        cls.vm.primary_ip4 = ip
        cls.vm.save()

        cls.si_wp = ServiceInstance.objects.create(catalog=cls.wp, parent=cls.vm, hostname="chinook.example")
        cls.si_db = ServiceInstance.objects.create(catalog=cls.db, parent=cls.vm, hostname="chinook.example")
        ServiceInstance.objects.create(catalog=cls.kv, parent=cls.vm, hostname="chinook.example")
        for param, value in ((cls.p_root, "/var/www/chinook.example"), (cls.p_slug, "wp-chinook"),
                             (cls.p_ssl, "true"), (cls.p_mem, "512M")):
            ServiceInstanceConfigValue.objects.create(instance=cls.si_wp, param=param, value=value)
        ServiceInstanceConfigValue.objects.create(instance=cls.si_db, param=cls.p_bind, value="0.0.0.0")
        DatabaseServer.objects.create(name="prod-wp-chinook-mariadb", engine="mariadb", version="11.8.6",
                                      port=3306, listen_address="127.0.0.1", virtual_machine=cls.vm,
                                      service_instance=cls.si_db)

    def mirror(self):
        return VirtualMachine.objects.get(name="mirror-wp-chinook")

    def mirror_instance(self, catalog):
        return ServiceInstance.objects.get(catalog=catalog, parent_object_id=self.mirror().pk)


@NEEDS
class DeriveMirrorTest(_Fleet):
    def test_creates_the_whole_mirror(self):
        done = derive_mirror(self.policy, self.vm)
        self.assertTrue(done)
        m = self.mirror()
        self.assertEqual((m.cluster, m.site.slug, m.device, m.status), (self.target, "house", self.host, "staged"))
        self.assertEqual((m.vcpus, m.memory, m.disk, m.tenant), (2, 4096, 10, self.tenant))
        self.assertEqual(list(m.tags.all()), [self.tag])
        required = CustomField.objects.get_for_model(VirtualMachine).filter(required=True).values_list("name", flat=True)
        self.assertEqual({k: m.custom_field_data.get(k) for k in required},
                         {k: self.vm.custom_field_data.get(k) for k in required})

        profile = apps.get_model("netbox_guests", "GuestProfile").objects.get(virtual_machine=m)
        self.assertEqual((profile.vmid, profile.features, profile.manage_journald, profile.onboot),
                         (11020, ["nesting"], False, True))

        iface = VMInterface.objects.get(virtual_machine=m)
        self.assertEqual((iface.name, iface.mode, iface.untagged_vlan), ("eth0", "access", self.vlan))
        gic = apps.get_model("netbox_guests", "GuestInterfaceConfig").objects.get(interface=iface)
        self.assertEqual(str(gic.gateway), "198.18.0.254")
        self.assertEqual(str(m.primary_ip4.address), "198.18.0.20/24")
        self.assertEqual(m.primary_ip4.assigned_object, iface)

        wp = self.mirror_instance(self.wp)
        self.assertEqual((wp.hostname, wp.status), ("chinook.example", ServiceInstanceStatusChoices.STAGED))
        values = {cv.param.key: cv.value for cv in wp.config_values.all()}
        self.assertEqual(values, {"wordpress_document_root": "/var/www/chinook.example",
                                  "wordpress_force_ssl_admin": "false", "wordpress_wp_memory_limit": "512M"})
        self.assertTrue(HAMirror.objects.filter(mirror=wp, primary=self.si_wp).exists())
        self.assertTrue(HAMirror.objects.filter(mirror=self.mirror_instance(self.db), primary=self.si_db).exists())
        self.assertFalse(HAMirror.objects.filter(primary__catalog=self.kv).exists())
        self.assertTrue(self.mirror_instance(self.kv))

        Server = apps.get_model("netbox_database", "DatabaseServer")
        mserver = Server.objects.get(service_instance=self.mirror_instance(self.db))
        self.assertEqual((mserver.name, mserver.version, mserver.listen_address, mserver.virtual_machine),
                         ("mirror-wp-chinook-mariadb", "11.8.6", "0.0.0.0", m))
        group = apps.get_model("netbox_database", "MariaDBReplication").objects.get(name="wp-chinook-replication")
        self.assertEqual((group.topology, group.sync_mode, group.gtid), ("master-master", "semi-sync", True))
        nodes = {n.server.name: (n.mariadb_server_id, n.role, n.read_only) for n in group.nodes.all()}
        self.assertEqual(nodes, {"prod-wp-chinook-mariadb": (320, "co-primary", False),
                                 "mirror-wp-chinook-mariadb": (11020, "co-primary", True)})

    def test_second_run_writes_nothing(self):
        derive_mirror(self.policy, self.vm)
        self.assertEqual(derive_mirror(self.policy, self.vm), [])
        self.assertEqual(VirtualMachine.objects.filter(name="mirror-wp-chinook").count(), 1)

    def test_syncs_primary_changes_and_keeps_mirror_status(self):
        derive_mirror(self.policy, self.vm)
        m = self.mirror()
        m.status = "active"
        m.save()
        self.vm.vcpus = 4
        self.vm.save()
        ServiceInstanceConfigValue.objects.filter(instance=self.si_wp, param=self.p_mem).update(value="768M")
        ServiceInstanceConfigValue.objects.filter(instance=self.si_wp, param=self.p_root).delete()
        done = derive_mirror(self.policy, VirtualMachine.objects.get(pk=self.vm.pk))
        self.assertTrue(done)
        m = self.mirror()
        self.assertEqual((m.vcpus, m.status), (4, "active"))
        values = {cv.param.key: cv.value for cv in self.mirror_instance(self.wp).config_values.all()}
        self.assertEqual(values, {"wordpress_force_ssl_admin": "false", "wordpress_wp_memory_limit": "768M"})

    def test_keeps_an_existing_mirror_address(self):
        derive_mirror(self.policy, self.vm)
        m = self.mirror()
        ip = IPAddress.objects.create(address=IPNetwork("198.18.0.99/24"),
                                      assigned_object=VMInterface.objects.get(virtual_machine=m))
        m.primary_ip4 = ip
        m.save()
        derive_mirror(self.policy, self.vm)
        self.assertEqual(str(self.mirror().primary_ip4.address), "198.18.0.99/24")

    def test_address_taken_by_another_guest_rolls_back(self):
        other = VirtualMachine.objects.create(name="other", cluster=self.target)
        IPAddress.objects.create(address=IPNetwork("198.18.0.20/24"),
                                 assigned_object=VMInterface.objects.create(virtual_machine=other, name="eth0"))
        with self.assertRaises(ValidationError):
            derive_mirror(self.policy, self.vm)
        self.assertFalse(VirtualMachine.objects.filter(name="mirror-wp-chinook").exists())

    def test_skips_what_it_must_not_mirror(self):
        self.vm.status = "decommissioning"
        self.assertEqual(derive_mirror(self.policy, self.vm), [])
        self.vm.status = "staged"
        self.policy.enabled = False
        self.assertEqual(derive_mirror(self.policy, self.vm), [])
        self.policy.enabled = True
        other = VirtualMachine.objects.create(name="dev-wp-chinook", cluster=self.source, status="staged")
        self.assertEqual(derive_mirror(self.policy, other), [])
        bare = VirtualMachine.objects.create(name="prod-wp-bare", cluster=self.source, status="staged")
        self.assertEqual(derive_mirror(self.policy, bare), [])
        self.assertFalse(VirtualMachine.objects.filter(cluster=self.target, name__startswith="mirror-").exists())

    def test_replication_needs_the_primary_database_server(self):
        apps.get_model("netbox_database", "DatabaseServer").objects.filter(virtual_machine=self.vm).delete()
        done = derive_mirror(self.policy, self.vm)
        self.assertIn(f"skipped replication for {self.si_db}: it has no database server", done)
        self.assertFalse(apps.get_model("netbox_database", "MariaDBReplication").objects.exists())

    def test_derive_for_vm_runs_matching_policies_only(self):
        self.assertTrue(derive_for_vm(self.vm.pk))
        self.assertEqual(derive_for_vm(self.mirror().pk), [])
        self.assertEqual(derive_for_vm(10 ** 9), [])


@NEEDS
class DeriveHookTest(_Fleet):
    def test_a_committed_primary_change_derives_the_mirror(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.vm.vcpus = 3
            self.vm.save()
        self.assertEqual(self.mirror().vcpus, 3)
        with self.captureOnCommitCallbacks(execute=True):
            ServiceInstanceConfigValue.objects.get(instance=self.si_wp, param=self.p_mem).delete()
        self.assertFalse(self.mirror_instance(self.wp).config_values.filter(param=self.p_mem).exists())
        with self.captureOnCommitCallbacks(execute=True):
            ServiceInstanceConfigValue.objects.create(instance=self.si_wp, param=self.p_mem, value="1G")
        self.assertEqual(self.mirror_instance(self.wp).config_values.get(param=self.p_mem).value, "1G")

    def test_a_profile_change_derives_the_mirror(self):
        derive_mirror(self.policy, self.vm)
        profile = apps.get_model("netbox_guests", "GuestProfile").objects.get(virtual_machine=self.vm)
        with self.captureOnCommitCallbacks(execute=True):
            profile.onboot = False
            profile.save()
        self.assertFalse(apps.get_model("netbox_guests", "GuestProfile").objects.get(virtual_machine=self.mirror()).onboot)


class MirrorAddressTest(TestCase):
    def test_keeps_the_host_offset(self):
        prefix = Prefix.objects.create(prefix=IPNetwork("198.18.0.0/24"))
        policy = HAMirrorPolicy(prefix=prefix)
        self.assertEqual(str(mirror_address(policy, IPNetwork("203.0.113.20/25"))), "198.18.0.20/24")
        self.assertEqual(str(mirror_address(policy, IPNetwork("203.0.113.1/25"))), "198.18.0.1/24")

    def test_refuses_an_offset_outside_the_prefix(self):
        policy = HAMirrorPolicy(prefix=Prefix.objects.create(prefix=IPNetwork("198.18.1.0/28")))
        with self.assertRaises(ValidationError):
            mirror_address(policy, IPNetwork("203.0.113.20/25"))


class HAMirrorPolicyModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        site = Site.objects.create(name="S", slug="s")
        cls.a = _cluster("a", site)
        cls.b = _cluster("b", site)
        cls.vlan = VLAN.objects.create(vid=11, name="HA")
        cls.prefix = Prefix.objects.create(prefix=IPNetwork("198.18.0.0/24"), vlan=cls.vlan)

    def policy(self, **kw):
        fields = dict(name="p", source_cluster=self.a, source_name_prefix="prod-", mirror_name_prefix="mirror-",
                      vmid_offset=10700, target_cluster=self.b, vlan=self.vlan, prefix=self.prefix,
                      gateway="198.18.0.254")
        fields.update(kw)
        return HAMirrorPolicy(**fields)

    def test_valid_str_url_and_name_mapping(self):
        p = self.policy()
        p.full_clean()
        p.save()
        self.assertEqual(str(p), "p")
        self.assertIn("/plugins/services/ha-mirror-policies/", p.get_absolute_url())
        vm = VirtualMachine(name="prod-x", cluster=self.a)
        self.assertTrue(p.matches(vm))
        self.assertEqual(p.mirror_name(vm), "mirror-x")
        self.assertFalse(p.matches(VirtualMachine(name="prod-x", cluster=self.b)))

    def test_gateway_outside_prefix(self):
        with self.assertRaises(ValidationError):
            self.policy(gateway="198.18.1.254").full_clean()

    def test_prefix_on_another_vlan(self):
        with self.assertRaises(ValidationError):
            self.policy(vlan=VLAN.objects.create(vid=12, name="DEV")).full_clean()

    def test_mirror_must_differ_from_primary(self):
        with self.assertRaises(ValidationError):
            self.policy(target_cluster=self.a, mirror_name_prefix="prod-").full_clean()


class CatalogConfigParamMirrorModeTest(TestCase):
    def test_default_copy_and_fixed_rules(self):
        cat = make_catalog("wordpress")
        p = CatalogConfigParam(catalog=cat, key="k", value_type="string")
        p.full_clean()
        self.assertEqual(p.mirror_mode, MirrorModeChoices.COPY)
        with self.assertRaises(ValidationError):
            CatalogConfigParam(catalog=cat, key="s", value_type="secret", secret=True,
                               mirror_mode=MirrorModeChoices.FIXED, mirror_value="x").full_clean()
        with self.assertRaises(ValidationError):
            CatalogConfigParam(catalog=cat, key="v", value_type="string", mirror_value="x").full_clean()
        CatalogConfigParam(catalog=cat, key="f", value_type="bool", mirror_mode=MirrorModeChoices.FIXED,
                           mirror_value="false").full_clean()
