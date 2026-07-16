# SPDX-License-Identifier: AGPL-3.0-or-later
"""FilterSet tests against a real DB (no mocks): the explicit FK + choice filters and search."""
from django.test import TestCase
from ..choices import (
    ExtensionKindChoices, HAStrategyChoices, IntegrationParamValueTypeChoices, ProviderScopeChoices,
    SecretKindChoices, ServiceInstanceStatusChoices,
)
from ..filtersets import (
    CatalogConfigParamFilterSet, CatalogExtensionFilterSet, HostRoleAssignmentFilterSet,
    HostRoleAssignmentVarFilterSet, HostRoleFilterSet, HostRoleParamFilterSet, IntegrationCatalogFilterSet,
    IntegrationCatalogParamFilterSet, IntegrationFilterSet, ServiceCatalogFilterSet,
    RotationPolicyFilterSet, ServiceInstanceConfigValueFilterSet, ServiceInstanceExtensionFilterSet,
    ServiceInstanceFilterSet,
)
from ..models import (
    CatalogConfigParam, CatalogExtension, HostRole, HostRoleAssignment, HostRoleAssignmentVar,
    HostRoleParam, Integration, IntegrationCatalog, IntegrationCatalogParam, RotationPolicy, ServiceCatalog,
    ServiceInstance, ServiceInstanceConfigValue, ServiceInstanceExtension,
)
from .utils import make_assignment, make_catalog, make_instance, make_role


class ServiceCatalogFilterTest(TestCase):
    queryset = ServiceCatalog.objects.all()
    filterset = ServiceCatalogFilterSet

    @classmethod
    def setUpTestData(cls):
        make_catalog("forgejo", tier=1, requires_gpu=False)
        make_catalog("vllm", tier=2, requires_gpu=True, ha_strategy=HAStrategyChoices.NONE)
        make_catalog("wordpress", tier=1, ha_strategy=HAStrategyChoices.CONTENT_RSYNC)

    def test_name(self):
        self.assertEqual(self.filterset({"name": ["forgejo"]}, self.queryset).qs.count(), 1)

    def test_requires_gpu(self):
        self.assertEqual(self.filterset({"requires_gpu": True}, self.queryset).qs.count(), 1)

    def test_ha_strategy(self):
        self.assertEqual(
            self.filterset({"ha_strategy": [HAStrategyChoices.CONTENT_RSYNC]}, self.queryset).qs.count(), 1
        )

    def test_search(self):
        self.assertEqual(self.filterset({"q": "word"}, self.queryset).qs.count(), 1)


class IntegrationCatalogFilterTest(TestCase):
    queryset = IntegrationCatalog.objects.all()
    filterset = IntegrationCatalogFilterSet

    @classmethod
    def setUpTestData(cls):
        cat = make_catalog("authentik")
        IntegrationCatalog.objects.create(catalog=cat, type="openbao", requires_service="openbao",
                                          provider_scope=ProviderScopeChoices.DEDICATED)
        IntegrationCatalog.objects.create(catalog=cat, type="alloy", requires_service="alloy")

    def test_catalog_by_name(self):
        self.assertEqual(self.filterset({"catalog": ["authentik"]}, self.queryset).qs.count(), 2)

    def test_provider_scope(self):
        self.assertEqual(
            self.filterset({"provider_scope": [ProviderScopeChoices.DEDICATED]}, self.queryset).qs.count(), 1
        )

    def test_requires_service(self):
        self.assertEqual(self.filterset({"requires_service": ["openbao"]}, self.queryset).qs.count(), 1)


