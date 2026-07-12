# SPDX-License-Identifier: AGPL-3.0-or-later
"""REST API CRUD tests against a real DB + real API client (no mocks). Composes the explicit CRUD
mixins (no GraphQL type yet). Integration create_data is kept within the cardinality rules (shared,
unbounded provider) so the pre_save backstop accepts every created edge."""
import unittest

from django.urls import reverse
from utilities.testing import APIViewTestCases, create_test_device
from ..choices import ExtensionKindChoices, IntegrationParamValueTypeChoices
from ..models import (
    CatalogConfigParam, CatalogCredential, CatalogExtension, CatalogSecondaryPort,
    CatalogTestIntegration, CatalogTestState, CatalogToken, HAMirror, Integration, IntegrationCatalog,
    IntegrationCatalogParam, IntegrationParam, InstanceOpenBaoPath, ServiceCatalog, ServiceInstance,
    ServiceInstanceConfigValue, ServiceInstanceExtension,
)
from .utils import make_catalog, make_instance, make_vm


class _CRUD(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.CreateObjectViewTestCase,
    APIViewTestCases.UpdateObjectViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
):
    # Plugin API views register under the `plugins-api:<app_label>-api` namespace;
    # without this override the test base reverses `<app_label>-api:…` (no
    # `plugins-api` prefix) → NoReverseMatch. See utilities/testing/api.py.
    view_namespace = "plugins-api:netbox_services"

    @classmethod
    def setUpClass(cls):
        if cls is _CRUD:
            raise unittest.SkipTest("abstract API test base")
        super().setUpClass()


class ServiceCatalogAPITest(_CRUD):
    model = ServiceCatalog
    brief_fields = ["display", "display_name", "id", "name", "url"]
    bulk_update_data = {"tier": 2}

    @classmethod
    def setUpTestData(cls):
        for n in ("forgejo", "openbao", "authentik"):
            make_catalog(n)
        cls.create_data = [
            {"name": "nextcloud", "display_name": "Nextcloud", "default_port": 80},
            {"name": "stalwart", "display_name": "Stalwart", "default_port": 443},
            {"name": "alloy", "display_name": "Alloy"},
        ]


class CatalogCredentialAPITest(_CRUD):
    model = CatalogCredential
    brief_fields = ["cred_id", "display", "id", "url"]
    bulk_update_data = {"length": 32}

    @classmethod
    def setUpTestData(cls):
        cat = make_catalog("authentik")
        CatalogCredential.objects.bulk_create([
            CatalogCredential(catalog=cat, cred_id=f"c{i}", deploy_var=f"v{i}") for i in range(3)
        ])
        cls.create_data = [
            {"catalog": cat.pk, "cred_id": "admin_pass", "length": 24, "deploy_var": "authentik_admin_password"},
            {"catalog": cat.pk, "cred_id": "db_pass", "length": 32, "deploy_var": "authentik_db_password"},
            {"catalog": cat.pk, "cred_id": "api_pass", "deploy_var": "authentik_api"},
        ]


class CatalogTokenAPITest(_CRUD):
    model = CatalogToken
    brief_fields = ["display", "id", "name", "url"]
    bulk_update_data = {"output_var": "out_file"}

    @classmethod
    def setUpTestData(cls):
        cat = make_catalog("openbao")
        CatalogToken.objects.bulk_create([
            CatalogToken(catalog=cat, name=f"t{i}", output_var=f"o{i}") for i in range(3)
        ])
        cls.create_data = [
            {"catalog": cat.pk, "name": "openbao_addr", "output_var": "addr_file"},
            {"catalog": cat.pk, "name": "admin_token", "output_var": "token_file"},
            {"catalog": cat.pk, "name": "openbao_unseal_key", "output_var": "unseal_file"},
        ]


class CatalogSecondaryPortAPITest(_CRUD):
    model = CatalogSecondaryPort
    brief_fields = ["display", "id", "port", "protocol", "url"]
    bulk_update_data = {"name": "renamed"}

    @classmethod
    def setUpTestData(cls):
        cat = make_catalog("forgejo")
        CatalogSecondaryPort.objects.bulk_create([
            CatalogSecondaryPort(catalog=cat, port=p, name=f"p{p}") for p in (2200, 2201, 2202)
        ])
        cls.create_data = [
            {"catalog": cat.pk, "port": 2222, "protocol": "tcp", "name": "ssh"},
            {"catalog": cat.pk, "port": 9418, "protocol": "tcp", "name": "git"},
            {"catalog": cat.pk, "port": 53, "protocol": "udp", "name": "dns"},
        ]


