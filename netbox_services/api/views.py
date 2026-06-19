# SPDX-License-Identifier: AGPL-3.0-or-later
from netbox.api.viewsets import NetBoxModelViewSet
from .. import filtersets
from ..models import (
    CatalogCredential, CatalogSecondaryPort, CatalogTestIntegration, CatalogTestState, CatalogToken,
    HAMirror, Integration, IntegrationCatalog, InstanceOpenBaoPath, ServiceCatalog, ServiceInstance,
)
from .serializers import (
    CatalogCredentialSerializer, CatalogSecondaryPortSerializer, CatalogTestIntegrationSerializer,
    CatalogTestStateSerializer, CatalogTokenSerializer, HAMirrorSerializer, IntegrationCatalogSerializer,
    IntegrationSerializer, InstanceOpenBaoPathSerializer, ServiceCatalogSerializer, ServiceInstanceSerializer,
)


class ServiceCatalogViewSet(NetBoxModelViewSet):
    queryset = ServiceCatalog.objects.prefetch_related("tags")
    serializer_class = ServiceCatalogSerializer
    filterset_class = filtersets.ServiceCatalogFilterSet


class CatalogCredentialViewSet(NetBoxModelViewSet):
    queryset = CatalogCredential.objects.prefetch_related("catalog", "tags")
    serializer_class = CatalogCredentialSerializer
    filterset_class = filtersets.CatalogCredentialFilterSet


class CatalogTokenViewSet(NetBoxModelViewSet):
    queryset = CatalogToken.objects.prefetch_related("catalog", "tags")
    serializer_class = CatalogTokenSerializer
    filterset_class = filtersets.CatalogTokenFilterSet


class CatalogSecondaryPortViewSet(NetBoxModelViewSet):
    queryset = CatalogSecondaryPort.objects.prefetch_related("catalog", "tags")
    serializer_class = CatalogSecondaryPortSerializer
    filterset_class = filtersets.CatalogSecondaryPortFilterSet


class IntegrationCatalogViewSet(NetBoxModelViewSet):
    queryset = IntegrationCatalog.objects.prefetch_related("catalog", "tags")
    serializer_class = IntegrationCatalogSerializer
    filterset_class = filtersets.IntegrationCatalogFilterSet


class CatalogTestStateViewSet(NetBoxModelViewSet):
    queryset = CatalogTestState.objects.prefetch_related("catalog", "tags")
    serializer_class = CatalogTestStateSerializer
    filterset_class = filtersets.CatalogTestStateFilterSet


class CatalogTestIntegrationViewSet(NetBoxModelViewSet):
    queryset = CatalogTestIntegration.objects.prefetch_related("test_state", "tags")
    serializer_class = CatalogTestIntegrationSerializer
    filterset_class = filtersets.CatalogTestIntegrationFilterSet


class ServiceInstanceViewSet(NetBoxModelViewSet):
    queryset = ServiceInstance.objects.prefetch_related("catalog", "parent_object_type", "listeners", "tags")
    serializer_class = ServiceInstanceSerializer
    filterset_class = filtersets.ServiceInstanceFilterSet


class InstanceOpenBaoPathViewSet(NetBoxModelViewSet):
    queryset = InstanceOpenBaoPath.objects.prefetch_related("instance", "tags")
    serializer_class = InstanceOpenBaoPathSerializer
    filterset_class = filtersets.InstanceOpenBaoPathFilterSet


class IntegrationViewSet(NetBoxModelViewSet):
    queryset = Integration.objects.prefetch_related("consumer", "provider", "tags")
    serializer_class = IntegrationSerializer
    filterset_class = filtersets.IntegrationFilterSet


class HAMirrorViewSet(NetBoxModelViewSet):
    queryset = HAMirror.objects.prefetch_related("mirror", "primary", "tags")
    serializer_class = HAMirrorSerializer
    filterset_class = filtersets.HAMirrorFilterSet