class IntegrationCatalogParamFilterTest(TestCase):
    queryset = IntegrationCatalogParam.objects.all()
    filterset = IntegrationCatalogParamFilterSet

    @classmethod
    def setUpTestData(cls):
        icat = IntegrationCatalog.objects.create(
            catalog=make_catalog("authentik"), type="openbao", requires_service="openbao"
        )
        cls.icat = icat
        IntegrationCatalogParam.objects.create(
            integration_catalog=icat, key="db_index", value_type=IntegrationParamValueTypeChoices.INT
        )
        IntegrationCatalogParam.objects.create(
            integration_catalog=icat, key="scopes", value_type=IntegrationParamValueTypeChoices.LIST,
            required=True,
        )
        IntegrationCatalogParam.objects.create(
            integration_catalog=icat, key="client_secret",
            value_type=IntegrationParamValueTypeChoices.SECRET_REF, secret=True,
        )

    def test_integration_catalog_id(self):
        self.assertEqual(
            self.filterset({"integration_catalog_id": [self.icat.pk]}, self.queryset).qs.count(), 3
        )

    def test_value_type(self):
        self.assertEqual(
            self.filterset({"value_type": [IntegrationParamValueTypeChoices.LIST]}, self.queryset).qs.count(), 1
        )

    def test_required(self):
        self.assertEqual(self.filterset({"required": True}, self.queryset).qs.count(), 1)

    def test_secret(self):
        self.assertEqual(self.filterset({"secret": True}, self.queryset).qs.count(), 1)

    def test_search_key(self):
        self.assertEqual(self.filterset({"q": "db_index"}, self.queryset).qs.count(), 1)


class CatalogConfigParamFilterTest(TestCase):
    queryset = CatalogConfigParam.objects.all()
    filterset = CatalogConfigParamFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.cat = make_catalog("forgejo")
        CatalogConfigParam.objects.create(
            catalog=cls.cat, key="workers", value_type=IntegrationParamValueTypeChoices.INT,
            provider_attr="forgejo_service.workers",
        )
        CatalogConfigParam.objects.create(
            catalog=cls.cat, key="allowed_hosts", value_type=IntegrationParamValueTypeChoices.LIST,
            required=True,
        )
        CatalogConfigParam.objects.create(
            catalog=cls.cat, key="smtp_password",
            value_type=IntegrationParamValueTypeChoices.SECRET_REF, secret=True,
        )

    def test_catalog_by_name(self):
        self.assertEqual(self.filterset({"catalog": ["forgejo"]}, self.queryset).qs.count(), 3)

    def test_value_type(self):
        self.assertEqual(
            self.filterset({"value_type": [IntegrationParamValueTypeChoices.LIST]}, self.queryset).qs.count(), 1
        )

    def test_required(self):
        self.assertEqual(self.filterset({"required": True}, self.queryset).qs.count(), 1)

    def test_secret(self):
        self.assertEqual(self.filterset({"secret": True}, self.queryset).qs.count(), 1)

    def test_search_provider_attr(self):
        self.assertEqual(self.filterset({"q": "forgejo_service"}, self.queryset).qs.count(), 1)


class ServiceInstanceConfigValueFilterTest(TestCase):
    queryset = ServiceInstanceConfigValue.objects.all()
    filterset = ServiceInstanceConfigValueFilterSet

    @classmethod
    def setUpTestData(cls):
        cat = make_catalog("forgejo")
        cls.param = CatalogConfigParam.objects.create(
            catalog=cat, key="workers", value_type=IntegrationParamValueTypeChoices.INT,
        )
        cls.instance = make_instance(cat, hostname="forgejo")
        ServiceInstanceConfigValue.objects.create(instance=cls.instance, param=cls.param, value="8")

    def test_instance_id(self):
        self.assertEqual(self.filterset({"instance_id": [self.instance.pk]}, self.queryset).qs.count(), 1)

    def test_param_id(self):
        self.assertEqual(self.filterset({"param_id": [self.param.pk]}, self.queryset).qs.count(), 1)

    def test_search_param_key(self):
        self.assertEqual(self.filterset({"q": "workers"}, self.queryset).qs.count(), 1)


class CatalogExtensionFilterTest(TestCase):
    queryset = CatalogExtension.objects.all()
    filterset = CatalogExtensionFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.wp = make_catalog("wordpress")
        CatalogExtension.objects.create(
            catalog=cls.wp, kind=ExtensionKindChoices.PLUGIN, name="akismet", required=True,
        )
        CatalogExtension.objects.create(
            catalog=cls.wp, kind=ExtensionKindChoices.THEME, name="twentytwentyfour",
        )
        CatalogExtension.objects.create(
            catalog=cls.wp, kind=ExtensionKindChoices.PLUGIN, name="woocommerce",
        )

    def test_catalog_by_name(self):
        self.assertEqual(self.filterset({"catalog": ["wordpress"]}, self.queryset).qs.count(), 3)

    def test_kind(self):
        self.assertEqual(
            self.filterset({"kind": [ExtensionKindChoices.PLUGIN]}, self.queryset).qs.count(), 2
        )

    def test_required(self):
        self.assertEqual(self.filterset({"required": True}, self.queryset).qs.count(), 1)

    def test_search_name(self):
        self.assertEqual(self.filterset({"q": "woocommerce"}, self.queryset).qs.count(), 1)


