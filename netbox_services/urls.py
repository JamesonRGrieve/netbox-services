# SPDX-License-Identifier: AGPL-3.0-or-later
from django.urls import path
from netbox.views.generic import ObjectChangeLogView, ObjectJournalView
from . import models, views


def _routes(slug, name, model, list_view, edit_view, detail_view, delete_view, bulk_delete_view):
    return [
        path(f"{slug}/", list_view.as_view(), name=f"{name}_list"),
        path(f"{slug}/add/", edit_view.as_view(), name=f"{name}_add"),
        path(f"{slug}/delete/", bulk_delete_view.as_view(), name=f"{name}_bulk_delete"),
        path(f"{slug}/<int:pk>/", detail_view.as_view(), name=name),
        path(f"{slug}/<int:pk>/edit/", edit_view.as_view(), name=f"{name}_edit"),
        path(f"{slug}/<int:pk>/delete/", delete_view.as_view(), name=f"{name}_delete"),
        path(f"{slug}/<int:pk>/changelog/", ObjectChangeLogView.as_view(), name=f"{name}_changelog", kwargs={"model": model}),
        path(f"{slug}/<int:pk>/journal/", ObjectJournalView.as_view(), name=f"{name}_journal", kwargs={"model": model}),
    ]


urlpatterns = [
    *_routes("service-catalog", "servicecatalog", models.ServiceCatalog,
             views.ServiceCatalogListView, views.ServiceCatalogEditView, views.ServiceCatalogView,
             views.ServiceCatalogDeleteView, views.ServiceCatalogBulkDeleteView),
    *_routes("catalog-credentials", "catalogcredential", models.CatalogCredential,
             views.CatalogCredentialListView, views.CatalogCredentialEditView, views.CatalogCredentialView,
             views.CatalogCredentialDeleteView, views.CatalogCredentialBulkDeleteView),
    *_routes("catalog-tokens", "catalogtoken", models.CatalogToken,
             views.CatalogTokenListView, views.CatalogTokenEditView, views.CatalogTokenView,
             views.CatalogTokenDeleteView, views.CatalogTokenBulkDeleteView),
    *_routes("catalog-secondary-ports", "catalogsecondaryport", models.CatalogSecondaryPort,
             views.CatalogSecondaryPortListView, views.CatalogSecondaryPortEditView, views.CatalogSecondaryPortView,
             views.CatalogSecondaryPortDeleteView, views.CatalogSecondaryPortBulkDeleteView),
    *_routes("integration-catalog", "integrationcatalog", models.IntegrationCatalog,
             views.IntegrationCatalogListView, views.IntegrationCatalogEditView, views.IntegrationCatalogView,
             views.IntegrationCatalogDeleteView, views.IntegrationCatalogBulkDeleteView),
    *_routes("integration-catalog-params", "integrationcatalogparam", models.IntegrationCatalogParam,
             views.IntegrationCatalogParamListView, views.IntegrationCatalogParamEditView, views.IntegrationCatalogParamView,
             views.IntegrationCatalogParamDeleteView, views.IntegrationCatalogParamBulkDeleteView),
    *_routes("catalog-config-params", "catalogconfigparam", models.CatalogConfigParam,
             views.CatalogConfigParamListView, views.CatalogConfigParamEditView, views.CatalogConfigParamView,
             views.CatalogConfigParamDeleteView, views.CatalogConfigParamBulkDeleteView),
    *_routes("catalog-test-states", "catalogteststate", models.CatalogTestState,
             views.CatalogTestStateListView, views.CatalogTestStateEditView, views.CatalogTestStateView,
             views.CatalogTestStateDeleteView, views.CatalogTestStateBulkDeleteView),
    *_routes("catalog-test-integrations", "catalogtestintegration", models.CatalogTestIntegration,
             views.CatalogTestIntegrationListView, views.CatalogTestIntegrationEditView, views.CatalogTestIntegrationView,
             views.CatalogTestIntegrationDeleteView, views.CatalogTestIntegrationBulkDeleteView),
    *_routes("service-instances", "serviceinstance", models.ServiceInstance,
             views.ServiceInstanceListView, views.ServiceInstanceEditView, views.ServiceInstanceView,
             views.ServiceInstanceDeleteView, views.ServiceInstanceBulkDeleteView),
    *_routes("instance-openbao-paths", "instanceopenbaopath", models.InstanceOpenBaoPath,
             views.InstanceOpenBaoPathListView, views.InstanceOpenBaoPathEditView, views.InstanceOpenBaoPathView,
             views.InstanceOpenBaoPathDeleteView, views.InstanceOpenBaoPathBulkDeleteView),
    *_routes("instance-config-values", "serviceinstanceconfigvalue", models.ServiceInstanceConfigValue,
             views.ServiceInstanceConfigValueListView, views.ServiceInstanceConfigValueEditView,
             views.ServiceInstanceConfigValueView, views.ServiceInstanceConfigValueDeleteView,
             views.ServiceInstanceConfigValueBulkDeleteView),
    *_routes("integrations", "integration", models.Integration,
             views.IntegrationListView, views.IntegrationEditView, views.IntegrationView,
             views.IntegrationDeleteView, views.IntegrationBulkDeleteView),
    *_routes("integration-params", "integrationparam", models.IntegrationParam,
             views.IntegrationParamListView, views.IntegrationParamEditView, views.IntegrationParamView,
             views.IntegrationParamDeleteView, views.IntegrationParamBulkDeleteView),
    *_routes("ha-mirrors", "hamirror", models.HAMirror,
             views.HAMirrorListView, views.HAMirrorEditView, views.HAMirrorView,
             views.HAMirrorDeleteView, views.HAMirrorBulkDeleteView),
]
