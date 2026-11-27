# SPDX-License-Identifier: AGPL-3.0-or-later
"""Derive a primary guest's HA mirror intent from an :class:`HAMirrorPolicy`.

``derive_mirror(policy, vm)`` creates whatever the mirror lacks and syncs what it derives, in one
transaction, and returns one line per write (empty = already in step):

* the mirror ``VirtualMachine`` (created ``staged`` with the primary's role, tenant, platform,
  start-on-boot and the values of any required (legacy) custom fields; cluster, site and host device from the policy; vCPUs, memory and disk kept equal to the
  primary; tags are added, never removed; status is never changed);
* its netbox-guests ``GuestProfile`` (VMID = primary + offset; the guest shape follows the primary;
  host-specific fields — node, pool, storage, OS template, swap, journald management, LXC features
  (``["nesting"]`` at create), sandbox, backup job, credentials — are the mirror's own);
* one interface on the policy VLAN with its ``GuestInterfaceConfig`` gateway and, when the mirror has
  no primary IPv4 yet, the primary's host offset inside the policy prefix as its primary IPv4;
* one ``ServiceInstance`` per primary instance whose catalog the policy names, with config values per
  ``CatalogConfigParam.mirror_mode`` (``copy`` mirrors the primary's stored value, ``omit`` and an
  unset primary value store nothing, ``fixed`` stores ``mirror_value``), and an ``HAMirror`` row for
  each catalog whose ``ha_strategy`` is not none;
* for a MariaDB master-master pair whose primary instance has a netbox-database server: the mirror's
  server, the replication group and both nodes (``mariadb_server_id`` = each guest's VMID).

It never deletes a mirror object other than a config value the rules no longer give, and never
touches the primary. A primary that is not ``staged``/``active``, or lacks a guest profile or primary
IPv4, is skipped. ``derive_for_vm`` runs every enabled policy that matches a guest; the signal hooks
(``signals.py``) call it after each commit that changes a primary.
"""
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from extras.models import CustomField
from ipam.models import IPAddress
from netaddr import IPAddress as NetIP, IPNetwork
from virtualization.choices import VirtualMachineStatusChoices
from virtualization.models import VirtualMachine, VMInterface

from .choices import HAStrategyChoices, MirrorModeChoices, ServiceInstanceStatusChoices
from .models import (
    CatalogConfigParam, HAMirror, HAMirrorPolicy, ServiceInstance, ServiceInstanceConfigValue,
)

DERIVE_STATUSES = (VirtualMachineStatusChoices.STATUS_STAGED, VirtualMachineStatusChoices.STATUS_ACTIVE)
# Kept equal to the primary (operator 2026-09-08: each mirror matches its primary) / set once at create.
VM_SYNC = ("vcpus", "memory", "disk")
VM_CREATE = ("role", "tenant", "platform", "start_on_boot")
# Profile fields kept equal to the primary. Swap, journald management and LXC features stay the
# mirror's own: every existing mirror runs swap 512 and unmanaged journald, and the pipeline token can
# set no feature but nesting at create (a mirror starts with ["nesting"]).
PROFILE_FIELDS = (
    "guest_type", "onboot", "start", "protection", "cpu_units", "unprivileged", "template", "image", "iso",
    "bios", "cpu_type", "sockets", "numa", "agent", "cloud_init", "balloon", "memory_shares",
)


def _create(model, done, **fields):
    obj = model(**fields)
    obj.full_clean()
    obj.save()
    done.append(f"created {model._meta.verbose_name} {obj}")
    return obj


def _sync(obj, done, **fields):
    changed = {k: v for k, v in fields.items() if getattr(obj, k) != v}
    if changed:
        obj.snapshot()
        for k, v in changed.items():
            setattr(obj, k, v)
        obj.full_clean()
        obj.save()
        done.append(f"updated {obj._meta.verbose_name} {obj}: {', '.join(sorted(changed))}")
    return obj


def _vm_ct():
    return ContentType.objects.get_for_model(VirtualMachine)


def mirror_address(policy, primary_ip):
    """The primary's host offset inside the policy prefix: 203.0.113.20/25 → 198.18.0.20/24."""
    source = IPNetwork(str(primary_ip))
    offset = int(source.ip) - int(source.network)
    target = policy.prefix.prefix
    if not 0 < offset < target.size - 1:
        raise ValidationError(f"Host offset {offset} of {source} does not fit {target}.")
    return IPNetwork(f"{NetIP(int(target.network) + offset)}/{target.prefixlen}")


