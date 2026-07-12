# SPDX-License-Identifier: AGPL-3.0-or-later
from netbox.views import generic
from . import filtersets, forms, models, tables


class ServiceCatalogView(generic.ObjectView):
    queryset = models.ServiceCatalog.objects.all()


class ServiceCatalogListView(generic.ObjectListView):
    queryset = models.ServiceCatalog.objects.all()
    table = tables.ServiceCatalogTable
    filterset = filtersets.ServiceCatalogFilterSet
    filterset_form = forms.ServiceCatalogFilterForm


class ServiceCatalogEditView(generic.ObjectEditView):
    queryset = models.ServiceCatalog.objects.all()
    form = forms.ServiceCatalogForm


class ServiceCatalogDeleteView(generic.ObjectDeleteView):
    queryset = models.ServiceCatalog.objects.all()


class ServiceCatalogBulkDeleteView(generic.BulkDeleteView):
    queryset = models.ServiceCatalog.objects.all()
    table = tables.ServiceCatalogTable


class CatalogCredentialView(generic.ObjectView):
    queryset = models.CatalogCredential.objects.all()


class CatalogCredentialListView(generic.ObjectListView):
    queryset = models.CatalogCredential.objects.all()
    table = tables.CatalogCredentialTable
    filterset = filtersets.CatalogCredentialFilterSet
    filterset_form = forms.CatalogCredentialFilterForm


class CatalogCredentialEditView(generic.ObjectEditView):
    queryset = models.CatalogCredential.objects.all()
    form = forms.CatalogCredentialForm


class CatalogCredentialDeleteView(generic.ObjectDeleteView):
    queryset = models.CatalogCredential.objects.all()


class CatalogCredentialBulkDeleteView(generic.BulkDeleteView):
    queryset = models.CatalogCredential.objects.all()
    table = tables.CatalogCredentialTable


class CatalogTokenView(generic.ObjectView):
    queryset = models.CatalogToken.objects.all()


class CatalogTokenListView(generic.ObjectListView):
    queryset = models.CatalogToken.objects.all()
    table = tables.CatalogTokenTable
    filterset = filtersets.CatalogTokenFilterSet
    filterset_form = forms.CatalogTokenFilterForm


class CatalogTokenEditView(generic.ObjectEditView):
    queryset = models.CatalogToken.objects.all()
    form = forms.CatalogTokenForm


class CatalogTokenDeleteView(generic.ObjectDeleteView):
    queryset = models.CatalogToken.objects.all()


class CatalogTokenBulkDeleteView(generic.BulkDeleteView):
    queryset = models.CatalogToken.objects.all()
    table = tables.CatalogTokenTable


class CatalogSecondaryPortView(generic.ObjectView):
    queryset = models.CatalogSecondaryPort.objects.all()


class CatalogSecondaryPortListView(generic.ObjectListView):
    queryset = models.CatalogSecondaryPort.objects.all()
    table = tables.CatalogSecondaryPortTable
    filterset = filtersets.CatalogSecondaryPortFilterSet
    filterset_form = forms.CatalogSecondaryPortFilterForm


class CatalogSecondaryPortEditView(generic.ObjectEditView):
    queryset = models.CatalogSecondaryPort.objects.all()
    form = forms.CatalogSecondaryPortForm


class CatalogSecondaryPortDeleteView(generic.ObjectDeleteView):
    queryset = models.CatalogSecondaryPort.objects.all()


class CatalogSecondaryPortBulkDeleteView(generic.BulkDeleteView):
    queryset = models.CatalogSecondaryPort.objects.all()
    table = tables.CatalogSecondaryPortTable


class IntegrationCatalogView(generic.ObjectView):
    queryset = models.IntegrationCatalog.objects.all()


class IntegrationCatalogListView(generic.ObjectListView):
    queryset = models.IntegrationCatalog.objects.all()
    table = tables.IntegrationCatalogTable
    filterset = filtersets.IntegrationCatalogFilterSet
    filterset_form = forms.IntegrationCatalogFilterForm


class IntegrationCatalogEditView(generic.ObjectEditView):
    queryset = models.IntegrationCatalog.objects.all()
    form = forms.IntegrationCatalogForm


class IntegrationCatalogDeleteView(generic.ObjectDeleteView):
    queryset = models.IntegrationCatalog.objects.all()


class IntegrationCatalogBulkDeleteView(generic.BulkDeleteView):
    queryset = models.IntegrationCatalog.objects.all()
    table = tables.IntegrationCatalogTable


class IntegrationCatalogParamView(generic.ObjectView):
    queryset = models.IntegrationCatalogParam.objects.all()


class IntegrationCatalogParamListView(generic.ObjectListView):
    queryset = models.IntegrationCatalogParam.objects.all()
    table = tables.IntegrationCatalogParamTable
    filterset = filtersets.IntegrationCatalogParamFilterSet
    filterset_form = forms.IntegrationCatalogParamFilterForm


class IntegrationCatalogParamEditView(generic.ObjectEditView):
    queryset = models.IntegrationCatalogParam.objects.all()
    form = forms.IntegrationCatalogParamForm


