# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# HA mirrors derived in NetBox (operator 2026-11-27, Zephyrex Software card 404): HAMirrorPolicy (the
# derivation rule), CatalogConfigParam.mirror_mode/mirror_value (what a mirror instance takes from its
# primary) and HAMirror.seeded (the mirror holds the primary's data). Additive with defaults: every
# param copies, every pair reads unseeded until set.
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
        ("dcim", "__first__"),
        ("extras", "__first__"),
        ("ipam", "__first__"),
        ("virtualization", "__first__"),
        ("netbox_services", "0016_instanceopenbaopath_generator_choices"),
    ]

    operations = [
        migrations.AddField(
            model_name="catalogconfigparam",
            name="mirror_mode",
            field=models.CharField(
                choices=[("copy", "Copy"), ("omit", "Omit"), ("fixed", "Fixed")],
                default="copy",
                help_text="What an HA mirror instance stores for this param: the primary's value (copy), nothing (omit), "
                          "or mirror_value (fixed).",
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name="catalogconfigparam",
            name="mirror_value",
            field=models.TextField(blank=True, help_text="The mirror's value when mirror_mode is fixed."),
        ),
        migrations.AddField(
            model_name="hamirror",
            name="seeded",
            field=models.BooleanField(
                default=False,
                help_text="The mirror holds the primary's data (seed restore done), so replication may run both ways.",
            ),
        ),
        migrations.CreateModel(
            name="HAMirrorPolicy",
            fields=[
                *_BASE,
                ("name", models.CharField(max_length=100, unique=True)),
                ("enabled", models.BooleanField(default=True)),
                ("source_name_prefix", models.CharField(help_text="Primary guest name prefix, e.g. prod-wp-.", max_length=64)),
                ("mirror_name_prefix", models.CharField(help_text="Mirror guest name prefix, e.g. mirror-wp-.", max_length=64)),
                ("vmid_offset", models.PositiveIntegerField(help_text="Mirror VMID = primary VMID + this (320 + 10700 = 11020).")),
                ("interface_name", models.CharField(default="eth0", max_length=64)),
                ("gateway", models.GenericIPAddressField(help_text="Set explicitly on every mirror interface.", protocol="IPv4")),
                ("replication_name_prefix", models.CharField(blank=True, default="wp-", max_length=64)),
                ("replication_semi_sync", models.BooleanField(default=True)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("source_cluster", models.ForeignKey(help_text="Where primaries run.", on_delete=django.db.models.deletion.PROTECT, related_name="+", to="virtualization.cluster")),
                ("target_cluster", models.ForeignKey(help_text="Where mirrors run.", on_delete=django.db.models.deletion.PROTECT, related_name="+", to="virtualization.cluster")),
                ("target_device", models.ForeignKey(blank=True, help_text="The mirror guest's host device in the target cluster.", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="dcim.device")),
                ("vlan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="ipam.vlan")),
                ("prefix", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="ipam.prefix")),
                ("catalogs", models.ManyToManyField(help_text="Services the mirror carries.", related_name="+", to="netbox_services.servicecatalog")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "verbose_name": "HA Mirror Policy",
                "verbose_name_plural": "HA Mirror Policies",
                "ordering": ["name"],
            },
        ),
    ]