def _mirror_vm(policy, vm, done):
    fields = {k: getattr(vm, k) for k in VM_SYNC}
    fields.update(site=getattr(policy.target_cluster, "_site", None), device=policy.target_device)
    mirror = VirtualMachine.objects.filter(name=policy.mirror_name(vm), cluster=policy.target_cluster).first()
    if mirror is None:
        # A legacy custom field NetBox still requires (netbox-guests' guest_type) is the one
        # custom-field value a mirror takes, from its primary (SOP NetBox Modelling exception).
        required = CustomField.objects.get_for_model(VirtualMachine).filter(required=True).values_list("name", flat=True)
        mirror = _create(VirtualMachine, done, name=policy.mirror_name(vm), cluster=policy.target_cluster,
                         status=VirtualMachineStatusChoices.STATUS_STAGED,
                         custom_field_data={k: vm.custom_field_data.get(k) for k in required},
                         **{k: getattr(vm, k) for k in VM_CREATE}, **fields)
    else:
        _sync(mirror, done, **fields)
    missing = set(vm.tags.all()) - set(mirror.tags.all())
    if missing:
        mirror.snapshot()
        mirror.tags.add(*missing)
        done.append(f"tagged {mirror}: {', '.join(sorted(t.name for t in missing))}")
    return mirror


def _mirror_profile(policy, profile, mirror, done):
    GuestProfile = type(profile)
    names = {f.name for f in GuestProfile._meta.fields}
    fields = {k: getattr(profile, k) for k in PROFILE_FIELDS if k in names}
    fields["vmid"] = profile.vmid + policy.vmid_offset
    mprofile = GuestProfile.objects.filter(virtual_machine=mirror).first()
    if mprofile is None:
        features = ["nesting"] if fields["guest_type"] == "container" else []
        return _create(GuestProfile, done, virtual_machine=mirror, features=features, **fields)
    return _sync(mprofile, done, **fields)


def _mirror_interface(policy, vm, mirror, done):
    GuestInterfaceConfig = apps.get_model("netbox_guests", "GuestInterfaceConfig")
    iface = VMInterface.objects.filter(virtual_machine=mirror, name=policy.interface_name).first()
    if iface is None:
        iface = _create(VMInterface, done, virtual_machine=mirror, name=policy.interface_name, mode="access",
                        untagged_vlan=policy.vlan)
    else:
        _sync(iface, done, mode="access", untagged_vlan=policy.vlan)
    config = GuestInterfaceConfig.objects.filter(interface=iface).first()
    if config is None:
        _create(GuestInterfaceConfig, done, interface=iface, gateway=policy.gateway)
    else:
        _sync(config, done, gateway=policy.gateway)
    if mirror.primary_ip4_id is not None:
        return
    address = mirror_address(policy, vm.primary_ip4.address)
    ip = IPAddress.objects.filter(address=address, vrf=policy.prefix.vrf).first()
    if ip is None:
        ip = _create(IPAddress, done, address=address, vrf=policy.prefix.vrf, tenant=vm.tenant,
                     assigned_object=iface)
    elif ip.assigned_object is None:
        _sync(ip, done, assigned_object=iface)
    elif ip.assigned_object != iface:
        raise ValidationError(f"{address} is already assigned to {ip.assigned_object}; the mirror of {vm} needs it.")
    _sync(mirror, done, primary_ip4=ip)


def _mirror_config(primary, mirror, done):
    stored = {cv.param_id: cv.value for cv in primary.config_values.all()}
    want = {}
    for param in CatalogConfigParam.objects.filter(catalog=primary.catalog):
        if param.mirror_mode == MirrorModeChoices.FIXED:
            want[param.pk] = (param, param.mirror_value)
        elif param.mirror_mode == MirrorModeChoices.COPY and param.pk in stored:
            want[param.pk] = (param, stored[param.pk])
    have = {cv.param_id: cv for cv in mirror.config_values.all()}
    for pk, (param, value) in want.items():
        if pk in have:
            _sync(have[pk], done, value=value)
        else:
            _create(ServiceInstanceConfigValue, done, instance=mirror, param=param, value=value)
    for pk, cv in have.items():
        if pk not in want:
            cv.snapshot()
            cv.delete()
            done.append(f"deleted service instance config value {cv}")


