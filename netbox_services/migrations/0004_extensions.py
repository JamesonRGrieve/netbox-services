# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored additive migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# Adds the plugin/app/theme/module inventory SoT: CatalogExtension (catalog-level known/default
# extensions of a service TYPE) + ServiceInstanceExtension (the per-instance declared inventory,
# with per-extension version/enabled/managed — arbitrary, no CatalogExtension FK).
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
        ("netbox_services", "0003_config_params"),
    ]
    operations = [
        migrations.CreateModel(
            name="CatalogExtension",
            fields=[
                *_BASE,
                ("kind", models.CharField(max_length=16)),
                ("name", models.CharField(max_length=200)),
                ("default_version", models.CharField(blank=True, max_length=100)),
                ("required", models.BooleanField(default=False)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("catalog", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="extensions", to="netbox_services.servicecatalog")),
                _TAGS,
            ],
            options={
                "verbose_name": "Catalog Extension",
                "ordering": ["catalog", "kind", "name"],
                "constraints": [models.UniqueConstraint(fields=("catalog", "kind", "name"), name="netbox_services_catalogextension_unique_catalog_kind_name")],
            },
        ),
        migrations.CreateModel(
            name="ServiceInstanceExtension",
            fields=[
                *_BASE,
                ("kind", models.CharField(max_length=16)),
                ("name", models.CharField(max_length=200)),
                ("version", models.CharField(blank=True, max_length=100)),
                ("enabled", models.BooleanField(default=True)),
                ("managed", models.BooleanField(default=True)),
                ("instance", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="extensions", to="netbox_services.serviceinstance")),
                _TAGS,
            ],
            options={
                "verbose_name": "Service Instance Extension",
                "ordering": ["instance", "kind", "name"],
                "constraints": [models.UniqueConstraint(fields=("instance", "kind", "name"), name="netbox_services_serviceinstanceextension_unique_instance_kind_name")],
            },
        ),
    ]
