# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored additive migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# Adds the MCP-companion SoT: the catalog half (what a companion IS, incl. its trust level) and the
# instance half (that a specific ServiceInstance runs one), plus the typed param pair so companion
# env knobs never become an untyped blob.
#
# Notes matching prior migrations in this plugin:
#   - transport / capability / source_type / value_type carry no `choices=` here, because NetBox
#     ChoiceSets are not serialized into migrations (same as 0002/0003/0005 value_type, 0006
#     secret_kind).
#   - `listeners` is an M2M to ipam.Service, mirroring ServiceInstance.listeners: ports live in
#     IPAM, never as a column here. Hence the ipam dependency.
#   - token_key / auth_token_key are plain CharFields naming an InstanceOpenBaoPath key on the
#     fronted instance; they are references validated in clean(), not FKs, because the target is a
#     key *within* the instance's own credential rows.
import django.db.models.deletion
import taggit.managers
import utilities.json
from django.db import migrations, models

_BASE = [
    ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
    ("created", models.DateTimeField(auto_now_add=True, blank=True, null=True)),
    ("last_updated", models.DateTimeField(auto_now=True, blank=True, null=True)),
    ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
]


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "__first__"),
        ("ipam", "__first__"),
        ("netbox_services", "0006_rotation_policy"),
    ]
    operations = [
        migrations.CreateModel(
            name="CatalogMcpServer",
            fields=[
                *_BASE,
                ("name", models.CharField(max_length=200)),
                ("source_type", models.CharField(max_length=16)),
                ("source", models.CharField(max_length=255)),
                ("default_version", models.CharField(blank=True, max_length=100)),
                ("transport", models.CharField(default="http", max_length=16)),
                ("default_port", models.PositiveIntegerField(blank=True, null=True)),
                ("capability", models.CharField(default="read_only", max_length=16)),
                ("upstream_url", models.URLField(blank=True)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("catalog", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mcp_servers", to="netbox_services.servicecatalog")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "verbose_name": "Catalog MCP Server",
                "ordering": ["catalog", "name"],
                "constraints": [models.UniqueConstraint(fields=("catalog", "name"), name="netbox_services_catalogmcpserver_unique_catalog_name")],
            },
        ),
        migrations.CreateModel(
            name="CatalogMcpServerParam",
            fields=[
                *_BASE,
                ("key", models.CharField(max_length=100)),
                ("value_type", models.CharField(max_length=16)),
                ("required", models.BooleanField(default=False)),
                ("default", models.CharField(blank=True, max_length=255)),
                ("secret", models.BooleanField(default=False)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("catalog_mcp", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="params", to="netbox_services.catalogmcpserver")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "verbose_name": "Catalog MCP Server Param",
                "ordering": ["catalog_mcp", "key"],
                "constraints": [models.UniqueConstraint(fields=("catalog_mcp", "key"), name="netbox_services_catalogmcpserverparam_unique_catalog_mcp_key")],
            },
        ),
        migrations.CreateModel(
            name="McpServer",
            fields=[
                *_BASE,
                ("version", models.CharField(blank=True, max_length=100)),
                ("transport", models.CharField(blank=True, max_length=16)),
                ("status", models.CharField(default="staged", max_length=20)),
                ("bind_address", models.CharField(blank=True, max_length=255)),
                ("token_key", models.CharField(blank=True, max_length=100)),
                ("auth_token_key", models.CharField(blank=True, max_length=100)),
                ("autostart", models.BooleanField(default=True)),
                ("managed", models.BooleanField(default=True)),
                ("catalog_mcp", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="instances", to="netbox_services.catalogmcpserver")),
                ("service_instance", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mcp_servers", to="netbox_services.serviceinstance")),
                ("listeners", models.ManyToManyField(blank=True, related_name="mcp_servers", to="ipam.service")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "verbose_name": "MCP Server",
                "ordering": ["service_instance", "catalog_mcp"],
                "constraints": [models.UniqueConstraint(fields=("service_instance", "catalog_mcp"), name="netbox_services_mcpserver_unique_instance_catalog_mcp")],
            },
        ),
        migrations.CreateModel(
            name="McpServerParam",
            fields=[
                *_BASE,
                ("key", models.CharField(max_length=100)),
                ("value", models.CharField(max_length=255)),
                ("mcp_server", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="params", to="netbox_services.mcpserver")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "verbose_name": "MCP Server Param",
                "ordering": ["mcp_server", "key"],
                "constraints": [models.UniqueConstraint(fields=("mcp_server", "key"), name="netbox_services_mcpserverparam_unique_mcp_server_key")],
            },
        ),
    ]
