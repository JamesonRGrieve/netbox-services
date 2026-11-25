# SPDX-License-Identifier: AGPL-3.0-or-later
# Hand-authored migration (NetBox disables makemigrations in production). Verify with:
#   python manage.py makemigrations netbox_services --check --dry-run   (on a dev/ephemeral NetBox)
# InstanceOpenBaoPath.generator gains fernet32, ed25519, ed25519_public and config (operator 2026-11-25 via
# Tofu: "Yes, move them", fixed fields "marked 'config'"; ZEPHYREX-SECRET-MARKER-SPEC 57ed26df). Choices only:
# every existing row keeps its value.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("netbox_services", "0015_instanceopenbaopath_generator"),
    ]

    operations = [
        migrations.AlterField(
            model_name="instanceopenbaopath",
            name="generator",
            field=models.CharField(
                blank=True,
                default="",
                max_length=30,
                choices=[
                    ("", "Supplied"),
                    ("alnum32", "32 letters and digits"),
                    ("policy32", "32 chars, lower/upper/digit/special (-_.)"),
                    ("fernet32", "32 random bytes, URL-safe base64 (Fernet)"),
                    ("ed25519", "ed25519 private key (OpenSSH)"),
                    ("ed25519_public", "the same key's public half"),
                    ("config", "a copy of the instance's config value"),
                ],
                help_text="How the pipeline generates the value at path + effective field (alnum32, policy32, fernet32, "
                          "ed25519, ed25519_public), or config (a copy of the instance's <catalog>_<key> config value). "
                          "Blank = supplied, never generated or overwritten. Pointers at one path + effective field "
                          "may not name two different generators; blank beside a generator is allowed (the consumer "
                          "checks whole-leaf marking). ed25519_public needs an ed25519 pointer at the same path.",
            ),
        ),
    ]
