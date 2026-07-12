# SPDX-License-Identifier: AGPL-3.0-or-later
"""FilterSets — drive both the REST API query params and the UI list filtering. FK filters are
declared explicitly (django-filter does not derive ``<fk>_id`` from a bare FK): ``<fk>_id`` by PK,
``<fk>`` by natural key."""
import django_filters
from django.db.models import Q
from netbox.filtersets import NetBoxModelFilterSet
from .choices import (
    DatabaseTypeChoices, DistroChoices, ExtensionKindChoices, HAStrategyChoices,
    IntegrationParamValueTypeChoices, ProviderScopeChoices, ServiceInstanceStatusChoices,
)
from .models import (
    CatalogConfigParam, CatalogCredential, CatalogExtension, CatalogSecondaryPort,
    CatalogTestIntegration, CatalogTestState, CatalogToken, HAMirror, Integration, IntegrationCatalog,
    IntegrationCatalogParam, IntegrationParam, InstanceOpenBaoPath, ServiceCatalog, ServiceInstance,
    ServiceInstanceConfigValue, ServiceInstanceExtension,
)


class _CatalogChildFilterMixin(NetBoxModelFilterSet):
    catalog_id = django_filters.ModelMultipleChoiceFilter(
        field_name="catalog", queryset=ServiceCatalog.objects.all(), label="Catalog (ID)"
    )
    catalog = django_filters.ModelMultipleChoiceFilter(
        field_name="catalog__name", to_field_name="name", queryset=ServiceCatalog.objects.all(),
        label="Catalog (name)",
    )

    class Meta:
        abstract = True


class _InstanceChildFilterMixin(NetBoxModelFilterSet):
    instance_id = django_filters.ModelMultipleChoiceFilter(
        field_name="instance", queryset=ServiceInstance.objects.all(), label="Instance (ID)"
    )

    class Meta:
        abstract = True


class ServiceCatalogFilterSet(NetBoxModelFilterSet):
    database_type = django_filters.MultipleChoiceFilter(choices=DatabaseTypeChoices)
    ha_strategy = django_filters.MultipleChoiceFilter(choices=HAStrategyChoices)

    class Meta:
        model = ServiceCatalog
        fields = ["id", "name", "display_name", "tier", "requires_gpu", "requires_database", "requires_cache"]

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) | Q(display_name__icontains=value) | Q(description__icontains=value)
        )


class CatalogCredentialFilterSet(_CatalogChildFilterMixin):
    class Meta:
        model = CatalogCredential
        fields = ["id", "cred_id", "deploy_var"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(cred_id__icontains=value) | Q(deploy_var__icontains=value))


class CatalogTokenFilterSet(_CatalogChildFilterMixin):
    class Meta:
        model = CatalogToken
        fields = ["id", "name", "output_var"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(name__icontains=value) | Q(output_var__icontains=value))


class CatalogSecondaryPortFilterSet(_CatalogChildFilterMixin):
    class Meta:
        model = CatalogSecondaryPort
        fields = ["id", "port", "protocol", "name"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(name__icontains=value))


class IntegrationCatalogFilterSet(_CatalogChildFilterMixin):
    provider_scope = django_filters.MultipleChoiceFilter(choices=ProviderScopeChoices)

    class Meta:
        model = IntegrationCatalog
        fields = ["id", "type", "requires_service", "consumer_max"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(type__icontains=value) | Q(requires_service__icontains=value))


class IntegrationCatalogParamFilterSet(NetBoxModelFilterSet):
    integration_catalog_id = django_filters.ModelMultipleChoiceFilter(
        field_name="integration_catalog", queryset=IntegrationCatalog.objects.all(),
        label="Integration Catalog (ID)",
    )
    value_type = django_filters.MultipleChoiceFilter(choices=IntegrationParamValueTypeChoices)

    class Meta:
        model = IntegrationCatalogParam
        fields = ["id", "key", "value_type", "required", "secret"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(key__icontains=value) | Q(description__icontains=value))


class CatalogConfigParamFilterSet(_CatalogChildFilterMixin):
    value_type = django_filters.MultipleChoiceFilter(choices=IntegrationParamValueTypeChoices)

    class Meta:
        model = CatalogConfigParam
        fields = ["id", "key", "value_type", "required", "secret", "provider_attr"]

    def search(self, queryset, name, value):
        return queryset.filter(
            Q(key__icontains=value) | Q(description__icontains=value) | Q(provider_attr__icontains=value)
        )


