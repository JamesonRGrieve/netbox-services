# SPDX-License-Identifier: AGPL-3.0-or-later
"""Forms. ``ServiceInstance`` exposes its ``parent`` GFK as two optional install-target fields
(device | virtual_machine); ``clean`` enforces exactly one and assigns it to the GFK."""
from dcim.models import Device
from django import forms
from ipam.models import Service
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms.fields import (
    DynamicModelChoiceField, DynamicModelMultipleChoiceField, TagFilterField,
)
from utilities.forms.rendering import FieldSet
from virtualization.models import VirtualMachine
from .choices import (
    DatabaseTypeChoices, DistroChoices, ExtensionKindChoices, HAStrategyChoices,
    IntegrationParamValueTypeChoices, ProviderScopeChoices, ServiceInstanceStatusChoices,
)
from .models import (
    CatalogConfigParam, CatalogCredential, CatalogExtension, CatalogSecondaryPort,
    CatalogTestIntegration, CatalogTestState, CatalogToken, HAMirror, HostRole, HostRoleAssignment,
    HostRoleAssignmentVar, HostRoleParam, Integration, IntegrationCatalog, IntegrationCatalogParam,
    IntegrationParam, InstanceOpenBaoPath, ServiceCatalog, ServiceInstance, ServiceInstanceConfigValue,
    ServiceInstanceExtension,
)


class ServiceCatalogForm(NetBoxModelForm):
    fieldsets = (
        FieldSet("name", "display_name", "description", "tier", "requires_gpu", name="Identity"),
        FieldSet("repo", "docs", "license", name="Provenance"),
        FieldSet("default_port", "install_memory", "install_cores", "runtime_memory", "runtime_cores", "disk", name="Resources"),
        FieldSet("playbook", "init_playbook", "customize_playbook", "unlock_playbook", name="Playbooks"),
        FieldSet("health_endpoint", "health_status_codes", "requires_database", "database_type", "requires_cache", name="Verification"),
        FieldSet("ha_strategy", "ingress_haproxy_backup", name="HA"),
    )

    class Meta:
        model = ServiceCatalog
        fields = [
            "name", "display_name", "description", "repo", "docs", "license", "tier", "requires_gpu",
            "default_port", "install_memory", "install_cores", "runtime_memory", "runtime_cores", "disk",
            "playbook", "init_playbook", "customize_playbook", "unlock_playbook", "health_endpoint",
            "health_status_codes", "requires_database", "database_type", "requires_cache", "ha_strategy",
            "ingress_haproxy_backup", "tags",
        ]


class CatalogCredentialForm(NetBoxModelForm):
    catalog = DynamicModelChoiceField(queryset=ServiceCatalog.objects.all())
    fieldsets = (FieldSet("catalog", "cred_id", "length", "deploy_var", name="Credential"),)

    class Meta:
        model = CatalogCredential
        fields = ["catalog", "cred_id", "length", "deploy_var", "tags"]


class CatalogTokenForm(NetBoxModelForm):
    catalog = DynamicModelChoiceField(queryset=ServiceCatalog.objects.all())
    fieldsets = (FieldSet("catalog", "name", "output_var", name="Token"),)

    class Meta:
        model = CatalogToken
        fields = ["catalog", "name", "output_var", "tags"]


class CatalogSecondaryPortForm(NetBoxModelForm):
    catalog = DynamicModelChoiceField(queryset=ServiceCatalog.objects.all())
    fieldsets = (FieldSet("catalog", "port", "protocol", "name", name="Secondary port"),)

    class Meta:
        model = CatalogSecondaryPort
        fields = ["catalog", "port", "protocol", "name", "tags"]


class IntegrationCatalogForm(NetBoxModelForm):
    catalog = DynamicModelChoiceField(queryset=ServiceCatalog.objects.all())
    fieldsets = (
        FieldSet("catalog", "type", "requires_service", "requires_tokens", "playbook", "description", name="Integration"),
        FieldSet("provider_scope", "consumer_max", name="Cardinality"),
    )

    class Meta:
        model = IntegrationCatalog
        fields = ["catalog", "type", "requires_service", "requires_tokens", "playbook", "description",
                  "provider_scope", "consumer_max", "tags"]


