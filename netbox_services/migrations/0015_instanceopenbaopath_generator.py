# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# InstanceOpenBaoPath gains `generator`: whether the pipeline generates the value at path + effective field,
# and to which shape. Blank (supplied) on every existing row, so nothing changes until a row is marked
# (operator 2026-11-25 via Tofu: "A plugin field"; OMG-SECRET-MARKER-SPEC e91f05f5).
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("netbox_services", "0014_external_instances_install_tier"),
    ]

    operations = [
        migrations.AddField(
            model_name="instanceopenbaopath",
            name="generator",
            field=models.CharField(
                blank=True,
                default="",
                max_length=30,
                choices=[("", "Supplied"), ("alnum32", "32 letters and digits"),
                         ("policy32", "32 chars, lower/upper/digit/special (-_.)")],
                help_text="How the pipeline generates the value at path + effective field (alnum32, policy32). "
                          "Blank = supplied, never generated or overwritten. Pointers at one path + effective field "
                          "may not name two different generators; blank beside a generator is allowed (the consumer "
                          "checks whole-leaf marking).",
            ),
        ),
    ]
