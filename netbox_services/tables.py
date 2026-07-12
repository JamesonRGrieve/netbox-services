# SPDX-License-Identifier: AGPL-3.0-or-later
import django_tables2 as tables
from netbox.tables import NetBoxTable, columns
from .models import (
    CatalogConfigParam, CatalogCredential, CatalogSecondaryPort, CatalogTestIntegration,
    CatalogTestState, CatalogToken, HAMirror, Integration, IntegrationCatalog,
    IntegrationCatalogParam, IntegrationParam, InstanceOpenBaoPath, ServiceCatalog, ServiceInstance,
    ServiceInstanceConfigValue,
)


class ServiceCatalogTable(NetBoxTable):
    name = tables.Column(linkify=True)
    ha_strategy = columns.ChoiceFieldColumn()
    requires_gpu = columns.BooleanColumn()
    tags = columns.TagColumn(url_name="plugins:netbox_services:servicecatalog_list")

    class Meta(NetBoxTable.Meta):
        model = ServiceCatalog
        fields = ("pk", "id", "name", "display_name", "tier", "default_port", "requires_gpu",
                  "database_type", "ha_strategy", "ingress_haproxy_backup", "tags", "created", "last_updated")
        default_columns = ("name", "display_name", "tier", "default_port", "ha_strategy")


class CatalogCredentialTable(NetBoxTable):
    catalog = tables.Column(linkify=True)
    cred_id = tables.Column(linkify=True)
    tags = columns.TagColumn(url_name="plugins:netbox_services:catalogcredential_list")

    class Meta(NetBoxTable.Meta):
        model = CatalogCredential
        fields = ("pk", "id", "catalog", "cred_id", "length", "deploy_var", "tags", "created", "last_updated")
        default_columns = ("catalog", "cred_id", "deploy_var")


class CatalogTokenTable(NetBoxTable):
    catalog = tables.Column(linkify=True)
    name = tables.Column(linkify=True)
    tags = columns.TagColumn(url_name="plugins:netbox_services:catalogtoken_list")

    class Meta(NetBoxTable.Meta):
        model = CatalogToken
        fields = ("pk", "id", "catalog", "name", "output_var", "tags", "created", "last_updated")
        default_columns = ("catalog", "name", "output_var")


class CatalogSecondaryPortTable(NetBoxTable):
    catalog = tables.Column(linkify=True)
    protocol = columns.ChoiceFieldColumn()
    tags = columns.TagColumn(url_name="plugins:netbox_services:catalogsecondaryport_list")

    class Meta(NetBoxTable.Meta):
        model = CatalogSecondaryPort
        fields = ("pk", "id", "catalog", "port", "protocol", "name", "tags", "created", "last_updated")
        default_columns = ("catalog", "port", "protocol", "name")


class IntegrationCatalogTable(NetBoxTable):
    catalog = tables.Column(linkify=True)
    type = tables.Column(linkify=True)
    provider_scope = columns.ChoiceFieldColumn()
    tags = columns.TagColumn(url_name="plugins:netbox_services:integrationcatalog_list")

    class Meta(NetBoxTable.Meta):
        model = IntegrationCatalog
        fields = ("pk", "id", "catalog", "type", "requires_service", "provider_scope", "consumer_max",
                  "tags", "created", "last_updated")
        default_columns = ("catalog", "type", "requires_service", "provider_scope", "consumer_max")


class IntegrationCatalogParamTable(NetBoxTable):
    integration_catalog = tables.Column(linkify=True)
    key = tables.Column(linkify=True)
    value_type = columns.ChoiceFieldColumn()
    required = columns.BooleanColumn()
    secret = columns.BooleanColumn()
    tags = columns.TagColumn(url_name="plugins:netbox_services:integrationcatalogparam_list")

    class Meta(NetBoxTable.Meta):
        model = IntegrationCatalogParam
        fields = ("pk", "id", "integration_catalog", "key", "value_type", "required", "default",
                  "secret", "description", "tags", "created", "last_updated")
        default_columns = ("integration_catalog", "key", "value_type", "required", "secret")


class IntegrationParamTable(NetBoxTable):
    integration = tables.Column(linkify=True)
    key = tables.Column(linkify=True)
    tags = columns.TagColumn(url_name="plugins:netbox_services:integrationparam_list")

    class Meta(NetBoxTable.Meta):
        model = IntegrationParam
        fields = ("pk", "id", "integration", "key", "value", "tags", "created", "last_updated")
        default_columns = ("integration", "key", "value")