class IntegrationCatalogParamDeleteView(generic.ObjectDeleteView):
    queryset = models.IntegrationCatalogParam.objects.all()


class IntegrationCatalogParamBulkDeleteView(generic.BulkDeleteView):
    queryset = models.IntegrationCatalogParam.objects.all()
    table = tables.IntegrationCatalogParamTable


class CatalogConfigParamView(generic.ObjectView):
    queryset = models.CatalogConfigParam.objects.all()


class CatalogConfigParamListView(generic.ObjectListView):
    queryset = models.CatalogConfigParam.objects.all()
    table = tables.CatalogConfigParamTable
    filterset = filtersets.CatalogConfigParamFilterSet
    filterset_form = forms.CatalogConfigParamFilterForm


class CatalogConfigParamEditView(generic.ObjectEditView):
    queryset = models.CatalogConfigParam.objects.all()
    form = forms.CatalogConfigParamForm


class CatalogConfigParamDeleteView(generic.ObjectDeleteView):
    queryset = models.CatalogConfigParam.objects.all()


class CatalogConfigParamBulkDeleteView(generic.BulkDeleteView):
    queryset = models.CatalogConfigParam.objects.all()
    table = tables.CatalogConfigParamTable


class CatalogExtensionView(generic.ObjectView):
    queryset = models.CatalogExtension.objects.all()


class CatalogExtensionListView(generic.ObjectListView):
    queryset = models.CatalogExtension.objects.all()
    table = tables.CatalogExtensionTable
    filterset = filtersets.CatalogExtensionFilterSet
    filterset_form = forms.CatalogExtensionFilterForm


class CatalogExtensionEditView(generic.ObjectEditView):
    queryset = models.CatalogExtension.objects.all()
    form = forms.CatalogExtensionForm


class CatalogExtensionDeleteView(generic.ObjectDeleteView):
    queryset = models.CatalogExtension.objects.all()


class CatalogExtensionBulkDeleteView(generic.BulkDeleteView):
    queryset = models.CatalogExtension.objects.all()
    table = tables.CatalogExtensionTable


class CatalogTestStateView(generic.ObjectView):
    queryset = models.CatalogTestState.objects.all()


class CatalogTestStateListView(generic.ObjectListView):
    queryset = models.CatalogTestState.objects.all()
    table = tables.CatalogTestStateTable
    filterset = filtersets.CatalogTestStateFilterSet
    filterset_form = forms.CatalogTestStateFilterForm


class CatalogTestStateEditView(generic.ObjectEditView):
    queryset = models.CatalogTestState.objects.all()
    form = forms.CatalogTestStateForm


class CatalogTestStateDeleteView(generic.ObjectDeleteView):
    queryset = models.CatalogTestState.objects.all()


class CatalogTestStateBulkDeleteView(generic.BulkDeleteView):
    queryset = models.CatalogTestState.objects.all()
    table = tables.CatalogTestStateTable


class CatalogTestIntegrationView(generic.ObjectView):
    queryset = models.CatalogTestIntegration.objects.all()


class CatalogTestIntegrationListView(generic.ObjectListView):
    queryset = models.CatalogTestIntegration.objects.all()
    table = tables.CatalogTestIntegrationTable
    filterset = filtersets.CatalogTestIntegrationFilterSet
    filterset_form = forms.CatalogTestIntegrationFilterForm


class CatalogTestIntegrationEditView(generic.ObjectEditView):
    queryset = models.CatalogTestIntegration.objects.all()
    form = forms.CatalogTestIntegrationForm


class CatalogTestIntegrationDeleteView(generic.ObjectDeleteView):
    queryset = models.CatalogTestIntegration.objects.all()


class CatalogTestIntegrationBulkDeleteView(generic.BulkDeleteView):
    queryset = models.CatalogTestIntegration.objects.all()
    table = tables.CatalogTestIntegrationTable


class ServiceInstanceView(generic.ObjectView):
    queryset = models.ServiceInstance.objects.all()


class ServiceInstanceListView(generic.ObjectListView):
    queryset = models.ServiceInstance.objects.all()
    table = tables.ServiceInstanceTable
    filterset = filtersets.ServiceInstanceFilterSet
    filterset_form = forms.ServiceInstanceFilterForm


class ServiceInstanceEditView(generic.ObjectEditView):
    queryset = models.ServiceInstance.objects.all()
    form = forms.ServiceInstanceForm


class ServiceInstanceDeleteView(generic.ObjectDeleteView):
    queryset = models.ServiceInstance.objects.all()


class ServiceInstanceBulkDeleteView(generic.BulkDeleteView):
    queryset = models.ServiceInstance.objects.all()
    table = tables.ServiceInstanceTable


class InstanceOpenBaoPathView(generic.ObjectView):
    queryset = models.InstanceOpenBaoPath.objects.all()


