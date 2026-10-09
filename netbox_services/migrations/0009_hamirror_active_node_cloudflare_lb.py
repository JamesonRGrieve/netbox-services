# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# HAMirror gains the pair's serving roles as typed fields: active_node (which node serves) and
# cloudflare_lb (pair behind the Cloudflare load balancer). Additive with defaults, so every existing
# pair reads primary / False until set.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("netbox_services", "0008_configvalue_value_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="hamirror",
            name="active_node",
            field=models.CharField(
                choices=[("primary", "Primary"), ("mirror", "Mirror")],
                default="primary",
                help_text="Which node serves; the other pulls content from it.",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="hamirror",
            name="cloudflare_lb",
            field=models.BooleanField(
                default=False, help_text="The pair sits behind the Cloudflare load balancer."
            ),
        ),
    ]