class IntegrationCatalogAPITest(_CRUD):
    model = IntegrationCatalog
    brief_fields = ["display", "id", "requires_service", "type", "url"]
    bulk_update_data = {"provider_scope": "dedicated"}

    @classmethod
    def setUpTestData(cls):
        cat = make_catalog("authentik")
        IntegrationCatalog.objects.bulk_create([
            IntegrationCatalog(catalog=cat, type=f"svc{i}", requires_service=f"svc{i}") for i in range(3)
        ])
        cls.create_data = [
            {"catalog": cat.pk, "type": "openbao", "requires_service": "openbao", "consumer_max": 1},
            {"catalog": cat.pk, "type": "stalwart", "requires_service": "stalwart"},
            {"catalog": cat.pk, "type": "alloy", "requires_service": "alloy", "provider_scope": "shared"},
        ]


class IntegrationCatalogParamAPITest(_CRUD):
    model = IntegrationCatalogParam
    brief_fields = ["display", "id", "key", "url", "value_type"]
    bulk_update_data = {"required": True}

    @classmethod
    def setUpTestData(cls):
        icat = IntegrationCatalog.objects.create(
            catalog=make_catalog("authentik"), type="openbao", requires_service="openbao"
        )
        IntegrationCatalogParam.objects.bulk_create([
            IntegrationCatalogParam(integration_catalog=icat, key=f"k{i}",
                                    value_type=IntegrationParamValueTypeChoices.STRING)
            for i in range(3)
        ])
        cls.create_data = [
            {"integration_catalog": icat.pk, "key": "db_index", "value_type": "int", "default": "0"},
            {"integration_catalog": icat.pk, "key": "scopes", "value_type": "list", "required": True},
            {"integration_catalog": icat.pk, "key": "client_secret", "value_type": "secret_ref", "secret": True},
        ]


class CatalogConfigParamAPITest(_CRUD):
    model = CatalogConfigParam
    brief_fields = ["display", "id", "key", "url", "value_type"]
    bulk_update_data = {"required": True}

    @classmethod
    def setUpTestData(cls):
        cat = make_catalog("forgejo")
        CatalogConfigParam.objects.bulk_create([
            CatalogConfigParam(catalog=cat, key=f"k{i}",
                               value_type=IntegrationParamValueTypeChoices.STRING)
            for i in range(3)
        ])
        cls.create_data = [
            {"catalog": cat.pk, "key": "workers", "value_type": "int", "default": "4",
             "provider_attr": "forgejo_service.workers"},
            {"catalog": cat.pk, "key": "allowed_hosts", "value_type": "list", "required": True},
            {"catalog": cat.pk, "key": "smtp_password", "value_type": "secret_ref", "secret": True},
        ]


class CatalogExtensionAPITest(_CRUD):
    model = CatalogExtension
    brief_fields = ["display", "id", "kind", "name", "url"]
    bulk_update_data = {"required": True}

    @classmethod
    def setUpTestData(cls):
        cat = make_catalog("wordpress")
        CatalogExtension.objects.bulk_create([
            CatalogExtension(catalog=cat, kind=ExtensionKindChoices.PLUGIN, name=f"plugin{i}")
            for i in range(3)
        ])
        cls.create_data = [
            {"catalog": cat.pk, "kind": "plugin", "name": "akismet", "default_version": "5.3", "required": True},
            {"catalog": cat.pk, "kind": "theme", "name": "twentytwentyfour"},
            {"catalog": cat.pk, "kind": "app", "name": "multisite"},
        ]


class CatalogTestStateAPITest(_CRUD):
    model = CatalogTestState
    brief_fields = ["display", "distro", "id", "url"]
    bulk_update_data = {"install": True}

    @classmethod
    def setUpTestData(cls):
        c1, c2, c3 = make_catalog("a"), make_catalog("b"), make_catalog("c")
        CatalogTestState.objects.bulk_create([
            CatalogTestState(catalog=c1, distro="debian"),
            CatalogTestState(catalog=c2, distro="debian"),
            CatalogTestState(catalog=c3, distro="debian"),
        ])
        cls.create_data = [
            {"catalog": c1.pk, "distro": "alpine", "install": True, "init": True},
            {"catalog": c2.pk, "distro": "alpine", "install": True},
            {"catalog": c3.pk, "distro": "redhat", "install": False},
        ]


