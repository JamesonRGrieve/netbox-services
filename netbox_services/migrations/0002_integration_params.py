# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored additive migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# Adds the per-edge integration config-param SoT: IntegrationCatalogParam (catalog-level schema —
# which params an integration TYPE accepts) + IntegrationParam (instance-level override value on
# one Integration edge). Mirrors the IntegrationCatalog→Integration + CatalogToken split.
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
_TAGS = ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag"))


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "__first__"),
        ("netbox_services", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="IntegrationCatalogParam",
            fields=[
                *_BASE,
                ("key", models.CharField(max_length=100)),
                ("value_type", models.CharField(max_length=16)),
                ("required", models.BooleanField(default=False)),
                ("default", models.CharField(blank=True, max_length=255)),
                ("secret", models.BooleanField(default=False)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("integration_catalog", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="params", to="netbox_services.integrationcatalog")),
                _TAGS,
            ],
            options={
                "verbose_name": "Integration Catalog Param",
                "ordering": ["integration_catalog", "key"],
                "constraints": [models.UniqueConstraint(fields=("integration_catalog", "key"), name="netbox_services_integrationcatalogparam_unique_catalog_key")],
            },
        ),
        migrations.CreateModel(
            name="IntegrationParam",
            fields=[
                *_BASE,
                ("key", models.CharField(max_length=100)),
                ("value", models.CharField(max_length=255)),
                ("integration", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="params", to="netbox_services.integration")),
                _TAGS,
            ],
            options={
                "verbose_name": "Integration Param",
                "ordering": ["integration", "key"],
                "constraints": [models.UniqueConstraint(fields=("integration", "key"), name="netbox_services_integrationparam_unique_integration_key")],
            },
        ),
    ]
