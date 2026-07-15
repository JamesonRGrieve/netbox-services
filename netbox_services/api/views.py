# SPDX-License-Identifier: AGPL-3.0-or-later
from netbox.api.viewsets import NetBoxModelViewSet
from .. import filtersets
from ..models import (
    CatalogConfigParam, CatalogCredential, CatalogExtension, CatalogSecondaryPort,
    CatalogTestIntegration, CatalogTestState, CatalogToken, HAMirror, HostRole, HostRoleAssignment,
    HostRoleAssignmentVar, HostRoleParam, Integration, IntegrationCatalog, IntegrationCatalogParam,
    IntegrationParam, InstanceOpenBaoPath, RotationPolicy, ServiceCatalog, ServiceInstance, ServiceInstanceConfigValue,
    ServiceInstanceExtension,
)
from .serializers import (
    CatalogConfigParamSerializer, CatalogCredentialSerializer, CatalogExtensionSerializer,
    CatalogSecondaryPortSerializer, CatalogTestIntegrationSerializer, CatalogTestStateSerializer,
    CatalogTokenSerializer, HAMirrorSerializer, HostRoleAssignmentSerializer,
    HostRoleAssignmentVarSerializer, HostRoleParamSerializer, HostRoleSerializer,
    IntegrationCatalogParamSerializer, IntegrationCatalogSerializer, IntegrationParamSerializer,
    IntegrationSerializer, InstanceOpenBaoPathSerializer, RotationPolicySerializer, ServiceCatalogSerializer,
    ServiceInstanceConfigValueSerializer, ServiceInstanceExtensionSerializer, ServiceInstanceSerializer,
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


class IntegrationCatalogParamViewSet(NetBoxModelViewSet):
    queryset = IntegrationCatalogParam.objects.prefetch_related("integration_catalog", "tags")
    serializer_class = IntegrationCatalogParamSerializer
    filterset_class = filtersets.IntegrationCatalogParamFilterSet


class CatalogConfigParamViewSet(NetBoxModelViewSet):
    queryset = CatalogConfigParam.objects.prefetch_related("catalog", "tags")
    serializer_class = CatalogConfigParamSerializer
    filterset_class = filtersets.CatalogConfigParamFilterSet


class CatalogExtensionViewSet(NetBoxModelViewSet):
    queryset = CatalogExtension.objects.prefetch_related("catalog", "tags")
    serializer_class = CatalogExtensionSerializer
    filterset_class = filtersets.CatalogExtensionFilterSet


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


class ServiceInstanceConfigValueViewSet(NetBoxModelViewSet):
    queryset = ServiceInstanceConfigValue.objects.prefetch_related("instance", "param", "tags")
    serializer_class = ServiceInstanceConfigValueSerializer
    filterset_class = filtersets.ServiceInstanceConfigValueFilterSet


class ServiceInstanceExtensionViewSet(NetBoxModelViewSet):
    queryset = ServiceInstanceExtension.objects.prefetch_related("instance", "tags")
    serializer_class = ServiceInstanceExtensionSerializer
    filterset_class = filtersets.ServiceInstanceExtensionFilterSet


class IntegrationViewSet(NetBoxModelViewSet):
    queryset = Integration.objects.prefetch_related("consumer", "provider", "tags")
    serializer_class = IntegrationSerializer
    filterset_class = filtersets.IntegrationFilterSet


class IntegrationParamViewSet(NetBoxModelViewSet):
    queryset = IntegrationParam.objects.prefetch_related("integration", "tags")
    serializer_class = IntegrationParamSerializer
    filterset_class = filtersets.IntegrationParamFilterSet


class HAMirrorViewSet(NetBoxModelViewSet):
    queryset = HAMirror.objects.prefetch_related("mirror", "primary", "tags")
    serializer_class = HAMirrorSerializer
    filterset_class = filtersets.HAMirrorFilterSet


class HostRoleViewSet(NetBoxModelViewSet):
    queryset = HostRole.objects.prefetch_related("tags")
    serializer_class = HostRoleSerializer
    filterset_class = filtersets.HostRoleFilterSet


class RotationPolicyViewSet(NetBoxModelViewSet):
    queryset = RotationPolicy.objects.prefetch_related("instance", "host_role", "consumers", "tags")
    serializer_class = RotationPolicySerializer
    filterset_class = filtersets.RotationPolicyFilterSet


class HostRoleParamViewSet(NetBoxModelViewSet):
    queryset = HostRoleParam.objects.prefetch_related("role", "tags")
    serializer_class = HostRoleParamSerializer
    filterset_class = filtersets.HostRoleParamFilterSet


class HostRoleAssignmentViewSet(NetBoxModelViewSet):
    queryset = HostRoleAssignment.objects.prefetch_related("role", "target_object_type", "tags")
    serializer_class = HostRoleAssignmentSerializer
    filterset_class = filtersets.HostRoleAssignmentFilterSet


class HostRoleAssignmentVarViewSet(NetBoxModelViewSet):
    queryset = HostRoleAssignmentVar.objects.prefetch_related("assignment", "param", "tags")
    serializer_class = HostRoleAssignmentVarSerializer
    filterset_class = filtersets.HostRoleAssignmentVarFilterSet
