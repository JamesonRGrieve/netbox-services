# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored initial migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# The ServiceInstance parent GFK (parent_object_type/_id) + limit_choices_to and the ipam.Service
# M2M target NetBox 4.6 — re-confirm against the pinned version.
import django.contrib.postgres.fields
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

# ServiceInstance.parent GFK is limited to a guest VM or a raw-OS device.
_PARENT_CT_LIMIT = models.Q(
    models.Q(("app_label", "dcim"), ("model", "device")),
    models.Q(("app_label", "virtualization"), ("model", "virtualmachine")),
    _connector="OR",
)


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("contenttypes", "0001_initial"),
        # NetBox 4.6 squashes core app migrations (dcim/extras/ipam/virtualization
        # → 0001_squashed*), so pin to __first__ rather than the nonexistent 0001_initial.
        ("dcim", "__first__"),
        ("extras", "__first__"),
        ("ipam", "__first__"),
        ("virtualization", "__first__"),
    ]
    operations = [
        migrations.CreateModel(
            name="ServiceCatalog",
            fields=[
                *_BASE,
                ("name", models.SlugField(max_length=100, unique=True)),
                ("display_name", models.CharField(max_length=200)),
                ("description", models.CharField(blank=True, max_length=500)),
                ("repo", models.URLField(blank=True)),
                ("docs", models.URLField(blank=True)),
                ("license", models.CharField(blank=True, max_length=100)),
                ("tier", models.PositiveSmallIntegerField(default=1)),
                ("requires_gpu", models.BooleanField(default=False)),
                ("default_port", models.PositiveIntegerField(blank=True, null=True)),
                ("install_memory", models.PositiveIntegerField(blank=True, null=True)),
                ("install_cores", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("runtime_memory", models.PositiveIntegerField(blank=True, null=True)),
                ("runtime_cores", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("disk", models.PositiveIntegerField(blank=True, null=True)),
                ("playbook", models.CharField(blank=True, max_length=255)),
                ("init_playbook", models.CharField(blank=True, max_length=255)),
                ("customize_playbook", models.CharField(blank=True, max_length=255)),
                ("unlock_playbook", models.CharField(blank=True, max_length=255)),
                ("health_endpoint", models.CharField(blank=True, max_length=255)),
                ("health_status_codes", django.contrib.postgres.fields.ArrayField(base_field=models.PositiveSmallIntegerField(), blank=True, default=list, size=None)),
                ("requires_database", models.BooleanField(default=False)),
                ("database_type", models.CharField(blank=True, max_length=16)),
                ("requires_cache", models.BooleanField(default=False)),
                ("ha_strategy", models.CharField(default="none", max_length=32)),
                ("ingress_haproxy_backup", models.BooleanField(default=False)),
                _TAGS,
            ],
            options={"verbose_name": "Service Catalog", "verbose_name_plural": "Service Catalog", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="CatalogCredential",
            fields=[
                *_BASE,
                ("cred_id", models.CharField(max_length=100)),
                ("length", models.PositiveSmallIntegerField(default=24)),
                ("deploy_var", models.CharField(max_length=200)),
                ("catalog", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="credentials", to="netbox_services.servicecatalog")),
                _TAGS,
            ],
            options={
                "verbose_name": "Catalog Credential",
                "ordering": ["catalog", "cred_id"],
                "constraints": [models.UniqueConstraint(fields=("catalog", "cred_id"), name="netbox_services_catalogcredential_unique")],
            },
        ),
        migrations.CreateModel(
            name="CatalogToken",
            fields=[
                *_BASE,
                ("name", models.CharField(max_length=100)),
                ("output_var", models.CharField(max_length=200)),
                ("catalog", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tokens", to="netbox_services.servicecatalog")),
                _TAGS,
            ],
            options={
                "verbose_name": "Catalog Token",
                "ordering": ["catalog", "name"],
                "constraints": [models.UniqueConstraint(fields=("catalog", "name"), name="netbox_services_catalogtoken_unique")],
            },
        ),
        migrations.CreateModel(
            name="CatalogSecondaryPort",
            fields=[
                *_BASE,
                ("port", models.PositiveIntegerField()),
                ("protocol", models.CharField(default="tcp", max_length=8)),
                ("name", models.CharField(blank=True, max_length=100)),
                ("catalog", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="secondary_ports", to="netbox_services.servicecatalog")),
                _TAGS,
            ],
            options={
                "verbose_name": "Catalog Secondary Port",
                "ordering": ["catalog", "port"],
                "constraints": [models.UniqueConstraint(fields=("catalog", "port", "protocol"), name="netbox_services_catalogsecondaryport_unique")],
            },
        ),
        migrations.CreateModel(
            name="IntegrationCatalog",
            fields=[
                *_BASE,
                ("type", models.CharField(max_length=100)),
                ("requires_service", models.CharField(max_length=100)),
                ("requires_tokens", django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=100), blank=True, default=list, size=None)),
                ("playbook", models.CharField(blank=True, max_length=255)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("provider_scope", models.CharField(default="shared", max_length=16)),
                ("consumer_max", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("catalog", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="integration_catalog", to="netbox_services.servicecatalog")),
                _TAGS,
            ],
            options={
                "verbose_name": "Integration Catalog",
                "verbose_name_plural": "Integration Catalog",
                "ordering": ["catalog", "type"],
                "constraints": [models.UniqueConstraint(fields=("catalog", "type"), name="netbox_services_integrationcatalog_unique")],
            },
        ),
        migrations.CreateModel(
            name="CatalogTestState",
            fields=[
                *_BASE,
                ("distro", models.CharField(max_length=16)),
                ("install", models.BooleanField(default=False)),
                ("init", models.BooleanField(default=False)),
                ("customize", models.BooleanField(default=False)),
                ("unlock", models.BooleanField(default=False)),
                ("peak_memory_mb", models.PositiveIntegerField(blank=True, null=True)),
                ("peak_cpu_load", models.FloatField(blank=True, null=True)),
                ("install_duration_s", models.PositiveIntegerField(blank=True, null=True)),
                ("catalog", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="test_states", to="netbox_services.servicecatalog")),
                _TAGS,
            ],
            options={
                "verbose_name": "Catalog Test State",
                "ordering": ["catalog", "distro"],
                "constraints": [models.UniqueConstraint(fields=("catalog", "distro"), name="netbox_services_catalogteststate_unique")],
            },
        ),
        migrations.CreateModel(
            name="CatalogTestIntegration",
            fields=[
                *_BASE,
                ("provider_service", models.CharField(max_length=100)),
                ("passed", models.BooleanField(default=False)),
                ("test_state", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="integrations", to="netbox_services.catalogteststate")),
                _TAGS,
            ],
            options={
                "verbose_name": "Catalog Test Integration",
                "ordering": ["test_state", "provider_service"],
                "constraints": [models.UniqueConstraint(fields=("test_state", "provider_service"), name="netbox_services_catalogtestintegration_unique")],
            },
        ),
        migrations.CreateModel(
            name="ServiceInstance",
            fields=[
                *_BASE,
                ("parent_object_id", models.PositiveBigIntegerField()),
                ("hostname", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(default="staged", max_length=20)),
                ("actual_memory", models.PositiveIntegerField(blank=True, null=True)),
                ("actual_cores", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("actual_disk", models.PositiveIntegerField(blank=True, null=True)),
                ("catalog", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="instances", to="netbox_services.servicecatalog")),
                ("parent_object_type", models.ForeignKey(limit_choices_to=_PARENT_CT_LIMIT, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="contenttypes.contenttype")),
                ("listeners", models.ManyToManyField(blank=True, related_name="service_instances", to="ipam.service")),
                _TAGS,
            ],
            options={
                "verbose_name": "Service Instance",
                "ordering": ["catalog", "hostname"],
                "indexes": [models.Index(fields=["parent_object_type", "parent_object_id"], name="netbox_serv_parent__idx")],
            },
        ),
        migrations.CreateModel(
            name="InstanceOpenBaoPath",
            fields=[
                *_BASE,
                ("key", models.CharField(max_length=100)),
                ("path", models.CharField(max_length=255)),
                ("instance", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="openbao_paths", to="netbox_services.serviceinstance")),
                _TAGS,
            ],
            options={
                "verbose_name": "Instance OpenBao Path",
                "ordering": ["instance", "key"],
                "constraints": [models.UniqueConstraint(fields=("instance", "key"), name="netbox_services_instanceopenbaopath_unique")],
            },
        ),
        migrations.CreateModel(
            name="Integration",
            fields=[
                *_BASE,
                ("type", models.CharField(max_length=100)),
                ("requires_tokens", django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=100), blank=True, default=list, size=None)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("consumer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="integrations_out", to="netbox_services.serviceinstance")),
                ("provider", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="integrations_in", to="netbox_services.serviceinstance")),
                _TAGS,
            ],
            options={
                "verbose_name": "Integration",
                "ordering": ["consumer", "type", "provider"],
                "constraints": [models.UniqueConstraint(fields=("consumer", "type", "provider"), name="netbox_services_integration_unique")],
            },
        ),
        migrations.CreateModel(
            name="HAMirror",
            fields=[
                *_BASE,
                ("mirror", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ha_mirror_of", to="netbox_services.serviceinstance")),
                ("primary", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ha_mirrors", to="netbox_services.serviceinstance")),
                _TAGS,
            ],
            options={
                "verbose_name": "HA Mirror",
                "ordering": ["primary", "mirror"],
                "constraints": [models.UniqueConstraint(fields=("mirror", "primary"), name="netbox_services_hamirror_unique")],
            },
        ),
    ]
