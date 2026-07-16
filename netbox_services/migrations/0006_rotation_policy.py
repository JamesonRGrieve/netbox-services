# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored additive migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# Adds the rotation-policy SoT. Secret values remain in OpenBao; this model stores only references,
# cadence/trigger intent, the atomic host role (nullable — on-demand rotations may predate their
# automation), and the complete service-consumer fan-out. secret_kind carries no `choices=` here
# because NetBox ChoiceSets are not serialized into migrations (matching every prior migration in
# this plugin, e.g. 0002/0003/0005's value_type).
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
        ("netbox_services", "0005_host_roles"),
    ]
    operations = [
        migrations.CreateModel(
            name="RotationPolicy",
            fields=[
                *_BASE,
                ("name", models.SlugField(max_length=100)),
                ("secret_kind", models.CharField(max_length=32)),
                ("openbao_path", models.CharField(max_length=255)),
                ("cadence_days", models.PositiveIntegerField(blank=True, null=True)),
                ("last_rotated_at", models.DateTimeField(blank=True, null=True)),
                ("next_due_at", models.DateTimeField(blank=True, null=True)),
                ("trigger_version", models.PositiveBigIntegerField(default=0)),
                ("semaphore_schedule_ref", models.CharField(blank=True, max_length=255)),
                ("enabled", models.BooleanField(default=True)),
                ("host_role", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="rotation_policies", to="netbox_services.hostrole")),
                ("instance", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rotation_policies", to="netbox_services.serviceinstance")),
                ("consumers", models.ManyToManyField(blank=True, related_name="consumed_rotation_policies", to="netbox_services.serviceinstance")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "verbose_name": "Rotation Policy",
                "ordering": ["instance", "name"],
                "constraints": [models.UniqueConstraint(fields=("instance", "name"), name="netbox_services_rotationpolicy_unique_instance_name")],
            },
        ),
    ]
