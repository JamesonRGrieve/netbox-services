# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# Operator 2026-11-24 ("Move it to netbox first. All of it"; card 254):
#   - ServiceCatalog.external: an outside service (SaaS, e.g. Square) whose instances are accounts with no
#     host of ours, so ServiceInstance.parent becomes optional (ServiceInstance.clean keeps it required
#     for every hosted catalog). Existing rows all have a parent and keep it.
#   - ServiceInstanceExtension.install_tier: an app's place in its service's install order (the Frappe
#     tiers the zephyrex root kept as HCL lists). Blank on every existing row until backfilled.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("netbox_services", "0013_instanceopenbaopath_vault"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicecatalog",
            name="external",
            field=models.BooleanField(
                default=False,
                help_text="An outside service (SaaS) with no host of ours, e.g. a payment provider: its instances "
                          "are accounts with no parent, named by hostname.",
            ),
        ),
        migrations.AlterField(
            model_name="serviceinstance",
            name="parent_object_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                limit_choices_to=models.Q(("app_label", "dcim"), ("model", "device"))
                | models.Q(("app_label", "virtualization"), ("model", "virtualmachine")),
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AlterField(
            model_name="serviceinstance",
            name="parent_object_id",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="serviceinstanceextension",
            name="install_tier",
            field=models.CharField(
                blank=True,
                max_length=16,
                help_text="Where the extension installs in its service's dependency order (framework, site, "
                          "dependent, last, after_last). Blank = no install order, or not installed yet.",
            ),
        ),
    ]