def _mirror_instances(policy, vm, mirror, done):
    ct = _vm_ct()
    pairs = []
    primaries = ServiceInstance.objects.filter(
        parent_object_type=ct, parent_object_id=vm.pk, catalog__in=policy.catalogs.all()
    ).select_related("catalog")
    for primary in primaries:
        instance = ServiceInstance.objects.filter(
            parent_object_type=ct, parent_object_id=mirror.pk, catalog=primary.catalog, hostname=primary.hostname
        ).first() or _create(ServiceInstance, done, catalog=primary.catalog, parent_object_type=ct,
                             parent_object_id=mirror.pk, hostname=primary.hostname,
                             status=ServiceInstanceStatusChoices.STAGED)
        _mirror_config(primary, instance, done)
        if primary.catalog.ha_strategy != HAStrategyChoices.NONE \
                and not HAMirror.objects.filter(mirror=instance, primary=primary).exists():
            _create(HAMirror, done, mirror=instance, primary=primary)
        pairs.append((primary, instance))
    return pairs


def _mirror_database(policy, vm, mirror, profile, mprofile, pairs, done):
    if not apps.is_installed("netbox_database"):
        return
    DatabaseServer = apps.get_model("netbox_database", "DatabaseServer")
    Replication = apps.get_model("netbox_database", "MariaDBReplication")
    Node = apps.get_model("netbox_database", "MariaDBReplicationNode")
    for primary, instance in pairs:
        if primary.catalog.ha_strategy != HAStrategyChoices.MARIADB_MASTER_MASTER:
            continue
        server = DatabaseServer.objects.filter(service_instance=primary).first()
        if server is None:
            done.append(f"skipped replication for {primary}: it has no database server")
            continue
        name = mirror.name + server.name[len(vm.name):] if server.name.startswith(vm.name) else f"{mirror.name}-{server.engine}"
        fields = dict(engine=server.engine, version=server.version, port=server.port)
        mserver = DatabaseServer.objects.filter(service_instance=instance).first()
        if mserver is None:
            mserver = _create(DatabaseServer, done, name=name, listen_address="0.0.0.0", virtual_machine=mirror,
                              service_instance=instance, **fields)
        else:
            _sync(mserver, done, **fields)
        rname = f"{policy.replication_name_prefix}{vm.name[len(policy.source_name_prefix):]}-replication"
        group = Replication.objects.filter(name=rname).first() or _create(
            Replication, done, name=rname, topology="master-master", gtid=True,
            sync_mode="semi-sync" if policy.replication_semi_sync else "async",
        )
        for node_server, server_id, read_only in ((server, profile.vmid, False), (mserver, mprofile.vmid, True)):
            node = Node.objects.filter(server=node_server).first()
            if node is None:
                _create(Node, done, replication=group, server=node_server, mariadb_server_id=server_id,
                        role="co-primary", read_only=read_only)
            elif node.replication_id != group.pk:
                done.append(f"skipped node for {node_server}: it is already in {node.replication}")


def derive_mirror(policy, vm):
    """Create or sync ``vm``'s mirror under ``policy``; returns one line per write."""
    if not (policy.matches(vm) and vm.status in DERIVE_STATUSES and apps.is_installed("netbox_guests")):
        return []
    profile = apps.get_model("netbox_guests", "GuestProfile").objects.filter(virtual_machine=vm).first()
    if profile is None or vm.primary_ip4_id is None:
        return []
    done = []
    with transaction.atomic():
        mirror = _mirror_vm(policy, vm, done)
        mprofile = _mirror_profile(policy, profile, mirror, done)
        _mirror_interface(policy, vm, mirror, done)
        pairs = _mirror_instances(policy, vm, mirror, done)
        _mirror_database(policy, vm, mirror, profile, mprofile, pairs, done)
    return done


def derive_for_vm(vm_id):
    """Run every enabled policy that matches guest ``vm_id`` (a no-op for any other guest)."""
    vm = VirtualMachine.objects.filter(pk=vm_id).first()
    if vm is None:
        return []
    return [line for policy in HAMirrorPolicy.objects.filter(enabled=True, source_cluster_id=vm.cluster_id)
            for line in derive_mirror(policy, vm)]
