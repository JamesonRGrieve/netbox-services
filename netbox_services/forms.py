# SPDX-License-Identifier: AGPL-3.0-or-later
"""Forms. ``ServiceInstance`` exposes its ``parent`` GFK as two optional install-target fields
(device | virtual_machine); ``clean`` enforces exactly one and assigns it to the GFK."""
from dcim.models import Device
from django import forms
from ipam.models import Service
from netbox.forms import NetBoxModelFilterSetForm, NetBoxModelForm
from utilities.forms import BOOLEAN_WITH_BLANK_CHOICES
from utilities.forms.fields import (
    DynamicModelChoiceField, DynamicModelMultipleChoiceField, TagFilterField,
)
from utilities.forms.rendering import FieldSet
from ipam.models import Prefix, VLAN
from virtualization.models import Cluster, VirtualMachine
from .choices import (
    DatabaseTypeChoices, DistroChoices, ExtensionInstallTierChoices, InstanceOpenBaoPathGeneratorChoices, ExtensionKindChoices, HAActiveNodeChoices, HAStrategyChoices,
    IntegrationParamValueTypeChoices, McpCapabilityChoices, McpSourceTypeChoices, McpTransportChoices,
    MirrorModeChoices, ProviderScopeChoices, ServiceInstanceStatusChoices,
)
from .models import (
    OPENBAO_CATALOG,
    CatalogConfigParam, CatalogCredential, CatalogExtension, CatalogMcpServer, CatalogMcpServerParam,
    CatalogSecondaryPort, CatalogTestIntegration, CatalogTestState, CatalogToken, HAMirror, HAMirrorPolicy, HostRole,
    HostRoleAssignment, HostRoleAssignmentVar, HostRoleParam, Integration, IntegrationCatalog,
    IntegrationCatalogParam, IntegrationParam, InstanceOpenBaoPath, McpServer, McpServerParam,
    ServiceCatalog, ServiceInstance, ServiceInstanceConfigValue,
    RotationPolicy, ServiceInstanceExtension,
)


class ServiceCatalogForm(NetBoxModelForm):
    fieldsets = (
        FieldSet("name", "display_name", "description", "tier", "requires_gpu", "external", name="Identity"),
        FieldSet("repo", "docs", "license", name="Provenance"),
        FieldSet("default_port", "install_memory", "install_cores", "runtime_memory", "runtime_cores", "disk", name="Resources"),
        FieldSet("playbook", "init_playbook", "customize_playbook", "unlock_playbook", name="Playbooks"),
        FieldSet("health_endpoint", "health_status_codes", "requires_database", "database_type", "requires_cache", name="Verification"),
        FieldSet("ha_strategy", "ingress_haproxy_backup", name="HA"),
    )

    class Meta:
        model = ServiceCatalog
        fields = [
            "name", "display_name", "description", "repo", "docs", "license", "tier", "requires_gpu", "external",
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
        FieldSet("mirror_mode", "mirror_value", name="HA mirror"),
    )

    class Meta:
        model = CatalogConfigParam
        fields = ["catalog", "key", "value_type", "required", "default", "secret", "provider_attr",
                  "description", "mirror_mode", "mirror_value", "tags"]


class ServiceInstanceConfigValueForm(NetBoxModelForm):
    instance = DynamicModelChoiceField(queryset=ServiceInstance.objects.all())
    param = DynamicModelChoiceField(queryset=CatalogConfigParam.objects.all())
    # Unstripped so a whole config file saved from the UI keeps its exact bytes.
    value = forms.CharField(widget=forms.Textarea, strip=False)
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
        FieldSet("source_url", "branch", name="Source"),
        FieldSet("module", "position", "install_tier", name="Loading"),
    )

    class Meta:
        model = ServiceInstanceExtension
        fields = ["instance", "kind", "name", "version", "source_url", "branch", "module", "position", "install_tier",
                  "enabled", "managed", "tags"]


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
        FieldSet("device", "virtual_machine", name="Install target (exactly one; none for an external catalog)"),
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
        catalog = self.cleaned_data.get("catalog")
        if catalog is not None and catalog.external:
            if device or vm:
                raise forms.ValidationError(f"{catalog.name} is external: its instances have no install target.")
            self.instance.parent_object_type = None
            self.instance.parent_object_id = None
            return self.cleaned_data
        if bool(device) == bool(vm):
            raise forms.ValidationError("Set exactly one install target: a device or a virtual machine.")
        self.instance.parent = device or vm
        return self.cleaned_data


class InstanceOpenBaoPathForm(NetBoxModelForm):
    instance = DynamicModelChoiceField(queryset=ServiceInstance.objects.all())
    vault = DynamicModelChoiceField(
        queryset=ServiceInstance.objects.filter(catalog__name=OPENBAO_CATALOG), required=False,
        query_params={"catalog": OPENBAO_CATALOG},
    )
    fieldsets = (FieldSet("instance", "key", "path", "field", "generator", "vault", name="OpenBao reference"),)

    class Meta:
        model = InstanceOpenBaoPath
        fields = ["instance", "key", "path", "field", "generator", "vault", "tags"]


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
    fieldsets = (FieldSet("mirror", "primary", "active_node", "cloudflare_lb", "seeded", name="HA pairing"),)

    class Meta:
        model = HAMirror
        fields = ["mirror", "primary", "active_node", "cloudflare_lb", "seeded", "tags"]


