# SPDX-License-Identifier: AGPL-3.0-or-later
"""Model tests against a real DB (no mocks): creation, str/url, constraints, the GFK parent + M2M
listeners, and — the load-bearing logic — Integration cardinality (clean() + the pre_save backstop)
and the HAMirror same-type / no-self-mirror rules."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from django.test import TestCase
from ipam.models import Service
from utilities.testing import create_test_device
from ..choices import HAStrategyChoices, ProviderScopeChoices, ServiceInstanceStatusChoices
from ..models import (
    CatalogCredential, CatalogTestIntegration, CatalogTestState, CatalogToken, HAMirror, Integration,
    IntegrationCatalog,
)
from .utils import make_catalog, make_instance, make_vm


class ServiceCatalogModelTest(TestCase):
    def test_create_str_url_defaults(self):
        c = make_catalog("forgejo", display_name="Forgejo")
        self.assertEqual(str(c), "Forgejo")
        self.assertIn("/plugins/services/service-catalog/", c.get_absolute_url())
        self.assertEqual(c.ha_strategy, HAStrategyChoices.NONE)
        self.assertFalse(c.ingress_haproxy_backup)

    def test_name_unique(self):
        make_catalog("openbao")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_catalog("openbao")

    def test_child_unique_and_cascade(self):
        c = make_catalog("authentik")
        CatalogCredential.objects.create(catalog=c, cred_id="admin_pass", deploy_var="authentik_admin_password")
        with self.assertRaises(IntegrityError), transaction.atomic():
            CatalogCredential.objects.create(catalog=c, cred_id="admin_pass", deploy_var="x")
        CatalogToken.objects.create(catalog=c, name="authentik_api_token", output_var="tok_file")
        c.delete()
        self.assertEqual(CatalogCredential.objects.count(), 0)
        self.assertEqual(CatalogToken.objects.count(), 0)


class CatalogTestStateModelTest(TestCase):
    def test_unique_per_catalog_distro_and_nested_integration(self):
        c = make_catalog("nextcloud")
        ts = CatalogTestState.objects.create(catalog=c, distro="debian", install=True, init=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CatalogTestState.objects.create(catalog=c, distro="debian")
        CatalogTestIntegration.objects.create(test_state=ts, provider_service="openbao", passed=True)
        self.assertEqual(ts.integrations.count(), 1)
        ts.delete()
        self.assertEqual(CatalogTestIntegration.objects.count(), 0)


class ServiceInstanceModelTest(TestCase):
    def test_vm_parent_str_url(self):
        c = make_catalog("forgejo")
        vm = make_vm("ct-forgejo")
        inst = make_instance(c, parent=vm, hostname="forgejo")
        self.assertEqual(inst.parent, vm)
        self.assertEqual(inst.status, ServiceInstanceStatusChoices.STAGED)
        self.assertIn("/plugins/services/service-instances/", inst.get_absolute_url())
        self.assertIn("forgejo", str(inst))

    def test_device_parent(self):
        c = make_catalog("openbao")
        dev = create_test_device("baremetal-1")
        inst = make_instance(c, parent=dev, hostname="bao")
        self.assertEqual(inst.parent, dev)

    def test_listeners_m2m(self):
        c = make_catalog("forgejo")
        inst = make_instance(c, hostname="fj")
        svc = Service.objects.create(name="forgejo-web", protocol="tcp", ports=[3000], parent=inst.parent)
        inst.listeners.add(svc)
        self.assertEqual(list(inst.listeners.all()), [svc])


class IntegrationCardinalityTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.openbao = make_catalog("openbao", default_port=8200)
        cls.authentik = make_catalog("authentik", default_port=9000)
        # authentik consumes openbao, shared, max 1.
        IntegrationCatalog.objects.create(
            catalog=cls.authentik, type="openbao", requires_service="openbao",
            provider_scope=ProviderScopeChoices.SHARED, consumer_max=1,
        )
        cls.consumer = make_instance(cls.authentik, hostname="authentik")
        cls.provider = make_instance(cls.openbao, hostname="openbao")

    def test_valid_edge(self):
        edge = Integration.objects.create(consumer=self.consumer, provider=self.provider, type="openbao")
        self.assertIn("openbao", str(edge))
        self.assertIn("/plugins/services/integrations/", edge.get_absolute_url())

    def test_self_integration_rejected(self):
        with self.assertRaises(ValidationError):
            Integration.objects.create(consumer=self.consumer, provider=self.consumer, type="openbao")

    def test_unknown_type_rejected(self):
        with self.assertRaises(ValidationError):
            Integration.objects.create(consumer=self.consumer, provider=self.provider, type="stalwart")

    def test_provider_type_mismatch_rejected(self):
        wrong = make_instance(self.authentik, hostname="not-openbao")
        with self.assertRaises(ValidationError):
            Integration.objects.create(consumer=self.consumer, provider=wrong, type="openbao")

    def test_consumer_max_enforced(self):
        Integration.objects.create(consumer=self.consumer, provider=self.provider, type="openbao")
        second = make_instance(self.openbao, hostname="openbao-2")
        with self.assertRaises(ValidationError):
            Integration.objects.create(consumer=self.consumer, provider=second, type="openbao")

    def test_dedicated_provider_single_consumer(self):
        forgejo = make_catalog("forgejo")
        IntegrationCatalog.objects.create(
            catalog=forgejo, type="openbao", requires_service="openbao",
            provider_scope=ProviderScopeChoices.DEDICATED, consumer_max=1,
        )
        c1 = make_instance(forgejo, hostname="forgejo-1")
        c2 = make_instance(forgejo, hostname="forgejo-2")
        Integration.objects.create(consumer=c1, provider=self.provider, type="openbao")
        with self.assertRaises(ValidationError):
            Integration.objects.create(consumer=c2, provider=self.provider, type="openbao")

    def test_unique_edge(self):
        Integration.objects.create(consumer=self.consumer, provider=self.provider, type="openbao")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Integration(consumer=self.consumer, provider=self.provider, type="openbao").save()


class HAMirrorModelTest(TestCase):
    def test_same_type_pairing(self):
        wp = make_catalog("wordpress", ha_strategy=HAStrategyChoices.CONTENT_RSYNC)
        primary = make_instance(wp, hostname="wp-primary")
        mirror = make_instance(wp, hostname="wp-mirror")
        edge = HAMirror.objects.create(mirror=mirror, primary=primary)
        edge.full_clean()
        self.assertIn("mirror of", str(edge))

    def test_self_mirror_rejected(self):
        wp = make_catalog("wordpress")
        inst = make_instance(wp, hostname="wp")
        with self.assertRaises(ValidationError):
            HAMirror(mirror=inst, primary=inst).full_clean()

    def test_cross_type_rejected(self):
        wp = make_catalog("wordpress")
        db = make_catalog("mariadb")
        with self.assertRaises(ValidationError):
            HAMirror(mirror=make_instance(wp, hostname="wp"), primary=make_instance(db, hostname="db")).full_clean()
