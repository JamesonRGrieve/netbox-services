# SPDX-License-Identifier: AGPL-3.0-or-later
"""ORM backstop for Integration cardinality. ``Integration.clean()`` covers the form/serializer
write paths; this ``pre_save`` receiver catches direct ORM / seeder / migration writes that bypass
``clean()``. Connected in :meth:`NetBoxServicesConfig.ready`."""
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Integration, validate_integration_cardinality


@receiver(pre_save, sender=Integration)
def _enforce_integration_cardinality(sender, instance, **kwargs):
    validate_integration_cardinality(instance)
