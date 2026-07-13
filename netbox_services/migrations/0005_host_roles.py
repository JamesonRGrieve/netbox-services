# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored additive migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# Adds the host-role SoT: HostRole (a scoped ansible role/task-file catalog entry) + HostRoleParam
# (its typed var schema, mirroring CatalogConfigParam) + HostRoleAssignment (which target — a guest
# VM or raw-OS device, GFK-limited like ServiceInstance.parent — runs the role, and in what apply
# order) + HostRoleAssignmentVar (per-assignment var overrides, mirroring ServiceInstanceConfigValue).
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

# HostRoleAssignment.target GFK is limited to a guest VM or a raw-OS device — the same set as
# ServiceInstance.parent (netbox_services.models.PARENT_CT_LIMIT).
_TARGET_CT_LIMIT = models.Q(
    models.Q(("app_label", "dcim"), ("model", "device")),
    models.Q(("app_label", "virtualization"), ("model", "virtualmachine")),
    _connector="OR",
)


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0001_initial"),
        ("extras", "__first__"),
        # NetBox 4.6 squashes core app migrations, so pin to __first__ rather than a nonexistent
        # 0001_initial (mirrors 0001_initial.py's ServiceInstance.parent dependency).
        ("dcim", "__first__"),
        ("virtualization", "__first__"),
        ("netbox_services", "0004_extensions"),
    ]
    operations = [
        migrations.CreateModel(
            name="HostRole",
            fields=[
                *_BASE,
                ("name", models.SlugField(max_length=100, unique=True)),
                ("display_name", models.CharField(max_length=200)),
                ("description", models.CharField(blank=True, max_length=500)),
                ("playbook", models.CharField(blank=True, max_length=255)),
                ("ansible_tags", django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=100), blank=True, default=list, size=None)),
                ("idempotent", models.BooleanField(default=True)),
                _TAGS,
            ],
            options={"verbose_name": "Host Role", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="HostRoleParam",
            fields=[
                *_BASE,
                ("key", models.CharField(max_length=100)),
                ("value_type", models.CharField(max_length=16)),
                ("required", models.BooleanField(default=False)),
                ("default", models.CharField(blank=True, max_length=255)),
                ("secret", models.BooleanField(default=False)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="params", to="netbox_services.hostrole")),
                _TAGS,
            ],
            options={
                "verbose_name": "Host Role Param",
                "ordering": ["role", "key"],
                "constraints": [models.UniqueConstraint(fields=("role", "key"), name="netbox_services_hostroleparam_unique_role_key")],
            },
        ),
        migrations.CreateModel(
            name="HostRoleAssignment",
            fields=[
                *_BASE,
                ("target_object_id", models.PositiveBigIntegerField()),
                ("order", models.PositiveSmallIntegerField(default=0)),
                ("enabled", models.BooleanField(default=True)),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assignments", to="netbox_services.hostrole")),
                ("target_object_type", models.ForeignKey(limit_choices_to=_TARGET_CT_LIMIT, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="contenttypes.contenttype")),
                _TAGS,
            ],
            options={
                "verbose_name": "Host Role Assignment",
                "ordering": ["target_object_type", "target_object_id", "order", "role"],
                "indexes": [models.Index(fields=["target_object_type", "target_object_id"], name="netbox_serv_hr_target_idx")],
                "constraints": [models.UniqueConstraint(fields=("target_object_type", "target_object_id", "role"), name="netbox_services_hostroleassignment_unique_target_role")],
            },
        ),
        migrations.CreateModel(
            name="HostRoleAssignmentVar",
            fields=[
                *_BASE,
                ("value", models.CharField(max_length=255)),
                ("assignment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vars", to="netbox_services.hostroleassignment")),
                ("param", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignment_values", to="netbox_services.hostroleparam")),
                _TAGS,
            ],
            options={
                "verbose_name": "Host Role Assignment Var",
                "ordering": ["assignment", "param"],
                "constraints": [models.UniqueConstraint(fields=("assignment", "param"), name="netbox_services_hostroleassignmentvar_unique_assignment_param")],
            },
        ),
    ]
