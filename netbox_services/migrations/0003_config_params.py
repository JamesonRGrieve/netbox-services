# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored additive migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# Adds the per-service declarative-config SoT: CatalogConfigParam (catalog-level schema — which
# config attributes a service TYPE accepts) + ServiceInstanceConfigValue (instance-level override
# value on one ServiceInstance). Mirrors the IntegrationCatalogParam→IntegrationParam split.
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
        ("netbox_services", "0002_integration_params"),
    ]
    operations = [
        migrations.CreateModel(
            name="CatalogConfigParam",
            fields=[
                *_BASE,
                ("key", models.CharField(max_length=100)),
                ("value_type", models.CharField(max_length=16)),
                ("required", models.BooleanField(default=False)),
                ("default", models.CharField(blank=True, max_length=255)),
                ("secret", models.BooleanField(default=False)),
                ("provider_attr", models.CharField(blank=True, max_length=200)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("catalog", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="config_params", to="netbox_services.servicecatalog")),
                _TAGS,
            ],
            options={
                "verbose_name": "Catalog Config Param",
                "ordering": ["catalog", "key"],
                "constraints": [models.UniqueConstraint(fields=("catalog", "key"), name="netbox_services_catalogconfigparam_unique_catalog_key")],
            },
        ),
        migrations.CreateModel(
            name="ServiceInstanceConfigValue",
            fields=[
                *_BASE,
                ("value", models.CharField(max_length=255)),
                ("instance", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="config_values", to="netbox_services.serviceinstance")),
                ("param", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="instance_values", to="netbox_services.catalogconfigparam")),
                _TAGS,
            ],
            options={
                "verbose_name": "Service Instance Config Value",
                "ordering": ["instance", "param"],
                "constraints": [models.UniqueConstraint(fields=("instance", "param"), name="netbox_services_serviceinstanceconfigvalue_unique_instance_param")],
            },
        ),
    ]
