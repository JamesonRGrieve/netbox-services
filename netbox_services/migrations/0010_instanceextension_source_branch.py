# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# ServiceInstanceExtension gains where an extension comes from: source_url (a repository outside the
# service's default source, e.g. a Frappe app not under github.com/frappe) and branch. Additive and
# blank by default, so every existing extension keeps meaning "the service's default source".
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("netbox_services", "0009_hamirror_active_node_cloudflare_lb"),
    ]

    operations = [
        migrations.AddField(
            model_name="serviceinstanceextension",
            name="source_url",
            field=models.URLField(
                blank=True,
                help_text="Repository the extension is fetched from, when it is not in the service's default "
                          "source (e.g. a Frappe app outside github.com/frappe). Blank = the service's default "
                          "source.",
            ),
        ),
        migrations.AddField(
            model_name="serviceinstanceextension",
            name="branch",
            field=models.CharField(
                blank=True,
                help_text="Branch fetched from the source (blank = the service's default branch).",
                max_length=100,
            ),
        ),
    ]