class HAMirrorPolicyForm(NetBoxModelForm):
    source_cluster = DynamicModelChoiceField(queryset=Cluster.objects.all())
    target_cluster = DynamicModelChoiceField(queryset=Cluster.objects.all())
    target_device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False)
    vlan = DynamicModelChoiceField(queryset=VLAN.objects.all())
    prefix = DynamicModelChoiceField(queryset=Prefix.objects.all())
    catalogs = DynamicModelMultipleChoiceField(queryset=ServiceCatalog.objects.all())
    fieldsets = (
        FieldSet("name", "enabled", "description", name="Policy"),
        FieldSet("source_cluster", "source_name_prefix", name="Primaries"),
        FieldSet("mirror_name_prefix", "vmid_offset", "target_cluster", "target_device", name="Mirror guest"),
        FieldSet("interface_name", "vlan", "prefix", "gateway", name="Mirror network"),
        FieldSet("catalogs", "replication_name_prefix", "replication_semi_sync", name="Mirror services"),
    )

    class Meta:
        model = HAMirrorPolicy
        fields = [
            "name", "enabled", "source_cluster", "source_name_prefix", "mirror_name_prefix", "vmid_offset",
            "target_cluster", "target_device", "interface_name", "vlan", "prefix", "gateway", "catalogs",
            "replication_name_prefix", "replication_semi_sync", "description", "tags",
        ]


class HostRoleForm(NetBoxModelForm):
    fieldsets = (
        FieldSet("name", "display_name", "description", name="Identity"),
        FieldSet("playbook", "ansible_tags", "idempotent", name="Ansible"),
    )

    class Meta:
        model = HostRole
        fields = ["name", "display_name", "description", "playbook", "ansible_tags", "idempotent", "tags"]


class RotationPolicyForm(NetBoxModelForm):
    instance = DynamicModelChoiceField(queryset=ServiceInstance.objects.all())
    host_role = DynamicModelChoiceField(queryset=HostRole.objects.all(), required=False)
    consumers = DynamicModelMultipleChoiceField(queryset=ServiceInstance.objects.all(), required=False)
    fieldsets = (
        FieldSet("instance", "name", "secret_kind", "openbao_path", "enabled", name="Secret"),
        FieldSet("cadence_days", "last_rotated_at", "next_due_at", "trigger_version", name="Intent"),
        FieldSet("host_role", "consumers", "semaphore_schedule_ref", name="Orchestration"),
    )

    class Meta:
        model = RotationPolicy
        fields = [
            "instance", "name", "secret_kind", "openbao_path", "cadence_days", "last_rotated_at",
            "next_due_at", "trigger_version", "host_role", "consumers", "semaphore_schedule_ref",
            "enabled", "tags",
        ]


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


class CatalogMcpServerForm(NetBoxModelForm):
    catalog = DynamicModelChoiceField(queryset=ServiceCatalog.objects.all())
    fieldsets = (
        FieldSet("catalog", "name", "description", "upstream_url", name="Companion"),
        FieldSet("source_type", "source", "default_version", name="Source"),
        FieldSet("transport", "default_port", "capability", name="Transport & trust"),
    )

    class Meta:
        model = CatalogMcpServer
        fields = [
            "catalog", "name", "source_type", "source", "default_version", "transport",
            "default_port", "capability", "upstream_url", "description", "tags",
        ]


class CatalogMcpServerParamForm(NetBoxModelForm):
    catalog_mcp = DynamicModelChoiceField(queryset=CatalogMcpServer.objects.all())
    fieldsets = (
        FieldSet("catalog_mcp", "key", "value_type", name="Param"),
        FieldSet("required", "default", "secret", "description", name="Contract"),
    )

    class Meta:
        model = CatalogMcpServerParam
        fields = [
            "catalog_mcp", "key", "value_type", "required", "default", "secret", "description", "tags",
        ]


class McpServerForm(NetBoxModelForm):
    service_instance = DynamicModelChoiceField(queryset=ServiceInstance.objects.all())
    catalog_mcp = DynamicModelChoiceField(queryset=CatalogMcpServer.objects.all())
    listeners = DynamicModelMultipleChoiceField(queryset=Service.objects.all(), required=False)
    fieldsets = (
        FieldSet("service_instance", "catalog_mcp", "version", "status", name="Companion"),
        FieldSet("transport", "bind_address", "listeners", name="Listener"),
        FieldSet("token_key", "auth_token_key", name="Credential references (OpenBao keys)"),
        FieldSet("autostart", "managed", name="Lifecycle"),
    )

    class Meta:
        model = McpServer
        fields = [
            "service_instance", "catalog_mcp", "version", "transport", "status", "bind_address",
            "listeners", "token_key", "auth_token_key", "autostart", "managed", "tags",
        ]


