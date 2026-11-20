# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# InstanceOpenBaoPath gains `vault`: the OpenBao instance holding the path when it is not the owner's
# own vault (a cross-OU read). Blank on every existing row, so effective_vault's tenant rule applies
# (card 407: one vault per client OU; operator 2026-11-20 "Link in NetBox").
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("netbox_services", "0012_instanceextension_module_position"),
    ]

    operations = [
        migrations.AddField(
            model_name="instanceopenbaopath",
            name="vault",
            field=models.ForeignKey(
                blank=True,
                help_text="The OpenBao instance holding path, when it is not the owner's own vault "
                          "(a cross-OU read). Blank = effective_vault's tenant rule.",
                limit_choices_to={"catalog__name": "openbao"},
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="vault_paths",
                to="netbox_services.serviceinstance",
            ),
        ),
    ]