class ServiceInstanceExtensionFilterTest(TestCase):
    queryset = ServiceInstanceExtension.objects.all()
    filterset = ServiceInstanceExtensionFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.instance = make_instance(make_catalog("wordpress"), hostname="wp")
        ServiceInstanceExtension.objects.create(
            instance=cls.instance, kind=ExtensionKindChoices.PLUGIN, name="akismet",
            version="5.3", enabled=True, managed=True,
        )
        ServiceInstanceExtension.objects.create(
            instance=cls.instance, kind=ExtensionKindChoices.PLUGIN, name="jetpack",
            enabled=False, managed=False,
        )

    def test_instance_id(self):
        self.assertEqual(self.filterset({"instance_id": [self.instance.pk]}, self.queryset).qs.count(), 2)

    def test_kind(self):
        self.assertEqual(
            self.filterset({"kind": [ExtensionKindChoices.PLUGIN]}, self.queryset).qs.count(), 2
        )

    def test_enabled(self):
        self.assertEqual(self.filterset({"enabled": True}, self.queryset).qs.count(), 1)

    def test_managed(self):
        self.assertEqual(self.filterset({"managed": False}, self.queryset).qs.count(), 1)

    def test_search_name(self):
        self.assertEqual(self.filterset({"q": "jetpack"}, self.queryset).qs.count(), 1)


class ServiceInstanceFilterTest(TestCase):
    queryset = ServiceInstance.objects.all()
    filterset = ServiceInstanceFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.cat = make_catalog("forgejo")
        make_instance(cls.cat, hostname="fj-1", status=ServiceInstanceStatusChoices.ACTIVE)
        make_instance(cls.cat, hostname="fj-2", status=ServiceInstanceStatusChoices.STAGED)

    def test_catalog_id(self):
        self.assertEqual(self.filterset({"catalog_id": [self.cat.pk]}, self.queryset).qs.count(), 2)

    def test_status(self):
        self.assertEqual(
            self.filterset({"status": [ServiceInstanceStatusChoices.ACTIVE]}, self.queryset).qs.count(), 1
        )

    def test_search_hostname(self):
        self.assertEqual(self.filterset({"q": "fj-1"}, self.queryset).qs.count(), 1)


class IntegrationFilterTest(TestCase):
    queryset = Integration.objects.all()
    filterset = IntegrationFilterSet

    @classmethod
    def setUpTestData(cls):
        openbao = make_catalog("openbao")
        authentik = make_catalog("authentik")
        IntegrationCatalog.objects.create(catalog=authentik, type="openbao", requires_service="openbao")
        cls.consumer = make_instance(authentik, hostname="authentik")
        provider = make_instance(openbao, hostname="openbao")
        Integration.objects.create(consumer=cls.consumer, provider=provider, type="openbao")

    def test_consumer_id(self):
        self.assertEqual(self.filterset({"consumer_id": [self.consumer.pk]}, self.queryset).qs.count(), 1)

    def test_type(self):
        self.assertEqual(self.filterset({"type": ["openbao"]}, self.queryset).qs.count(), 1)


class HostRoleFilterTest(TestCase):
    queryset = HostRole.objects.all()
    filterset = HostRoleFilterSet

    @classmethod
    def setUpTestData(cls):
        make_role("wire_fail2ban", idempotent=True)
        make_role("harden_php_ini", idempotent=False)

    def test_name(self):
        self.assertEqual(self.filterset({"name": ["wire_fail2ban"]}, self.queryset).qs.count(), 1)

    def test_idempotent(self):
        self.assertEqual(self.filterset({"idempotent": False}, self.queryset).qs.count(), 1)

    def test_search(self):
        self.assertEqual(self.filterset({"q": "fail2ban"}, self.queryset).qs.count(), 1)


