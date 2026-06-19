# SPDX-License-Identifier: AGPL-3.0-or-later
"""REST serializers — the contract the ``tofu-services`` provider and the about.json seeder read.

The ``ServiceInstance.parent`` GFK follows the core ``ipam.Service`` pattern: ``parent_object_type``
(a ``ContentTypeField``) + ``parent_object_id`` are the writable pair, ``parent`` is a read-only
nested representation. ``listeners`` is a writable nested M2M to ``ipam.Service``."""
from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema_field
from ipam.api.serializers import ServiceSerializer
from ipam.models import Service
from netbox.api.fields import ContentTypeField, SerializedPKRelatedField
from netbox.api.serializers import NetBoxModelSerializer
from rest_framework import serializers
from ..models import (
    CatalogCredential, CatalogSecondaryPort, CatalogTestIntegration, CatalogTestState, CatalogToken,
    HAMirror, Integration, IntegrationCatalog, InstanceOpenBaoPath, ServiceCatalog, ServiceInstance,
)

_META = ["tags", "custom_fields", "created", "last_updated"]


class ServiceCatalogSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_services-api:servicecatalog-detail")

    class Meta:
        model = ServiceCatalog
        fields = [
            "id", "url", "display", "name", "display_name", "description", "repo", "docs", "license",
            "tier", "requires_gpu", "default_port", "install_memory", "install_cores",
            "runtime_memory", "runtime_cores", "disk", "playbook", "init_playbook",
            "customize_playbook", "unlock_playbook", "health_endpoint", "health_status_codes",
            "requires_database", "database_type", "requires_cache", "ha_strategy",
            "ingress_haproxy_backup", *_META,
        ]
        brief_fields = ["id", "url", "display", "name", "display_name"]


class CatalogCredentialSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_services-api:catalogcredential-detail")
    catalog = ServiceCatalogSerializer(nested=True)

    class Meta:
        model = CatalogCredential
        fields = ["id", "url", "display", "catalog", "cred_id", "length", "deploy_var", *_META]
        brief_fields = ["id", "url", "display", "cred_id"]


class CatalogTokenSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_services-api:catalogtoken-detail")
    catalog = ServiceCatalogSerializer(nested=True)

    class Meta:
        model = CatalogToken
        fields = ["id", "url", "display", "catalog", "name", "output_var", *_META]
        brief_fields = ["id", "url", "display", "name"]


class CatalogSecondaryPortSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_services-api:catalogsecondaryport-detail")
    catalog = ServiceCatalogSerializer(nested=True)

    class Meta:
        model = CatalogSecondaryPort
        fields = ["id", "url", "display", "catalog", "port", "protocol", "name", *_META]
        brief_fields = ["id", "url", "display", "port", "protocol"]


class IntegrationCatalogSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_services-api:integrationcatalog-detail")
    catalog = ServiceCatalogSerializer(nested=True)

    class Meta:
        model = IntegrationCatalog
        fields = [
            "id", "url", "display", "catalog", "type", "requires_service", "requires_tokens",
            "playbook", "description", "provider_scope", "consumer_max", *_META,
        ]
        brief_fields = ["id", "url", "display", "type", "requires_service"]


class CatalogTestStateSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_services-api:catalogteststate-detail")
    catalog = ServiceCatalogSerializer(nested=True)

    class Meta:
        model = CatalogTestState
        fields = [
            "id", "url", "display", "catalog", "distro", "install", "init", "customize", "unlock",
            "peak_memory_mb", "peak_cpu_load", "install_duration_s", *_META,
        ]
        brief_fields = ["id", "url", "display", "distro"]


class CatalogTestIntegrationSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_services-api:catalogtestintegration-detail")
    test_state = CatalogTestStateSerializer(nested=True)

    class Meta:
        model = CatalogTestIntegration
        fields = ["id", "url", "display", "test_state", "provider_service", "passed", *_META]
        brief_fields = ["id", "url", "display", "provider_service", "passed"]


class ServiceInstanceSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_services-api:serviceinstance-detail")
    catalog = ServiceCatalogSerializer(nested=True)
    # Catalog FK fields denormalized for the provider contract (the tofu-services
    # provider + hv/pve reader): resolved server-side via the FK so a single
    # instance fetch carries the type's install metadata — no separate catalog
    # fetch + client-side id-join. Read-only mirrors; the writable FK is `catalog`.
    catalog_playbook = serializers.CharField(source="catalog.playbook", read_only=True)
    catalog_default_port = serializers.IntegerField(
        source="catalog.default_port", read_only=True, allow_null=True
    )
    catalog_requires_database = serializers.BooleanField(
        source="catalog.requires_database", read_only=True
    )
    parent_object_type = ContentTypeField(queryset=ContentType.objects.all())
    parent = serializers.SerializerMethodField(read_only=True)
    listeners = SerializedPKRelatedField(
        queryset=Service.objects.all(), serializer=ServiceSerializer, nested=True, required=False, many=True
    )

    class Meta:
        model = ServiceInstance
        fields = [
            "id", "url", "display", "catalog", "catalog_playbook", "catalog_default_port",
            "catalog_requires_database", "parent_object_type", "parent_object_id", "parent",
            "hostname", "status", "actual_memory", "actual_cores", "actual_disk", "listeners", *_META,
        ]
        brief_fields = ["id", "url", "display", "catalog", "hostname", "status"]

    @extend_schema_field(serializers.JSONField(allow_null=True))
    def get_parent(self, obj):
        if obj.parent is None:
            return None
        request = self.context.get("request")
        url = obj.parent.get_absolute_url()
        return {
            "id": obj.parent.pk,
            "display": str(obj.parent),
            "url": request.build_absolute_uri(url) if request else url,
        }


class InstanceOpenBaoPathSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_services-api:instanceopenbaopath-detail")
    instance = ServiceInstanceSerializer(nested=True)

    class Meta:
        model = InstanceOpenBaoPath
        fields = ["id", "url", "display", "instance", "key", "path", *_META]
        brief_fields = ["id", "url", "display", "key"]


class IntegrationSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_services-api:integration-detail")
    consumer = ServiceInstanceSerializer(nested=True)
    provider = ServiceInstanceSerializer(nested=True)

    class Meta:
        model = Integration
        fields = ["id", "url", "display", "consumer", "provider", "type", "requires_tokens", "description", *_META]
        brief_fields = ["id", "url", "display", "type"]


class HAMirrorSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:netbox_services-api:hamirror-detail")
    mirror = ServiceInstanceSerializer(nested=True)
    primary = ServiceInstanceSerializer(nested=True)

    class Meta:
        model = HAMirror
        fields = ["id", "url", "display", "mirror", "primary", *_META]
        brief_fields = ["id", "url", "display", "mirror", "primary"]
