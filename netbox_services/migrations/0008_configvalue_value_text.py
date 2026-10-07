# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# ServiceInstanceConfigValue.value: CharField(255) -> TextField, so a whole config file (an adopted
# site's live Apache vhost, 284-1305 chars on the OMG fleet) can be recorded as intent. Widening only;
# every existing row fits unchanged.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("netbox_services", "0007_mcp_servers"),
    ]

    operations = [
        migrations.AlterField(
            model_name="serviceinstanceconfigvalue",
            name="value",
            field=models.TextField(
                help_text="Rendered per value_type (list = newline-delimited; secret = OpenBao path). Unbounded, so a "
                "whole config file (e.g. an adopted site's live vhost) fits exactly."
            ),
        ),
    ]