class InstanceOpenBaoPathListView(generic.ObjectListView):
    queryset = models.InstanceOpenBaoPath.objects.all()
    table = tables.InstanceOpenBaoPathTable
    filterset = filtersets.InstanceOpenBaoPathFilterSet
    filterset_form = forms.InstanceOpenBaoPathFilterForm


class InstanceOpenBaoPathEditView(generic.ObjectEditView):
    queryset = models.InstanceOpenBaoPath.objects.all()
    form = forms.InstanceOpenBaoPathForm


class InstanceOpenBaoPathDeleteView(generic.ObjectDeleteView):
    queryset = models.InstanceOpenBaoPath.objects.all()


class InstanceOpenBaoPathBulkDeleteView(generic.BulkDeleteView):
    queryset = models.InstanceOpenBaoPath.objects.all()
    table = tables.InstanceOpenBaoPathTable


class ServiceInstanceConfigValueView(generic.ObjectView):
    queryset = models.ServiceInstanceConfigValue.objects.all()


class ServiceInstanceConfigValueListView(generic.ObjectListView):
    queryset = models.ServiceInstanceConfigValue.objects.all()
    table = tables.ServiceInstanceConfigValueTable
    filterset = filtersets.ServiceInstanceConfigValueFilterSet
    filterset_form = forms.ServiceInstanceConfigValueFilterForm


class ServiceInstanceConfigValueEditView(generic.ObjectEditView):
    queryset = models.ServiceInstanceConfigValue.objects.all()
    form = forms.ServiceInstanceConfigValueForm


class ServiceInstanceConfigValueDeleteView(generic.ObjectDeleteView):
    queryset = models.ServiceInstanceConfigValue.objects.all()


class ServiceInstanceConfigValueBulkDeleteView(generic.BulkDeleteView):
    queryset = models.ServiceInstanceConfigValue.objects.all()
    table = tables.ServiceInstanceConfigValueTable


class ServiceInstanceExtensionView(generic.ObjectView):
    queryset = models.ServiceInstanceExtension.objects.all()


class ServiceInstanceExtensionListView(generic.ObjectListView):
    queryset = models.ServiceInstanceExtension.objects.all()
    table = tables.ServiceInstanceExtensionTable
    filterset = filtersets.ServiceInstanceExtensionFilterSet
    filterset_form = forms.ServiceInstanceExtensionFilterForm


class ServiceInstanceExtensionEditView(generic.ObjectEditView):
    queryset = models.ServiceInstanceExtension.objects.all()
    form = forms.ServiceInstanceExtensionForm


class ServiceInstanceExtensionDeleteView(generic.ObjectDeleteView):
    queryset = models.ServiceInstanceExtension.objects.all()


class ServiceInstanceExtensionBulkDeleteView(generic.BulkDeleteView):
    queryset = models.ServiceInstanceExtension.objects.all()
    table = tables.ServiceInstanceExtensionTable


class IntegrationView(generic.ObjectView):
    queryset = models.Integration.objects.all()


class IntegrationListView(generic.ObjectListView):
    queryset = models.Integration.objects.all()
    table = tables.IntegrationTable
    filterset = filtersets.IntegrationFilterSet
    filterset_form = forms.IntegrationFilterForm


class IntegrationEditView(generic.ObjectEditView):
    queryset = models.Integration.objects.all()
    form = forms.IntegrationForm


class IntegrationDeleteView(generic.ObjectDeleteView):
    queryset = models.Integration.objects.all()


class IntegrationBulkDeleteView(generic.BulkDeleteView):
    queryset = models.Integration.objects.all()
    table = tables.IntegrationTable


class IntegrationParamView(generic.ObjectView):
    queryset = models.IntegrationParam.objects.all()


class IntegrationParamListView(generic.ObjectListView):
    queryset = models.IntegrationParam.objects.all()
    table = tables.IntegrationParamTable
    filterset = filtersets.IntegrationParamFilterSet
    filterset_form = forms.IntegrationParamFilterForm


class IntegrationParamEditView(generic.ObjectEditView):
    queryset = models.IntegrationParam.objects.all()
    form = forms.IntegrationParamForm


class IntegrationParamDeleteView(generic.ObjectDeleteView):
    queryset = models.IntegrationParam.objects.all()


class IntegrationParamBulkDeleteView(generic.BulkDeleteView):
    queryset = models.IntegrationParam.objects.all()
    table = tables.IntegrationParamTable


class HAMirrorView(generic.ObjectView):
    queryset = models.HAMirror.objects.all()


class HAMirrorListView(generic.ObjectListView):
    queryset = models.HAMirror.objects.all()
    table = tables.HAMirrorTable
    filterset = filtersets.HAMirrorFilterSet
    filterset_form = forms.HAMirrorFilterForm


class HAMirrorEditView(generic.ObjectEditView):
    queryset = models.HAMirror.objects.all()
    form = forms.HAMirrorForm


class HAMirrorDeleteView(generic.ObjectDeleteView):
    queryset = models.HAMirror.objects.all()


class HAMirrorBulkDeleteView(generic.BulkDeleteView):
    queryset = models.HAMirror.objects.all()
    table = tables.HAMirrorTable
