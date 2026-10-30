# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# InstanceOpenBaoPath gains `field`: the key inside the secret when it differs from the logical
# key, so a pointer can follow the OpenBao grammar's purpose leaves (admin -> password, api -> token)
# while the consumer keeps its own name. Additive and blank by default, so every existing pointer
# keeps reading data[key].
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("netbox_services", "0010_instanceextension_source_branch"),
    ]

    operations = [
        migrations.AddField(
            model_name="instanceopenbaopath",
            name="field",
            field=models.CharField(
                blank=True,
                help_text="Key inside the secret at path, when it differs from key (blank = key).",
                max_length=100,
            ),
        ),
    ]
