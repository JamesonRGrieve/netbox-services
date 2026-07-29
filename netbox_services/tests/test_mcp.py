# SPDX-License-Identifier: AGPL-3.0-or-later
"""MCP-companion model tests against a real DB (no mocks).

Covers the load-bearing rules: a companion may only be bolted onto an instance of its OWN service
type, credential fields must name a real ``InstanceOpenBaoPath`` key on the fronted instance,
capability is a catalog-owned property an instance cannot widen, the stdio/listener contradictions,
the effective-value fallbacks the provider relies on, both uniqueness constraints, and the
declared-param + typed-value contract on ``McpServerParam``.
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError
from django.db.utils import IntegrityError
from django.test import TestCase
from ipam.models import Service

from ..choices import (
    IntegrationParamValueTypeChoices, McpCapabilityChoices, McpSourceTypeChoices, McpTransportChoices,
)
from ..models import (
    CatalogMcpServer, CatalogMcpServerParam, InstanceOpenBaoPath, McpServer, McpServerParam,
)
from .utils import make_catalog, make_catalog_mcp, make_instance, make_mcp_server


class CatalogMcpServerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.catalog = make_catalog("netbox")

    def test_create_and_str(self):
        entry = make_catalog_mcp(self.catalog)
        self.assertEqual(str(entry), "netbox: netbox-mcp-server")
        self.assertTrue(entry.get_absolute_url())
        # Upstream's server is read-only; the default must not silently grant writes.
        self.assertEqual(entry.capability, McpCapabilityChoices.READ_ONLY)
        self.assertEqual(entry.transport, McpTransportChoices.HTTP)

    def test_unique_catalog_name(self):
        make_catalog_mcp(self.catalog)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CatalogMcpServer(
                catalog=self.catalog, name="netbox-mcp-server",
                source_type=McpSourceTypeChoices.PYPI, source="netbox-mcp-server",
            ).save()

    def test_same_name_allowed_on_another_catalog(self):
        other = make_catalog("semaphore")
        make_catalog_mcp(self.catalog)
        make_catalog_mcp(other)  # must not collide — uniqueness is per catalog
        self.assertEqual(CatalogMcpServer.objects.filter(name="netbox-mcp-server").count(), 2)

    def test_stdio_rejects_default_port(self):
        entry = CatalogMcpServer(
            catalog=self.catalog, name="stdio-companion", source_type=McpSourceTypeChoices.PYPI,
            source="some-mcp", transport=McpTransportChoices.STDIO, default_port=8899,
        )
        with self.assertRaises(ValidationError):
            entry.full_clean()

    def test_stdio_without_port_is_valid(self):
        CatalogMcpServer(
            catalog=self.catalog, name="stdio-companion", source_type=McpSourceTypeChoices.PYPI,
            source="some-mcp", transport=McpTransportChoices.STDIO,
        ).full_clean()


class McpServerTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.catalog = make_catalog("netbox")
        cls.instance = make_instance(cls.catalog, hostname="prod-netbox")
        cls.catalog_mcp = make_catalog_mcp(cls.catalog)
        InstanceOpenBaoPath.objects.create(
            instance=cls.instance, key="api_token", path="secret/data/agent/claude/netbox"
        )

    def test_create_and_str(self):
        companion = make_mcp_server(self.instance, self.catalog_mcp)
        self.assertIn("netbox-mcp-server", str(companion))
        self.assertTrue(companion.get_absolute_url())

    def test_unique_instance_catalog_mcp(self):
        make_mcp_server(self.instance, self.catalog_mcp)
        with self.assertRaises(IntegrityError), transaction.atomic():
            McpServer(service_instance=self.instance, catalog_mcp=self.catalog_mcp).save()

    def test_reject_companion_of_another_service_type(self):
        """You cannot bolt Semaphore's companion onto NetBox."""
        other_catalog = make_catalog("semaphore")
        foreign = make_catalog_mcp(other_catalog, name="semaphore-mcp")
        with self.assertRaises(ValidationError):
            McpServer(service_instance=self.instance, catalog_mcp=foreign).full_clean()

    def test_token_key_must_exist_on_fronted_instance(self):
        with self.assertRaises(ValidationError):
            McpServer(
                service_instance=self.instance, catalog_mcp=self.catalog_mcp, token_key="nope"
            ).full_clean()
        McpServer(
            service_instance=self.instance, catalog_mcp=self.catalog_mcp, token_key="api_token"
        ).full_clean()

    def test_auth_token_key_must_exist_on_fronted_instance(self):
        with self.assertRaises(ValidationError):
            McpServer(
                service_instance=self.instance, catalog_mcp=self.catalog_mcp, auth_token_key="absent"
            ).full_clean()

    def test_blank_credential_keys_are_allowed(self):
        """Blank auth_token_key on an http companion = deliberately unauthenticated endpoint."""
        McpServer(service_instance=self.instance, catalog_mcp=self.catalog_mcp).full_clean()

    def test_stdio_rejects_bind_address(self):
        stdio_catalog = make_catalog_mcp(
            self.catalog, name="stdio-companion", transport=McpTransportChoices.STDIO
        )
        with self.assertRaises(ValidationError):
            McpServer(
                service_instance=self.instance, catalog_mcp=stdio_catalog, bind_address="127.0.0.1"
            ).full_clean()

    def test_transport_override_drives_the_stdio_check(self):
        """An instance overriding an http catalog entry to stdio is held to the stdio contract."""
        with self.assertRaises(ValidationError):
            McpServer(
                service_instance=self.instance, catalog_mcp=self.catalog_mcp,
                transport=McpTransportChoices.STDIO, bind_address="127.0.0.1",
            ).full_clean()

    def test_effective_fallbacks(self):
        entry = make_catalog_mcp(
            self.catalog, name="pinned", default_version="1.4.0", transport=McpTransportChoices.HTTP
        )
        inherit = McpServer.objects.create(service_instance=self.instance, catalog_mcp=entry)
        self.assertEqual(inherit.effective_version, "1.4.0")
        self.assertEqual(inherit.effective_transport, McpTransportChoices.HTTP)

        override = McpServer.objects.create(
            service_instance=make_instance(self.catalog, hostname="other"),
            catalog_mcp=entry, version="1.5.0", transport=McpTransportChoices.STDIO,
        )
        self.assertEqual(override.effective_version, "1.5.0")
        self.assertEqual(override.effective_transport, McpTransportChoices.STDIO)

    def test_capability_is_catalog_owned_and_not_instance_overridable(self):
        companion = make_mcp_server(self.instance, self.catalog_mcp)
        self.assertEqual(companion.capability, McpCapabilityChoices.READ_ONLY)
        # No instance-level field can widen it; changing the TYPE changes every instance.
        self.assertFalse(any(f.name == "capability" for f in McpServer._meta.get_fields()
                             if getattr(f, "concrete", False)))
        self.catalog_mcp.capability = McpCapabilityChoices.READ_WRITE
        self.catalog_mcp.save()
        companion.refresh_from_db()
        self.assertEqual(companion.capability, McpCapabilityChoices.READ_WRITE)

    def test_listeners_are_ipam_services(self):
        """Ports live in IPAM, exactly as on ServiceInstance — no port column on this model."""
        companion = make_mcp_server(self.instance, self.catalog_mcp)
        listener = Service.objects.create(
            name="netbox-mcp", protocol="tcp", ports=[8899], parent=self.instance.parent
        )
        companion.listeners.add(listener)
        self.assertEqual(companion.listeners.count(), 1)
        self.assertFalse(any(f.name == "port" for f in McpServer._meta.get_fields()))

    def test_deleting_the_instance_removes_its_companion(self):
        instance = make_instance(self.catalog, hostname="ephemeral")
        make_mcp_server(instance, self.catalog_mcp)
        instance.delete()
        self.assertEqual(McpServer.objects.filter(service_instance_id=instance.pk).count(), 0)

    def test_catalog_entry_is_protected_while_in_use(self):
        make_mcp_server(self.instance, self.catalog_mcp)
        with self.assertRaises(ProtectedError), transaction.atomic():
            self.catalog_mcp.delete()


class McpServerParamTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.catalog = make_catalog("netbox")
        cls.instance = make_instance(cls.catalog, hostname="prod-netbox")
        cls.catalog_mcp = make_catalog_mcp(cls.catalog)
        cls.companion = make_mcp_server(cls.instance, cls.catalog_mcp)
        cls.p_bool = CatalogMcpServerParam.objects.create(
            catalog_mcp=cls.catalog_mcp, key="ENABLE_PLUGIN_DISCOVERY",
            value_type=IntegrationParamValueTypeChoices.BOOL, default="false",
        )
        cls.p_int = CatalogMcpServerParam.objects.create(
            catalog_mcp=cls.catalog_mcp, key="PORT", value_type=IntegrationParamValueTypeChoices.INT,
        )
        cls.p_secret = CatalogMcpServerParam.objects.create(
            catalog_mcp=cls.catalog_mcp, key="MCP_AUTH_TOKEN",
            value_type=IntegrationParamValueTypeChoices.SECRET, secret=True,
        )

    def test_accepts_declared_param(self):
        McpServerParam(mcp_server=self.companion, key="ENABLE_PLUGIN_DISCOVERY", value="true").full_clean()

    def test_rejects_undeclared_param(self):
        with self.assertRaises(ValidationError):
            McpServerParam(mcp_server=self.companion, key="NOT_DECLARED", value="x").full_clean()

    def test_rejects_param_declared_on_another_companion(self):
        other_catalog = make_catalog("semaphore")
        other_mcp = make_catalog_mcp(other_catalog, name="semaphore-mcp")
        CatalogMcpServerParam.objects.create(
            catalog_mcp=other_mcp, key="SEMAPHORE_PROJECT_ID",
            value_type=IntegrationParamValueTypeChoices.INT,
        )
        with self.assertRaises(ValidationError):
            McpServerParam(mcp_server=self.companion, key="SEMAPHORE_PROJECT_ID", value="1").full_clean()

    def test_typed_value_enforced(self):
        with self.assertRaises(ValidationError):
            McpServerParam(mcp_server=self.companion, key="PORT", value="notanint").full_clean()
        McpServerParam(mcp_server=self.companion, key="PORT", value="8899").full_clean()
        with self.assertRaises(ValidationError):
            McpServerParam(mcp_server=self.companion, key="ENABLE_PLUGIN_DISCOVERY", value="yes").full_clean()

    def test_secret_param_rejects_inline_value(self):
        """Secret VALUES never live in NetBox — only OpenBao path references."""
        with self.assertRaises(ValidationError):
            McpServerParam(
                mcp_server=self.companion, key="MCP_AUTH_TOKEN", value="hunter2"
            ).full_clean()
        McpServerParam(
            mcp_server=self.companion, key="MCP_AUTH_TOKEN", value="secret/data/agent/claude/mcp"
        ).full_clean()

    def test_unique_mcp_server_key(self):
        McpServerParam.objects.create(mcp_server=self.companion, key="PORT", value="8899")
        with self.assertRaises(IntegrityError), transaction.atomic():
            McpServerParam(mcp_server=self.companion, key="PORT", value="9000").save()

    def test_deleting_companion_removes_its_params(self):
        McpServerParam.objects.create(mcp_server=self.companion, key="PORT", value="8899")
        pk = self.companion.pk
        self.companion.delete()
        self.assertEqual(McpServerParam.objects.filter(mcp_server_id=pk).count(), 0)