class IntegrationCatalogParamForm(NetBoxModelForm):
    integration_catalog = DynamicModelChoiceField(queryset=IntegrationCatalog.objects.all())
    fieldsets = (
        FieldSet("integration_catalog", "key", "value_type", "required", "default", "secret",
                 "description", name="Catalog param"),
    )

    class Meta:
        model = IntegrationCatalogParam
        fields = ["integration_catalog", "key", "value_type", "required", "default", "secret",
                  "description", "tags"]


class IntegrationParamForm(NetBoxModelForm):
    integration = DynamicModelChoiceField(queryset=Integration.objects.all())
    fieldsets = (FieldSet("integration", "key", "value", name="Param value"),)

    class Meta:
        model = IntegrationParam
        fields = ["integration", "key", "value", "tags"]


class CatalogConfigParamForm(NetBoxModelForm):
    catalog = DynamicModelChoiceField(queryset=ServiceCatalog.objects.all())
    fieldsets = (
        FieldSet("catalog", "key", "value_type", "required", "default", "secret", "provider_attr",
                 "description", name="Config param"),
    )

    class Meta:
        model = CatalogConfigParam
        fields = ["catalog", "key", "value_type", "required", "default", "secret", "provider_attr",
                  "description", "tags"]


class ServiceInstanceConfigValueForm(NetBoxModelForm):
    instance = DynamicModelChoiceField(queryset=ServiceInstance.objects.all())
    param = DynamicModelChoiceField(queryset=CatalogConfigParam.objects.all())
    fieldsets = (FieldSet("instance", "param", "value", name="Config value"),)

    class Meta:
        model = ServiceInstanceConfigValue
        fields = ["instance", "param", "value", "tags"]


class CatalogExtensionForm(NetBoxModelForm):
    catalog = DynamicModelChoiceField(queryset=ServiceCatalog.objects.all())
    fieldsets = (
        FieldSet("catalog", "kind", "name", "default_version", "required", "description", name="Extension"),
    )

    class Meta:
        model = CatalogExtension
        fields = ["catalog", "kind", "name", "default_version", "required", "description", "tags"]


class ServiceInstanceExtensionForm(NetBoxModelForm):
    instance = DynamicModelChoiceField(queryset=ServiceInstance.objects.all())
    fieldsets = (
        FieldSet("instance", "kind", "name", "version", "enabled", "managed", name="Installed extension"),
    )

    class Meta:
        model = ServiceInstanceExtension
        fields = ["instance", "kind", "name", "version", "enabled", "managed", "tags"]


class CatalogTestStateForm(NetBoxModelForm):
    catalog = DynamicModelChoiceField(queryset=ServiceCatalog.objects.all())
    fieldsets = (
        FieldSet("catalog", "distro", name="Test"),
        FieldSet("install", "init", "customize", "unlock", name="Stages"),
        FieldSet("peak_memory_mb", "peak_cpu_load", "install_duration_s", name="Telemetry"),
    )

    class Meta:
        model = CatalogTestState
        fields = ["catalog", "distro", "install", "init", "customize", "unlock", "peak_memory_mb",
                  "peak_cpu_load", "install_duration_s", "tags"]


class CatalogTestIntegrationForm(NetBoxModelForm):
    test_state = DynamicModelChoiceField(queryset=CatalogTestState.objects.all())
    fieldsets = (FieldSet("test_state", "provider_service", "passed", name="Integration result"),)

    class Meta:
        model = CatalogTestIntegration
        fields = ["test_state", "provider_service", "passed", "tags"]


