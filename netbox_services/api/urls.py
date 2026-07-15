# SPDX-License-Identifier: AGPL-3.0-or-later
from netbox.api.routers import NetBoxRouter
from . import views

app_name = "netbox_services"

router = NetBoxRouter()
router.register("service-catalog", views.ServiceCatalogViewSet)
router.register("catalog-credentials", views.CatalogCredentialViewSet)
router.register("catalog-tokens", views.CatalogTokenViewSet)
router.register("catalog-secondary-ports", views.CatalogSecondaryPortViewSet)
router.register("integration-catalog", views.IntegrationCatalogViewSet)
router.register("integration-catalog-params", views.IntegrationCatalogParamViewSet)
router.register("catalog-config-params", views.CatalogConfigParamViewSet)
router.register("catalog-extensions", views.CatalogExtensionViewSet)
router.register("catalog-test-states", views.CatalogTestStateViewSet)
router.register("catalog-test-integrations", views.CatalogTestIntegrationViewSet)
router.register("service-instances", views.ServiceInstanceViewSet)
router.register("instance-openbao-paths", views.InstanceOpenBaoPathViewSet)
router.register("instance-config-values", views.ServiceInstanceConfigValueViewSet)
router.register("instance-extensions", views.ServiceInstanceExtensionViewSet)
router.register("integrations", views.IntegrationViewSet)
router.register("integration-params", views.IntegrationParamViewSet)
router.register("ha-mirrors", views.HAMirrorViewSet)
router.register("host-roles", views.HostRoleViewSet)
router.register("rotation-policies", views.RotationPolicyViewSet)
router.register("host-role-params", views.HostRoleParamViewSet)
router.register("host-role-assignments", views.HostRoleAssignmentViewSet)
router.register("host-role-assignment-vars", views.HostRoleAssignmentVarViewSet)

urlpatterns = router.urls