class CatalogConfigParamTable(NetBoxTable):
    catalog = tables.Column(linkify=True)
    key = tables.Column(linkify=True)
    value_type = columns.ChoiceFieldColumn()
    required = columns.BooleanColumn()
    secret = columns.BooleanColumn()
    tags = columns.TagColumn(url_name="plugins:netbox_services:catalogconfigparam_list")

    class Meta(NetBoxTable.Meta):
        model = CatalogConfigParam
        fields = ("pk", "id", "catalog", "key", "value_type", "required", "default", "secret",
                  "provider_attr", "description", "tags", "created", "last_updated")
        default_columns = ("catalog", "key", "value_type", "required", "secret", "provider_attr")


class CatalogTestStateTable(NetBoxTable):
    catalog = tables.Column(linkify=True)
    distro = columns.ChoiceFieldColumn()
    install = columns.BooleanColumn()
    init = columns.BooleanColumn()
    customize = columns.BooleanColumn()
    unlock = columns.BooleanColumn()
    tags = columns.TagColumn(url_name="plugins:netbox_services:catalogteststate_list")

    class Meta(NetBoxTable.Meta):
        model = CatalogTestState
        fields = ("pk", "id", "catalog", "distro", "install", "init", "customize", "unlock",
                  "peak_memory_mb", "install_duration_s", "tags", "created", "last_updated")
        default_columns = ("catalog", "distro", "install", "init", "customize", "unlock")


class CatalogTestIntegrationTable(NetBoxTable):
    test_state = tables.Column(linkify=True)
    passed = columns.BooleanColumn()
    tags = columns.TagColumn(url_name="plugins:netbox_services:catalogtestintegration_list")

    class Meta(NetBoxTable.Meta):
        model = CatalogTestIntegration
        fields = ("pk", "id", "test_state", "provider_service", "passed", "tags", "created", "last_updated")
        default_columns = ("test_state", "provider_service", "passed")


class ServiceInstanceTable(NetBoxTable):
    catalog = tables.Column(linkify=True)
    hostname = tables.Column(linkify=True)
    parent = tables.Column(linkify=False, verbose_name="Parent")
    status = columns.ChoiceFieldColumn()
    tags = columns.TagColumn(url_name="plugins:netbox_services:serviceinstance_list")

    class Meta(NetBoxTable.Meta):
        model = ServiceInstance
        fields = ("pk", "id", "catalog", "hostname", "parent", "status", "actual_memory", "actual_cores",
                  "actual_disk", "tags", "created", "last_updated")
        default_columns = ("catalog", "hostname", "parent", "status")


class InstanceOpenBaoPathTable(NetBoxTable):
    instance = tables.Column(linkify=True)
    key = tables.Column(linkify=True)
    tags = columns.TagColumn(url_name="plugins:netbox_services:instanceopenbaopath_list")

    class Meta(NetBoxTable.Meta):
        model = InstanceOpenBaoPath
        fields = ("pk", "id", "instance", "key", "path", "tags", "created", "last_updated")
        default_columns = ("instance", "key", "path")


class ServiceInstanceConfigValueTable(NetBoxTable):
    instance = tables.Column(linkify=True)
    param = tables.Column(linkify=True)
    tags = columns.TagColumn(url_name="plugins:netbox_services:serviceinstanceconfigvalue_list")

    class Meta(NetBoxTable.Meta):
        model = ServiceInstanceConfigValue
        fields = ("pk", "id", "instance", "param", "value", "tags", "created", "last_updated")
        default_columns = ("instance", "param", "value")


class IntegrationTable(NetBoxTable):
    consumer = tables.Column(linkify=True)
    provider = tables.Column(linkify=True)
    type = tables.Column(linkify=True)
    tags = columns.TagColumn(url_name="plugins:netbox_services:integration_list")

    class Meta(NetBoxTable.Meta):
        model = Integration
        fields = ("pk", "id", "consumer", "type", "provider", "description", "tags", "created", "last_updated")
        default_columns = ("consumer", "type", "provider")


class HAMirrorTable(NetBoxTable):
    mirror = tables.Column(linkify=True)
    primary = tables.Column(linkify=True)
    tags = columns.TagColumn(url_name="plugins:netbox_services:hamirror_list")

    class Meta(NetBoxTable.Meta):
        model = HAMirror
        fields = ("pk", "id", "mirror", "primary", "tags", "created", "last_updated")
        default_columns = ("mirror", "primary")