class RotationPolicyFilterTest(TestCase):
    queryset = RotationPolicy.objects.all()
    filterset = RotationPolicyFilterSet

    @classmethod
    def setUpTestData(cls):
        catalog = make_catalog("postgres")
        cls.role = make_role("rotate-postgres-role")
        cls.consumer = make_instance(make_catalog("forgejo"), hostname="forgejo")
        for i, enabled in enumerate((True, False)):
            policy = RotationPolicy.objects.create(
                instance=make_instance(catalog, hostname=f"postgres-{i}"), name=f"role-{i}",
                secret_kind=SecretKindChoices.DB_SERVICE_ACCOUNT, openbao_path=f"secret/data/postgres/role-{i}",
                host_role=cls.role, enabled=enabled,
            )
            if i == 0:
                policy.consumers.add(cls.consumer)

    def test_role_consumer_enabled_and_search(self):
        self.assertEqual(self.filterset({"host_role_id": [self.role.pk]}, self.queryset).qs.count(), 2)
        self.assertEqual(self.filterset({"consumer_id": [self.consumer.pk]}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({"enabled": True}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({"q": "role-1"}, self.queryset).qs.count(), 1)


class HostRoleParamFilterTest(TestCase):
    queryset = HostRoleParam.objects.all()
    filterset = HostRoleParamFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.role = make_role("harden_php_ini")
        HostRoleParam.objects.create(
            role=cls.role, key="disable_functions", value_type=IntegrationParamValueTypeChoices.STRING
        )
        HostRoleParam.objects.create(
            role=cls.role, key="max_execution_time", value_type=IntegrationParamValueTypeChoices.INT, required=True,
        )
        HostRoleParam.objects.create(
            role=cls.role, key="db_password", value_type=IntegrationParamValueTypeChoices.SECRET_REF, secret=True,
        )

    def test_role_by_name(self):
        self.assertEqual(self.filterset({"role": ["harden_php_ini"]}, self.queryset).qs.count(), 3)

    def test_value_type(self):
        self.assertEqual(
            self.filterset({"value_type": [IntegrationParamValueTypeChoices.INT]}, self.queryset).qs.count(), 1
        )

    def test_required(self):
        self.assertEqual(self.filterset({"required": True}, self.queryset).qs.count(), 1)

    def test_secret(self):
        self.assertEqual(self.filterset({"secret": True}, self.queryset).qs.count(), 1)

    def test_search_key(self):
        self.assertEqual(self.filterset({"q": "disable_functions"}, self.queryset).qs.count(), 1)


class HostRoleAssignmentFilterTest(TestCase):
    queryset = HostRoleAssignment.objects.all()
    filterset = HostRoleAssignmentFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.role = make_role("wire_aide")
        make_assignment(cls.role, enabled=True)
        make_assignment(cls.role, enabled=False)

    def test_role_id(self):
        self.assertEqual(self.filterset({"role_id": [self.role.pk]}, self.queryset).qs.count(), 2)

    def test_enabled(self):
        self.assertEqual(self.filterset({"enabled": True}, self.queryset).qs.count(), 1)


class HostRoleAssignmentVarFilterTest(TestCase):
    queryset = HostRoleAssignmentVar.objects.all()
    filterset = HostRoleAssignmentVarFilterSet

    @classmethod
    def setUpTestData(cls):
        role = make_role("harden_php_ini")
        cls.param = HostRoleParam.objects.create(
            role=role, key="max_execution_time", value_type=IntegrationParamValueTypeChoices.INT
        )
        cls.assignment = make_assignment(role)
        HostRoleAssignmentVar.objects.create(assignment=cls.assignment, param=cls.param, value="90")

    def test_assignment_id(self):
        self.assertEqual(self.filterset({"assignment_id": [self.assignment.pk]}, self.queryset).qs.count(), 1)

    def test_param_id(self):
        self.assertEqual(self.filterset({"param_id": [self.param.pk]}, self.queryset).qs.count(), 1)

    def test_search_param_key(self):
        self.assertEqual(self.filterset({"q": "max_execution_time"}, self.queryset).qs.count(), 1)