class CatalogExtensionFilterSet(_CatalogChildFilterMixin):
    kind = django_filters.MultipleChoiceFilter(choices=ExtensionKindChoices)

    class Meta:
        model = CatalogExtension
        fields = ["id", "kind", "name", "default_version", "required"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


class CatalogTestStateFilterSet(_CatalogChildFilterMixin):
    distro = django_filters.MultipleChoiceFilter(choices=DistroChoices)

    class Meta:
        model = CatalogTestState
        fields = ["id", "install", "init", "customize", "unlock"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(catalog__name__icontains=value))


class CatalogTestIntegrationFilterSet(NetBoxModelFilterSet):
    test_state_id = django_filters.ModelMultipleChoiceFilter(
        field_name="test_state", queryset=CatalogTestState.objects.all(), label="Test State (ID)"
    )

    class Meta:
        model = CatalogTestIntegration
        fields = ["id", "provider_service", "passed"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(provider_service__icontains=value))


class ServiceInstanceFilterSet(NetBoxModelFilterSet):
    catalog_id = django_filters.ModelMultipleChoiceFilter(
        field_name="catalog", queryset=ServiceCatalog.objects.all(), label="Catalog (ID)"
    )
    catalog = django_filters.ModelMultipleChoiceFilter(
        field_name="catalog__name", to_field_name="name", queryset=ServiceCatalog.objects.all(),
        label="Catalog (name)",
    )
    status = django_filters.MultipleChoiceFilter(choices=ServiceInstanceStatusChoices)

    class Meta:
        model = ServiceInstance
        fields = ["id", "hostname", "parent_object_id"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(hostname__icontains=value) | Q(catalog__name__icontains=value))


class InstanceOpenBaoPathFilterSet(_InstanceChildFilterMixin):
    class Meta:
        model = InstanceOpenBaoPath
        fields = ["id", "key", "path"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(key__icontains=value) | Q(path__icontains=value))


class IntegrationFilterSet(NetBoxModelFilterSet):
    consumer_id = django_filters.ModelMultipleChoiceFilter(
        field_name="consumer", queryset=ServiceInstance.objects.all(), label="Consumer (ID)"
    )
    provider_id = django_filters.ModelMultipleChoiceFilter(
        field_name="provider", queryset=ServiceInstance.objects.all(), label="Provider (ID)"
    )

    class Meta:
        model = Integration
        fields = ["id", "type"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(type__icontains=value))


class IntegrationParamFilterSet(NetBoxModelFilterSet):
    integration_id = django_filters.ModelMultipleChoiceFilter(
        field_name="integration", queryset=Integration.objects.all(), label="Integration (ID)"
    )

    class Meta:
        model = IntegrationParam
        fields = ["id", "key", "value"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(key__icontains=value) | Q(value__icontains=value))


class ServiceInstanceConfigValueFilterSet(_InstanceChildFilterMixin):
    param_id = django_filters.ModelMultipleChoiceFilter(
        field_name="param", queryset=CatalogConfigParam.objects.all(), label="Config Param (ID)"
    )

    class Meta:
        model = ServiceInstanceConfigValue
        fields = ["id", "value"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(value__icontains=value) | Q(param__key__icontains=value))


class ServiceInstanceExtensionFilterSet(_InstanceChildFilterMixin):
    kind = django_filters.MultipleChoiceFilter(choices=ExtensionKindChoices)

    class Meta:
        model = ServiceInstanceExtension
        fields = ["id", "kind", "name", "version", "enabled", "managed"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(name__icontains=value) | Q(version__icontains=value))


class HAMirrorFilterSet(NetBoxModelFilterSet):
    mirror_id = django_filters.ModelMultipleChoiceFilter(
        field_name="mirror", queryset=ServiceInstance.objects.all(), label="Mirror (ID)"
    )
    primary_id = django_filters.ModelMultipleChoiceFilter(
        field_name="primary", queryset=ServiceInstance.objects.all(), label="Primary (ID)"
    )

    class Meta:
        model = HAMirror
        fields = ["id"]

    def search(self, queryset, name, value):
        return queryset.filter(Q(mirror__hostname__icontains=value) | Q(primary__hostname__icontains=value))
