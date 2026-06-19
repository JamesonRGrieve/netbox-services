# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared test helpers (real objects, no mocks). ``make_vm`` builds a core virtualization VM via an
idempotent ClusterType/Cluster (the same pattern as netbox-guests); ``make_catalog`` /
``make_instance`` build the plugin's own rows. A ``dcim.Device`` parent uses the framework's
``create_test_device``."""
from virtualization.models import Cluster, ClusterType, VirtualMachine
from ..models import ServiceCatalog, ServiceInstance


def make_vm(name, cluster_name="core"):
    ctype, _ = ClusterType.objects.get_or_create(name="PVE", slug="pve")
    cluster, _ = Cluster.objects.get_or_create(name=cluster_name, type=ctype)
    return VirtualMachine.objects.create(name=name, cluster=cluster)


def make_catalog(name, **kwargs):
    defaults = {
        "display_name": name.title(),
        "default_port": 3000,
        "playbook": f"baremetal/install_{name}.yml",
    }
    defaults.update(kwargs)
    return ServiceCatalog.objects.create(name=name, **defaults)


def make_instance(catalog, parent=None, hostname="host", **kwargs):
    parent = parent or make_vm(f"vm-{hostname}")
    return ServiceInstance.objects.create(catalog=catalog, parent=parent, hostname=hostname, **kwargs)
