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
from ..choices import (
    HAStrategyChoices, IntegrationParamValueTypeChoices, ProviderScopeChoices,
    ServiceInstanceStatusChoices,
)
from ..models import (
    CatalogConfigParam, CatalogCredential, CatalogTestIntegration, CatalogTestState, CatalogToken,
    HAMirror, Integration, IntegrationCatalog, IntegrationCatalogParam, IntegrationParam,
    ServiceInstanceConfigValue,
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


class IntegrationParamModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.openbao = make_catalog("openbao")
        cls.authentik = make_catalog("authentik")
        cls.icat = IntegrationCatalog.objects.create(
            catalog=cls.authentik, type="openbao", requires_service="openbao"
        )
        IntegrationCatalogParam.objects.create(
            integration_catalog=cls.icat, key="db_index",
            value_type=IntegrationParamValueTypeChoices.INT, default="0",
        )
        IntegrationCatalogParam.objects.create(
            integration_catalog=cls.icat, key="scopes", value_type=IntegrationParamValueTypeChoices.LIST
        )
        IntegrationCatalogParam.objects.create(
            integration_catalog=cls.icat, key="redirect", value_type=IntegrationParamValueTypeChoices.URL
        )
        IntegrationCatalogParam.objects.create(
            integration_catalog=cls.icat, key="enabled", value_type=IntegrationParamValueTypeChoices.BOOL
        )
        IntegrationCatalogParam.objects.create(
            integration_catalog=cls.icat, key="client_secret",
            value_type=IntegrationParamValueTypeChoices.SECRET_REF, secret=True,
        )
        cls.consumer = make_instance(cls.authentik, hostname="authentik")
        cls.provider = make_instance(cls.openbao, hostname="openbao")
        cls.edge = Integration.objects.create(consumer=cls.consumer, provider=cls.provider, type="openbao")

    def test_catalog_param_declaration_str_url(self):
        p = IntegrationCatalogParam.objects.get(integration_catalog=self.icat, key="db_index")
        self.assertIn("db_index", str(p))
        self.assertIn("/plugins/services/integration-catalog-params/", p.get_absolute_url())

    def test_catalog_param_unique_and_cascade(self):
        icat2 = IntegrationCatalog.objects.create(
            catalog=make_catalog("nextcloud"), type="s3", requires_service="minio"
        )
        IntegrationCatalogParam.objects.create(
            integration_catalog=icat2, key="bucket", value_type=IntegrationParamValueTypeChoices.STRING
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            IntegrationCatalogParam.objects.create(
                integration_catalog=icat2, key="bucket",
                value_type=IntegrationParamValueTypeChoices.STRING,
            )
        icat2.delete()
        self.assertFalse(IntegrationCatalogParam.objects.filter(key="bucket").exists())

    def test_instance_override_valid(self):
        param = IntegrationParam(integration=self.edge, key="db_index", value="3")
        param.full_clean()
        param.save()
        self.assertIn("db_index", str(param))
        self.assertIn("/plugins/services/integration-params/", param.get_absolute_url())

    def test_instance_param_unique(self):
        IntegrationParam.objects.create(integration=self.edge, key="db_index", value="1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            IntegrationParam(integration=self.edge, key="db_index", value="2").save()

    def test_reject_unknown_key(self):
        with self.assertRaises(ValidationError):
            IntegrationParam(integration=self.edge, key="not_declared", value="x").full_clean()

    def test_reject_bad_int(self):
        with self.assertRaises(ValidationError):
            IntegrationParam(integration=self.edge, key="db_index", value="not-an-int").full_clean()

    def test_reject_bad_bool(self):
        with self.assertRaises(ValidationError):
            IntegrationParam(integration=self.edge, key="enabled", value="maybe").full_clean()
        IntegrationParam(integration=self.edge, key="enabled", value="true").full_clean()

    def test_reject_bad_url(self):
        with self.assertRaises(ValidationError):
            IntegrationParam(integration=self.edge, key="redirect", value="not a url").full_clean()
        IntegrationParam(integration=self.edge, key="redirect", value="https://authentik.example/cb").full_clean()

    def test_reject_inline_secret(self):
        # An inline literal (a URL / an email / a bare token with no path) is rejected on a secret param.
        for inline in ("https://example.com/token", "user@example.com", "literaltoken"):
            with self.assertRaises(ValidationError):
                IntegrationParam(integration=self.edge, key="client_secret", value=inline).full_clean()
        # An OpenBao path reference is accepted.
        IntegrationParam(integration=self.edge, key="client_secret", value="secret/data/authentik/client").full_clean()

    def test_missing_required_without_default(self):
        # A required param with no default must have an instance row; the edge's clean() reports it missing.
        IntegrationCatalogParam.objects.create(
            integration_catalog=self.icat, key="issuer_url",
            value_type=IntegrationParamValueTypeChoices.URL, required=True,
        )
        with self.assertRaises(ValidationError):
            self.edge.full_clean()
        IntegrationParam.objects.create(integration=self.edge, key="issuer_url", value="https://id.example/")
        self.edge.full_clean()

    def test_list_order_round_trips(self):
        value = "openid\nprofile\nemail\ngroups"
        param = IntegrationParam.objects.create(integration=self.edge, key="scopes", value=value)
        param.refresh_from_db()
        self.assertEqual(param.value.split("\n"), ["openid", "profile", "email", "groups"])


class CatalogConfigParamModelTest(TestCase):
    """CatalogConfigParam (the service-config schema) + ServiceInstanceConfigValue (the per-instance
    override): str/url, uniqueness/cascade, the typed-value contract, the secret ⇒ path rule, and
    the cross-type guard (a value may only reference a param of the instance's own service type)."""

    @classmethod
    def setUpTestData(cls):
        cls.forgejo = make_catalog("forgejo")
        cls.p_int = CatalogConfigParam.objects.create(
            catalog=cls.forgejo, key="workers", value_type=IntegrationParamValueTypeChoices.INT,
            default="4", provider_attr="forgejo_service.workers",
        )
        cls.p_list = CatalogConfigParam.objects.create(
            catalog=cls.forgejo, key="allowed_hosts", value_type=IntegrationParamValueTypeChoices.LIST,
        )
        cls.p_url = CatalogConfigParam.objects.create(
            catalog=cls.forgejo, key="root_url", value_type=IntegrationParamValueTypeChoices.URL,
        )
        cls.p_bool = CatalogConfigParam.objects.create(
            catalog=cls.forgejo, key="registration_open", value_type=IntegrationParamValueTypeChoices.BOOL,
        )
        cls.p_secret = CatalogConfigParam.objects.create(
            catalog=cls.forgejo, key="smtp_password",
            value_type=IntegrationParamValueTypeChoices.SECRET_REF, secret=True,
        )
        cls.instance = make_instance(cls.forgejo, hostname="forgejo")

    def test_catalog_param_str_url(self):
        self.assertIn("workers", str(self.p_int))
        self.assertIn("/plugins/services/catalog-config-params/", self.p_int.get_absolute_url())

    def test_catalog_param_unique_and_cascade(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            CatalogConfigParam.objects.create(
                catalog=self.forgejo, key="workers", value_type=IntegrationParamValueTypeChoices.INT,
            )
        other = make_catalog("openbao")
        p = CatalogConfigParam.objects.create(
            catalog=other, key="listen_addr", value_type=IntegrationParamValueTypeChoices.STRING,
        )
        other.delete()
        self.assertFalse(CatalogConfigParam.objects.filter(pk=p.pk).exists())

    def test_instance_override_valid(self):
        cv = ServiceInstanceConfigValue(instance=self.instance, param=self.p_int, value="8")
        cv.full_clean()
        cv.save()
        self.assertIn("workers", str(cv))
        self.assertIn("/plugins/services/instance-config-values/", cv.get_absolute_url())

    def test_instance_value_unique_and_cascade(self):
        ServiceInstanceConfigValue.objects.create(instance=self.instance, param=self.p_int, value="6")
        with self.assertRaises(IntegrityError), transaction.atomic():
            ServiceInstanceConfigValue(instance=self.instance, param=self.p_int, value="7").save()
        self.p_int.delete()
        self.assertEqual(ServiceInstanceConfigValue.objects.filter(param=self.p_int.pk).count(), 0)

    def test_reject_bad_int(self):
        with self.assertRaises(ValidationError):
            ServiceInstanceConfigValue(instance=self.instance, param=self.p_int, value="lots").full_clean()

    def test_reject_bad_bool(self):
        with self.assertRaises(ValidationError):
            ServiceInstanceConfigValue(instance=self.instance, param=self.p_bool, value="maybe").full_clean()
        ServiceInstanceConfigValue(instance=self.instance, param=self.p_bool, value="true").full_clean()

    def test_reject_bad_url(self):
        with self.assertRaises(ValidationError):
            ServiceInstanceConfigValue(instance=self.instance, param=self.p_url, value="not a url").full_clean()
        ServiceInstanceConfigValue(instance=self.instance, param=self.p_url, value="https://forgejo.example/").full_clean()

    def test_reject_inline_secret(self):
        for inline in ("https://example.com/token", "user@example.com", "literaltoken"):
            with self.assertRaises(ValidationError):
                ServiceInstanceConfigValue(instance=self.instance, param=self.p_secret, value=inline).full_clean()
        ServiceInstanceConfigValue(
            instance=self.instance, param=self.p_secret, value="secret/data/forgejo/smtp"
        ).full_clean()

    def test_reject_cross_type_param(self):
        # A value may only reference a config param declared on the instance's own service type.
        openbao = make_catalog("openbao")
        foreign = CatalogConfigParam.objects.create(
            catalog=openbao, key="listen_addr", value_type=IntegrationParamValueTypeChoices.STRING,
        )
        with self.assertRaises(ValidationError):
            ServiceInstanceConfigValue(instance=self.instance, param=foreign, value="0.0.0.0").full_clean()

    def test_list_order_round_trips(self):
        value = "forgejo.example\ngit.example\nlocalhost"
        cv = ServiceInstanceConfigValue.objects.create(instance=self.instance, param=self.p_list, value=value)
        cv.refresh_from_db()
        self.assertEqual(cv.value.split("\n"), ["forgejo.example", "git.example", "localhost"])


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
