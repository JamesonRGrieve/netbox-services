# SPDX-License-Identifier: AGPL-3.0-or-later
"""netbox-services: NetBox as the source of truth for application **install-data + service
integrations**. The catalog layer (``ServiceCatalog`` + children) is the upstream that
``about.json`` is generated *from*; the instance layer (``ServiceInstance`` + ``Integration``
+ ``HAMirror``) models deployed apps, their instance-to-instance integration edges with
cardinality, and HA mirror pairings — the data the ``tofu-services`` provider reads and the
Semaphore reconciler acts on.

**Secret policy:** credential and provides-token *references* only (``InstanceOpenBaoPath`` keys
an OpenBao path); secret values never live here. **No config_context, no CustomField data-blob** —
every attribute is a real typed column or a child row, mirroring the sibling
``netbox-system-services`` / ``netbox-guests`` discipline.
"""
from netbox.plugins import PluginConfig

__version__ = "0.0.1"


class NetBoxServicesConfig(PluginConfig):
    name = "netbox_services"
    verbose_name = "NetBox Services"
    description = "Native SoT for application install-data + service integrations (catalog, instances, edges, HA)"
    version = __version__
    author = "Jameson"
    base_url = "services"
    min_version = "4.6.0"
    max_version = "4.6.99"

    def ready(self):
        super().ready()
        from . import signals  # noqa: F401  (connects the cardinality pre_save backstop)


config = NetBoxServicesConfig
