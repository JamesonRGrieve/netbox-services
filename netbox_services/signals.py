# SPDX-License-Identifier: AGPL-3.0-or-later
"""ORM hooks, connected in :meth:`NetBoxServicesConfig.ready`.

* ``pre_save`` backstop for Integration cardinality: ``Integration.clean()`` covers the form/serializer
  write paths; this catches direct ORM / seeder / migration writes that bypass ``clean()``.
* HA mirror derivation: a committed change to a guest, its guest profile, one of its service instances
  or one of their config values re-derives that guest's mirror (``ha_derive.derive_for_vm``) once the
  transaction commits. A change to a mirror re-runs nothing, because no policy matches it.
"""
from django.apps import apps
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from virtualization.models import VirtualMachine

from .ha_derive import derive_for_vm
from .models import Integration, ServiceInstance, ServiceInstanceConfigValue, validate_integration_cardinality


@receiver(pre_save, sender=Integration)
def _enforce_integration_cardinality(sender, instance, **kwargs):
    validate_integration_cardinality(instance)


def _derive_after_commit(vm_id):
    if vm_id is not None:
        transaction.on_commit(lambda: derive_for_vm(vm_id))


def _instance_vm_id(instance):
    return instance.parent_object_id if instance.parent_object_type_id is not None \
        and instance.parent_object_type.model_class() is VirtualMachine else None


@receiver(post_save, sender=VirtualMachine)
def _vm_saved(sender, instance, **kwargs):
    _derive_after_commit(instance.pk)


@receiver(post_save, sender=ServiceInstance)
def _instance_saved(sender, instance, **kwargs):
    _derive_after_commit(_instance_vm_id(instance))


@receiver(post_save, sender=ServiceInstanceConfigValue)
@receiver(post_delete, sender=ServiceInstanceConfigValue)
def _config_value_changed(sender, instance, **kwargs):
    parent = ServiceInstance.objects.filter(pk=instance.instance_id).first()
    _derive_after_commit(_instance_vm_id(parent) if parent else None)


def connect_guest_profile():
    """GuestProfile belongs to netbox-guests, so its hook connects only when that plugin is installed."""
    if apps.is_installed("netbox_guests"):
        post_save.connect(_profile_saved, sender=apps.get_model("netbox_guests", "GuestProfile"),
                          dispatch_uid="netbox_services_ha_profile")


def _profile_saved(sender, instance, **kwargs):
    _derive_after_commit(instance.virtual_machine_id)