class CatalogTestIntegrationAPITest(_CRUD):
    model = CatalogTestIntegration
    brief_fields = ["display", "id", "passed", "provider_service", "url"]
    bulk_update_data = {"passed": True}

    @classmethod
    def setUpTestData(cls):
        ts = CatalogTestState.objects.create(catalog=make_catalog("nextcloud"), distro="debian")
        CatalogTestIntegration.objects.bulk_create([
            CatalogTestIntegration(test_state=ts, provider_service=f"p{i}") for i in range(3)
        ])
        cls.create_data = [
            {"test_state": ts.pk, "provider_service": "openbao", "passed": True},
            {"test_state": ts.pk, "provider_service": "authentik", "passed": False},
            {"test_state": ts.pk, "provider_service": "alloy", "passed": True},
        ]


class ServiceInstanceAPITest(_CRUD):
    model = ServiceInstance
    brief_fields = ["catalog", "display", "hostname", "id", "status", "url"]
    bulk_update_data = {"status": "active"}

    @classmethod
    def setUpTestData(cls):
        cat = make_catalog("forgejo")
        for i in range(3):
            make_instance(cat, parent=make_vm(f"vm-existing-{i}"), hostname=f"existing-{i}")
        vms = [make_vm(f"vm-new-{i}") for i in range(3)]
        ct = "virtualization.virtualmachine"
        cls.create_data = [
            {"catalog": cat.pk, "parent_object_type": ct, "parent_object_id": vms[0].pk, "hostname": "n0", "status": "staged"},
            {"catalog": cat.pk, "parent_object_type": ct, "parent_object_id": vms[1].pk, "hostname": "n1", "status": "active"},
            {"catalog": cat.pk, "parent_object_type": ct, "parent_object_id": vms[2].pk, "hostname": "n2"},
        ]

    def test_catalog_fk_fields_denormalized(self):
        """The catalog FK's provider-contract fields (playbook / default_port /
        requires_database) are denormalized onto the instance, so the tofu-services
        reader resolves them in a single fetch — no separate catalog GET."""
        self.add_permissions("netbox_services.view_serviceinstance")
        cat = make_catalog(
            "wordpress", requires_database=True, default_port=443,
            playbook="applications/wordpress/baremetal/install_wordpress.yml",
        )
        inst = make_instance(cat, hostname="wp")
        url = reverse("plugins-api:netbox_services-api:serviceinstance-detail", kwargs={"pk": inst.pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["catalog_playbook"], cat.playbook)
        self.assertEqual(response.data["catalog_default_port"], 443)
        self.assertEqual(response.data["catalog_requires_database"], True)


class InstanceOpenBaoPathAPITest(_CRUD):
    model = InstanceOpenBaoPath
    brief_fields = ["display", "id", "key", "url"]
    bulk_update_data = {"path": "secret/data/renamed"}

    @classmethod
    def setUpTestData(cls):
        inst = make_instance(make_catalog("authentik"), hostname="authentik")
        InstanceOpenBaoPath.objects.bulk_create([
            InstanceOpenBaoPath(instance=inst, key=f"k{i}", path=f"secret/data/k{i}") for i in range(3)
        ])
        cls.create_data = [
            {"instance": inst.pk, "key": "admin_pass", "path": "secret/data/authentik/admin"},
            {"instance": inst.pk, "key": "db_pass", "path": "secret/data/authentik/db"},
            {"instance": inst.pk, "key": "api_token", "path": "secret/data/authentik/api"},
        ]


class ServiceInstanceConfigValueAPITest(_CRUD):
    model = ServiceInstanceConfigValue
    brief_fields = ["display", "id", "param", "url", "value"]
    bulk_update_data = {"value": "changed"}

    @classmethod
    def setUpTestData(cls):
        cat = make_catalog("forgejo")
        # STRING params so every created/updated value parses; distinct params so (instance, param)
        # stays unique. API create runs full_clean(), so each param must belong to the instance's type.
        params = [
            CatalogConfigParam.objects.create(
                catalog=cat, key=f"k{i}", value_type=IntegrationParamValueTypeChoices.STRING
            )
            for i in range(6)
        ]
        inst = make_instance(cat, hostname="forgejo")
        ServiceInstanceConfigValue.objects.bulk_create([
            ServiceInstanceConfigValue(instance=inst, param=params[i], value="v") for i in range(3)
        ])
        cls.create_data = [
            {"instance": inst.pk, "param": params[3].pk, "value": "listen"},
            {"instance": inst.pk, "param": params[4].pk, "value": "web"},
            {"instance": inst.pk, "param": params[5].pk, "value": "app"},
        ]


class ServiceInstanceExtensionAPITest(_CRUD):
    model = ServiceInstanceExtension
    brief_fields = ["display", "id", "kind", "name", "url"]
    bulk_update_data = {"enabled": False}

    @classmethod
    def setUpTestData(cls):
        inst = make_instance(make_catalog("wordpress"), hostname="wp")
        ServiceInstanceExtension.objects.bulk_create([
            ServiceInstanceExtension(instance=inst, kind=ExtensionKindChoices.PLUGIN, name=f"plugin{i}")
            for i in range(3)
        ])
        cls.create_data = [
            {"instance": inst.pk, "kind": "plugin", "name": "akismet", "version": "5.3"},
            {"instance": inst.pk, "kind": "plugin", "name": "woocommerce", "enabled": False},
            {"instance": inst.pk, "kind": "theme", "name": "twentytwentyfour", "managed": False},
        ]


class IntegrationAPITest(_CRUD):
    model = Integration
    brief_fields = ["display", "id", "type", "url"]
    bulk_update_data = {"description": "updated"}

    @classmethod
    def setUpTestData(cls):
        openbao = make_catalog("openbao")
        authentik = make_catalog("authentik")
        IntegrationCatalog.objects.create(catalog=authentik, type="openbao", requires_service="openbao")
        cls.consumer = make_instance(authentik, hostname="authentik")
        providers = [make_instance(openbao, hostname=f"openbao-{i}") for i in range(6)]
        # Existing edges (bulk_create skips the pre_save signal) — distinct providers.
        Integration.objects.bulk_create([
            Integration(consumer=cls.consumer, provider=providers[i], type="openbao") for i in range(3)
        ])
        cls.create_data = [
            {"consumer": cls.consumer.pk, "provider": providers[3].pk, "type": "openbao"},
            {"consumer": cls.consumer.pk, "provider": providers[4].pk, "type": "openbao"},
            {"consumer": cls.consumer.pk, "provider": providers[5].pk, "type": "openbao"},
        ]


class IntegrationParamAPITest(_CRUD):
    model = IntegrationParam
    brief_fields = ["display", "id", "key", "url"]
    bulk_update_data = {"value": "changed"}

    @classmethod
    def setUpTestData(cls):
        authentik = make_catalog("authentik")
        openbao = make_catalog("openbao")
        icat = IntegrationCatalog.objects.create(catalog=authentik, type="openbao", requires_service="openbao")
        # Declared catalog params for every key the tests touch (create + existing); API create runs
        # full_clean(), so each key must be declared and each value must parse for its value_type.
        for key, vt in (
            ("k0", "string"), ("k1", "string"), ("k2", "string"),
            ("db_index", "int"), ("bucket", "string"), ("from_address", "string"),
        ):
            IntegrationCatalogParam.objects.create(integration_catalog=icat, key=key, value_type=vt)
        consumer = make_instance(authentik, hostname="authentik")
        provider = make_instance(openbao, hostname="openbao")
        edge = Integration.objects.create(consumer=consumer, provider=provider, type="openbao")
        IntegrationParam.objects.bulk_create([
            IntegrationParam(integration=edge, key=f"k{i}", value="v") for i in range(3)
        ])
        cls.create_data = [
            {"integration": edge.pk, "key": "db_index", "value": "3"},
            {"integration": edge.pk, "key": "bucket", "value": "assets"},
            {"integration": edge.pk, "key": "from_address", "value": "noreply@example.com"},
        ]


class HAMirrorAPITest(_CRUD):
    model = HAMirror
    brief_fields = ["display", "id", "mirror", "primary", "url"]

    @classmethod
    def setUpTestData(cls):
        wp = make_catalog("wordpress")
        primaries = [make_instance(wp, hostname=f"wp-p{i}") for i in range(6)]
        mirrors = [make_instance(wp, hostname=f"wp-m{i}") for i in range(6)]
        HAMirror.objects.bulk_create([
            HAMirror(mirror=mirrors[i], primary=primaries[i]) for i in range(3)
        ])
        cls.create_data = [
            {"mirror": mirrors[3].pk, "primary": primaries[3].pk},
            {"mirror": mirrors[4].pk, "primary": primaries[4].pk},
            {"mirror": mirrors[5].pk, "primary": primaries[5].pk},
        ]