class ServiceInstanceForm(NetBoxModelForm):
    catalog = DynamicModelChoiceField(queryset=ServiceCatalog.objects.all())
    device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False, label="Device")
    virtual_machine = DynamicModelChoiceField(queryset=VirtualMachine.objects.all(), required=False, label="Virtual machine")
    listeners = DynamicModelMultipleChoiceField(queryset=Service.objects.all(), required=False)

    fieldsets = (
        FieldSet("catalog", "hostname", "status", name="Instance"),
        FieldSet("device", "virtual_machine", name="Install target (set exactly one)"),
        FieldSet("actual_memory", "actual_cores", "actual_disk", name="Resources"),
        FieldSet("listeners", name="Listeners"),
    )

    class Meta:
        model = ServiceInstance
        fields = ["catalog", "hostname", "status", "actual_memory", "actual_cores", "actual_disk",
                  "listeners", "tags"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parent = getattr(self.instance, "parent", None)
        if isinstance(parent, Device):
            self.fields["device"].initial = parent.pk
        elif isinstance(parent, VirtualMachine):
            self.fields["virtual_machine"].initial = parent.pk

    def clean(self):
        super().clean()
        device = self.cleaned_data.get("device")
        vm = self.cleaned_data.get("virtual_machine")
        if bool(device) == bool(vm):
            raise forms.ValidationError("Set exactly one install target: a device or a virtual machine.")
        self.instance.parent = device or vm
        return self.cleaned_data


class InstanceOpenBaoPathForm(NetBoxModelForm):
    instance = DynamicModelChoiceField(queryset=ServiceInstance.objects.all())
    fieldsets = (FieldSet("instance", "key", "path", name="OpenBao reference"),)

    class Meta:
        model = InstanceOpenBaoPath
        fields = ["instance", "key", "path", "tags"]


class IntegrationForm(NetBoxModelForm):
    consumer = DynamicModelChoiceField(queryset=ServiceInstance.objects.all())
    provider = DynamicModelChoiceField(queryset=ServiceInstance.objects.all())
    fieldsets = (FieldSet("consumer", "type", "provider", "requires_tokens", "description", name="Integration edge"),)

    class Meta:
        model = Integration
        fields = ["consumer", "provider", "type", "requires_tokens", "description", "tags"]


class HAMirrorForm(NetBoxModelForm):
    mirror = DynamicModelChoiceField(queryset=ServiceInstance.objects.all())
    primary = DynamicModelChoiceField(queryset=ServiceInstance.objects.all())
    fieldsets = (FieldSet("mirror", "primary", name="HA pairing"),)

    class Meta:
        model = HAMirror
        fields = ["mirror", "primary", "tags"]


class HostRoleForm(NetBoxModelForm):
    fieldsets = (
        FieldSet("name", "display_name", "description", name="Identity"),
        FieldSet("playbook", "ansible_tags", "idempotent", name="Ansible"),
    )

    class Meta:
        model = HostRole
        fields = ["name", "display_name", "description", "playbook", "ansible_tags", "idempotent", "tags"]


class HostRoleParamForm(NetBoxModelForm):
    role = DynamicModelChoiceField(queryset=HostRole.objects.all())
    fieldsets = (
        FieldSet("role", "key", "value_type", "required", "default", "secret", "description", name="Role param"),
    )

    class Meta:
        model = HostRoleParam
        fields = ["role", "key", "value_type", "required", "default", "secret", "description", "tags"]


class HostRoleAssignmentForm(NetBoxModelForm):
    role = DynamicModelChoiceField(queryset=HostRole.objects.all())
    device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False, label="Device")
    virtual_machine = DynamicModelChoiceField(queryset=VirtualMachine.objects.all(), required=False, label="Virtual machine")

    fieldsets = (
        FieldSet("role", "order", "enabled", name="Assignment"),
        FieldSet("device", "virtual_machine", name="Target (set exactly one)"),
    )

    class Meta:
        model = HostRoleAssignment
        fields = ["role", "order", "enabled", "tags"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        target = getattr(self.instance, "target", None)
        if isinstance(target, Device):
            self.fields["device"].initial = target.pk
        elif isinstance(target, VirtualMachine):
            self.fields["virtual_machine"].initial = target.pk

    def clean(self):
        super().clean()
        device = self.cleaned_data.get("device")
        vm = self.cleaned_data.get("virtual_machine")
        if bool(device) == bool(vm):
            raise forms.ValidationError("Set exactly one target: a device or a virtual machine.")
        self.instance.target = device or vm
        return self.cleaned_data


class HostRoleAssignmentVarForm(NetBoxModelForm):
    assignment = DynamicModelChoiceField(queryset=HostRoleAssignment.objects.all())
    param = DynamicModelChoiceField(queryset=HostRoleParam.objects.all())
    fieldsets = (FieldSet("assignment", "param", "value", name="Override value"),)

    class Meta:
        model = HostRoleAssignmentVar
        fields = ["assignment", "param", "value", "tags"]


# --------------------------------------------------------------------------- filter forms


class ServiceCatalogFilterForm(NetBoxModelFilterSetForm):
    model = ServiceCatalog
    database_type = forms.MultipleChoiceField(choices=DatabaseTypeChoices, required=False)
    ha_strategy = forms.MultipleChoiceField(choices=HAStrategyChoices, required=False)
    requires_gpu = forms.NullBooleanField(required=False)
    tag = TagFilterField(ServiceCatalog)


class CatalogCredentialFilterForm(NetBoxModelFilterSetForm):
    model = CatalogCredential
    catalog_id = DynamicModelMultipleChoiceField(queryset=ServiceCatalog.objects.all(), required=False, label="Catalog")
    tag = TagFilterField(CatalogCredential)


class CatalogTokenFilterForm(NetBoxModelFilterSetForm):
    model = CatalogToken
    catalog_id = DynamicModelMultipleChoiceField(queryset=ServiceCatalog.objects.all(), required=False, label="Catalog")
    tag = TagFilterField(CatalogToken)


class CatalogSecondaryPortFilterForm(NetBoxModelFilterSetForm):
    model = CatalogSecondaryPort
    catalog_id = DynamicModelMultipleChoiceField(queryset=ServiceCatalog.objects.all(), required=False, label="Catalog")
    tag = TagFilterField(CatalogSecondaryPort)


class IntegrationCatalogFilterForm(NetBoxModelFilterSetForm):
    model = IntegrationCatalog
    catalog_id = DynamicModelMultipleChoiceField(queryset=ServiceCatalog.objects.all(), required=False, label="Catalog")
    provider_scope = forms.MultipleChoiceField(choices=ProviderScopeChoices, required=False)
    tag = TagFilterField(IntegrationCatalog)


class IntegrationCatalogParamFilterForm(NetBoxModelFilterSetForm):
    model = IntegrationCatalogParam
    integration_catalog_id = DynamicModelMultipleChoiceField(
        queryset=IntegrationCatalog.objects.all(), required=False, label="Integration Catalog"
    )
    value_type = forms.MultipleChoiceField(choices=IntegrationParamValueTypeChoices, required=False)
    required = forms.NullBooleanField(required=False)
    secret = forms.NullBooleanField(required=False)
    tag = TagFilterField(IntegrationCatalogParam)


class IntegrationParamFilterForm(NetBoxModelFilterSetForm):
    model = IntegrationParam
    integration_id = DynamicModelMultipleChoiceField(
        queryset=Integration.objects.all(), required=False, label="Integration"
    )
    tag = TagFilterField(IntegrationParam)


class CatalogConfigParamFilterForm(NetBoxModelFilterSetForm):
    model = CatalogConfigParam
    catalog_id = DynamicModelMultipleChoiceField(queryset=ServiceCatalog.objects.all(), required=False, label="Catalog")
    value_type = forms.MultipleChoiceField(choices=IntegrationParamValueTypeChoices, required=False)
    required = forms.NullBooleanField(required=False)
    secret = forms.NullBooleanField(required=False)
    tag = TagFilterField(CatalogConfigParam)


class ServiceInstanceConfigValueFilterForm(NetBoxModelFilterSetForm):
    model = ServiceInstanceConfigValue
    instance_id = DynamicModelMultipleChoiceField(queryset=ServiceInstance.objects.all(), required=False, label="Instance")
    param_id = DynamicModelMultipleChoiceField(queryset=CatalogConfigParam.objects.all(), required=False, label="Config Param")
    tag = TagFilterField(ServiceInstanceConfigValue)


class CatalogExtensionFilterForm(NetBoxModelFilterSetForm):
    model = CatalogExtension
    catalog_id = DynamicModelMultipleChoiceField(queryset=ServiceCatalog.objects.all(), required=False, label="Catalog")
    kind = forms.MultipleChoiceField(choices=ExtensionKindChoices, required=False)
    required = forms.NullBooleanField(required=False)
    tag = TagFilterField(CatalogExtension)


class ServiceInstanceExtensionFilterForm(NetBoxModelFilterSetForm):
    model = ServiceInstanceExtension
    instance_id = DynamicModelMultipleChoiceField(queryset=ServiceInstance.objects.all(), required=False, label="Instance")
    kind = forms.MultipleChoiceField(choices=ExtensionKindChoices, required=False)
    enabled = forms.NullBooleanField(required=False)
    managed = forms.NullBooleanField(required=False)
    tag = TagFilterField(ServiceInstanceExtension)


class CatalogTestStateFilterForm(NetBoxModelFilterSetForm):
    model = CatalogTestState
    catalog_id = DynamicModelMultipleChoiceField(queryset=ServiceCatalog.objects.all(), required=False, label="Catalog")
    distro = forms.MultipleChoiceField(choices=DistroChoices, required=False)
    tag = TagFilterField(CatalogTestState)


class CatalogTestIntegrationFilterForm(NetBoxModelFilterSetForm):
    model = CatalogTestIntegration
    test_state_id = DynamicModelMultipleChoiceField(queryset=CatalogTestState.objects.all(), required=False, label="Test State")
    passed = forms.NullBooleanField(required=False)
    tag = TagFilterField(CatalogTestIntegration)


class ServiceInstanceFilterForm(NetBoxModelFilterSetForm):
    model = ServiceInstance
    catalog_id = DynamicModelMultipleChoiceField(queryset=ServiceCatalog.objects.all(), required=False, label="Catalog")
    status = forms.MultipleChoiceField(choices=ServiceInstanceStatusChoices, required=False)
    tag = TagFilterField(ServiceInstance)


class InstanceOpenBaoPathFilterForm(NetBoxModelFilterSetForm):
    model = InstanceOpenBaoPath
    instance_id = DynamicModelMultipleChoiceField(queryset=ServiceInstance.objects.all(), required=False, label="Instance")
    tag = TagFilterField(InstanceOpenBaoPath)


class IntegrationFilterForm(NetBoxModelFilterSetForm):
    model = Integration
    consumer_id = DynamicModelMultipleChoiceField(queryset=ServiceInstance.objects.all(), required=False, label="Consumer")
    provider_id = DynamicModelMultipleChoiceField(queryset=ServiceInstance.objects.all(), required=False, label="Provider")
    tag = TagFilterField(Integration)


class HAMirrorFilterForm(NetBoxModelFilterSetForm):
    model = HAMirror
    mirror_id = DynamicModelMultipleChoiceField(queryset=ServiceInstance.objects.all(), required=False, label="Mirror")
    primary_id = DynamicModelMultipleChoiceField(queryset=ServiceInstance.objects.all(), required=False, label="Primary")
    tag = TagFilterField(HAMirror)


class HostRoleFilterForm(NetBoxModelFilterSetForm):
    model = HostRole
    idempotent = forms.NullBooleanField(required=False)
    tag = TagFilterField(HostRole)


class HostRoleParamFilterForm(NetBoxModelFilterSetForm):
    model = HostRoleParam
    role_id = DynamicModelMultipleChoiceField(queryset=HostRole.objects.all(), required=False, label="Host Role")
    value_type = forms.MultipleChoiceField(choices=IntegrationParamValueTypeChoices, required=False)
    required = forms.NullBooleanField(required=False)
    secret = forms.NullBooleanField(required=False)
    tag = TagFilterField(HostRoleParam)


class HostRoleAssignmentFilterForm(NetBoxModelFilterSetForm):
    model = HostRoleAssignment
    role_id = DynamicModelMultipleChoiceField(queryset=HostRole.objects.all(), required=False, label="Host Role")
    enabled = forms.NullBooleanField(required=False)
    tag = TagFilterField(HostRoleAssignment)


class HostRoleAssignmentVarFilterForm(NetBoxModelFilterSetForm):
    model = HostRoleAssignmentVar
    assignment_id = DynamicModelMultipleChoiceField(queryset=HostRoleAssignment.objects.all(), required=False, label="Assignment")
    param_id = DynamicModelMultipleChoiceField(queryset=HostRoleParam.objects.all(), required=False, label="Param")
    tag = TagFilterField(HostRoleAssignmentVar)