class McpServerParamForm(NetBoxModelForm):
    mcp_server = DynamicModelChoiceField(queryset=McpServer.objects.all())
    fieldsets = (FieldSet("mcp_server", "key", "value", name="Override value"),)

    class Meta:
        model = McpServerParam
        fields = ["mcp_server", "key", "value", "tags"]


# --------------------------------------------------------------------------- filter forms


class ServiceCatalogFilterForm(NetBoxModelFilterSetForm):
    model = ServiceCatalog
    database_type = forms.MultipleChoiceField(choices=DatabaseTypeChoices, required=False)
    ha_strategy = forms.MultipleChoiceField(choices=HAStrategyChoices, required=False)
    requires_gpu = forms.NullBooleanField(required=False)
    external = forms.NullBooleanField(required=False)
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
    mirror_mode = forms.MultipleChoiceField(choices=MirrorModeChoices, required=False)
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
    install_tier = forms.MultipleChoiceField(choices=ExtensionInstallTierChoices, required=False)
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
    vault_id = DynamicModelMultipleChoiceField(
        queryset=ServiceInstance.objects.filter(catalog__name=OPENBAO_CATALOG), required=False, label="Vault",
        query_params={"catalog": OPENBAO_CATALOG},
    )
    generator = forms.MultipleChoiceField(choices=InstanceOpenBaoPathGeneratorChoices, required=False)
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
    active_node = forms.MultipleChoiceField(choices=HAActiveNodeChoices, required=False)
    cloudflare_lb = forms.NullBooleanField(required=False, widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES))
    seeded = forms.NullBooleanField(required=False, widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES))
    tag = TagFilterField(HAMirror)


class HAMirrorPolicyFilterForm(NetBoxModelFilterSetForm):
    model = HAMirrorPolicy
    source_cluster_id = DynamicModelMultipleChoiceField(queryset=Cluster.objects.all(), required=False, label="Source cluster")
    target_cluster_id = DynamicModelMultipleChoiceField(queryset=Cluster.objects.all(), required=False, label="Target cluster")
    enabled = forms.NullBooleanField(required=False, widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES))
    tag = TagFilterField(HAMirrorPolicy)


class HostRoleFilterForm(NetBoxModelFilterSetForm):
    model = HostRole
    idempotent = forms.NullBooleanField(required=False)
    tag = TagFilterField(HostRole)


class RotationPolicyFilterForm(NetBoxModelFilterSetForm):
    model = RotationPolicy
    instance_id = DynamicModelMultipleChoiceField(queryset=ServiceInstance.objects.all(), required=False, label="Instance")
    host_role_id = DynamicModelMultipleChoiceField(queryset=HostRole.objects.all(), required=False, label="Host Role")
    consumer_id = DynamicModelMultipleChoiceField(queryset=ServiceInstance.objects.all(), required=False, label="Consumer")
    enabled = forms.NullBooleanField(required=False)
    tag = TagFilterField(RotationPolicy)


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


class CatalogMcpServerFilterForm(NetBoxModelFilterSetForm):
    model = CatalogMcpServer
    catalog_id = DynamicModelMultipleChoiceField(queryset=ServiceCatalog.objects.all(), required=False, label="Catalog")
    transport = forms.MultipleChoiceField(choices=McpTransportChoices, required=False)
    capability = forms.MultipleChoiceField(choices=McpCapabilityChoices, required=False)
    source_type = forms.MultipleChoiceField(choices=McpSourceTypeChoices, required=False)
    tag = TagFilterField(CatalogMcpServer)


class CatalogMcpServerParamFilterForm(NetBoxModelFilterSetForm):
    model = CatalogMcpServerParam
    catalog_mcp_id = DynamicModelMultipleChoiceField(
        queryset=CatalogMcpServer.objects.all(), required=False, label="Catalog MCP Server"
    )
    value_type = forms.MultipleChoiceField(choices=IntegrationParamValueTypeChoices, required=False)
    required = forms.NullBooleanField(required=False)
    secret = forms.NullBooleanField(required=False)
    tag = TagFilterField(CatalogMcpServerParam)


class McpServerFilterForm(NetBoxModelFilterSetForm):
    model = McpServer
    service_instance_id = DynamicModelMultipleChoiceField(
        queryset=ServiceInstance.objects.all(), required=False, label="Service Instance"
    )
    catalog_mcp_id = DynamicModelMultipleChoiceField(
        queryset=CatalogMcpServer.objects.all(), required=False, label="Catalog MCP Server"
    )
    status = forms.MultipleChoiceField(choices=ServiceInstanceStatusChoices, required=False)
    transport = forms.MultipleChoiceField(choices=McpTransportChoices, required=False)
    capability = forms.MultipleChoiceField(choices=McpCapabilityChoices, required=False)
    autostart = forms.NullBooleanField(required=False)
    managed = forms.NullBooleanField(required=False)
    tag = TagFilterField(McpServer)


class McpServerParamFilterForm(NetBoxModelFilterSetForm):
    model = McpServerParam
    mcp_server_id = DynamicModelMultipleChoiceField(
        queryset=McpServer.objects.all(), required=False, label="MCP Server"
    )
    tag = TagFilterField(McpServerParam)
