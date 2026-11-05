# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# ServiceInstanceExtension gains `module` (the import/app name when it differs from `name`, e.g. a
# NetBox plugin's Django app label: package netbox-plugin-dns loads as netbox_dns) and `position`
# (load order among the instance's extensions of one kind, e.g. NetBox's PLUGINS order). Lets the
# NetBox service's own plugin set live in NetBox instead of the root (operator 2026-11-05).
# Additive, blank/null by default, so every existing extension is unchanged.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("netbox_services", "0011_instanceopenbaopath_field"),
    ]

    operations = [
        migrations.AddField(
            model_name="serviceinstanceextension",
            name="module",
            field=models.CharField(
                blank=True,
                help_text="Import/app name when it differs from name (e.g. a NetBox plugin's Django app label). "
                          "Blank = name.",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="serviceinstanceextension",
            name="position",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                help_text="Load order among this instance's extensions of the same kind (e.g. NetBox PLUGINS "
                          "order). Blank = unordered.",
            ),
        ),
    ]
