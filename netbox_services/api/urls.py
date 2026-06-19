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
router.register("catalog-test-states", views.CatalogTestStateViewSet)
router.register("catalog-test-integrations", views.CatalogTestIntegrationViewSet)
router.register("service-instances", views.ServiceInstanceViewSet)
router.register("instance-openbao-paths", views.InstanceOpenBaoPathViewSet)
router.register("integrations", views.IntegrationViewSet)
router.register("ha-mirrors", views.HAMirrorViewSet)

urlpatterns = router.urls
