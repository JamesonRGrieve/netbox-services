# SPDX-License-Identifier: AGPL-3.0-or-later
"""The service catalog + instance source of truth.

**Catalog layer** (the upstream ``about.json`` is generated *from*): :class:`ServiceCatalog` plus
its child rows — :class:`CatalogCredential`, :class:`CatalogToken` (provides_tokens),
:class:`CatalogSecondaryPort` (verification.secondary_ports), :class:`IntegrationCatalog` (the
allowed integration types + cardinality), and :class:`CatalogTestState` /
:class:`CatalogTestIntegration` (the harness test matrix the harness writes back).

**Instance layer** (what the provider reads): :class:`ServiceInstance` (a deployed app on a guest
VM or raw-OS device; ports linked natively to ``ipam.Service``), :class:`InstanceOpenBaoPath`
(credential references), :class:`Integration` (the consumer→provider edge, with cardinality), and
:class:`HAMirror` (a mirror→primary HA pairing).

**Host-role layer** (the host-level analogue of the catalog/instance split above, scoped to
cross-service ansible roles rather than a named application): :class:`HostRole` (a scoped ansible
role/task-file catalog entry) plus :class:`HostRoleParam` (its typed var schema, mirroring
:class:`CatalogConfigParam`), :class:`HostRoleAssignment` (which target — a guest VM or raw-OS
device — runs the role and in what apply order), and :class:`HostRoleAssignmentVar` (per-assignment
var overrides, mirroring :class:`ServiceInstanceConfigValue`). This is the SoT the ``tofu-ansible``
provider's consuming module reads to emit ``ansible_role`` resources.

Every attribute is a real typed column or a child row — **no config_context, no CustomField
data-blob**. Secret *values* never live here; only OpenBao path references.
"""
from urllib.parse import urlparse

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from ipam.choices import ServiceProtocolChoices
from netbox.models import NetBoxModel
from .choices import (
    DatabaseTypeChoices, DistroChoices, ExtensionKindChoices, HAStrategyChoices,
    IntegrationParamValueTypeChoices, ProviderScopeChoices, ServiceInstanceStatusChoices,
)

# Content types a ServiceInstance may be installed onto (a guest VM or a raw-OS device).
PARENT_CT_LIMIT = models.Q(app_label="dcim", model="device") | models.Q(
    app_label="virtualization", model="virtualmachine"
)


# --------------------------------------------------------------------------- catalog layer


class ServiceCatalog(NetBoxModel):
    """A service *type* (the about.json catalog row). NetBox is the SoT; about.json is generated
    from this. ``name`` is the stable catalog key (the playbook directory name)."""

    name = models.SlugField(max_length=100, unique=True, help_text="Catalog key (app directory name).")
    display_name = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True)
    repo = models.URLField(blank=True)
    docs = models.URLField(blank=True)
    license = models.CharField(max_length=100, blank=True)
    tier = models.PositiveSmallIntegerField(default=1, help_text="Test tier (distro breadth).")
    requires_gpu = models.BooleanField(default=False)

    # Resources (flat columns, not a blob): install vs runtime, in MiB / cores / GiB.
    default_port = models.PositiveIntegerField(null=True, blank=True)
    install_memory = models.PositiveIntegerField(null=True, blank=True, help_text="MiB.")
    install_cores = models.PositiveSmallIntegerField(null=True, blank=True)
    runtime_memory = models.PositiveIntegerField(null=True, blank=True, help_text="MiB.")
    runtime_cores = models.PositiveSmallIntegerField(null=True, blank=True)
    disk = models.PositiveIntegerField(null=True, blank=True, help_text="GiB.")

    # Lifecycle playbooks (paths relative to the ansible repo's application dir).
    playbook = models.CharField(max_length=255, blank=True)
    init_playbook = models.CharField(max_length=255, blank=True)
    customize_playbook = models.CharField(max_length=255, blank=True)
    unlock_playbook = models.CharField(max_length=255, blank=True)

    # Verification (about.json verification{}).
    health_endpoint = models.CharField(max_length=255, blank=True)
    health_status_codes = ArrayField(
        models.PositiveSmallIntegerField(), default=list, blank=True,
        help_text="HTTP status codes treated as healthy.",
    )
    requires_database = models.BooleanField(default=False)
    database_type = models.CharField(max_length=16, choices=DatabaseTypeChoices, blank=True)
    requires_cache = models.BooleanField(default=False)

    # HA (about.json/§7): the data-sync strategy + whether the type is fronted by an HAProxy
    # backup. Mirrors materialize these per HAMirror edge.
    ha_strategy = models.CharField(
        max_length=32, choices=HAStrategyChoices, default=HAStrategyChoices.NONE
    )
    ingress_haproxy_backup = models.BooleanField(
        default=False, help_text="Register the mirror's edge as an HAProxy backup in the primary's pool."
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Service Catalog"
        verbose_name_plural = "Service Catalog"

    def __str__(self):
        return self.display_name or self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:servicecatalog", args=[self.pk])

    def get_ha_strategy_color(self):
        return HAStrategyChoices.colors.get(self.ha_strategy)


class CatalogCredential(NetBoxModel):
    """A credential the type provisions at install (about.json ``credentials[]``). ``deploy_var`` is
    the ansible var the generated password is passed as; the value lives in OpenBao, never here."""

    catalog = models.ForeignKey(ServiceCatalog, on_delete=models.CASCADE, related_name="credentials")
    cred_id = models.CharField(max_length=100, help_text="Credential id (e.g. admin_pass).")
    length = models.PositiveSmallIntegerField(default=24, help_text="Generated length.")
    deploy_var = models.CharField(max_length=200, help_text="Ansible deploy var the value is passed as.")

    class Meta:
        ordering = ["catalog", "cred_id"]
        verbose_name = "Catalog Credential"
        constraints = [
            models.UniqueConstraint(
                fields=["catalog", "cred_id"], name="netbox_services_catalogcredential_unique"
            )
        ]

    def __str__(self):
        return f"{self.catalog.name}: {self.cred_id}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:catalogcredential", args=[self.pk])


class CatalogToken(NetBoxModel):
    """A token the type publishes after init (about.json ``provides_tokens``): ``name`` → the output
    var/file the init playbook writes. Consumers wire these in via ``Integration.requires_tokens``."""

    catalog = models.ForeignKey(ServiceCatalog, on_delete=models.CASCADE, related_name="tokens")
    name = models.CharField(max_length=100, help_text="Token name (e.g. authentik_api_token).")
    output_var = models.CharField(max_length=200, help_text="Init output var/file (or _ct_url sentinel).")

    class Meta:
        ordering = ["catalog", "name"]
        verbose_name = "Catalog Token"
        constraints = [
            models.UniqueConstraint(
                fields=["catalog", "name"], name="netbox_services_catalogtoken_unique"
            )
        ]

    def __str__(self):
        return f"{self.catalog.name}: {self.name}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:catalogtoken", args=[self.pk])


class CatalogSecondaryPort(NetBoxModel):
    """An additional listener the type opens beyond ``default_port`` (about.json
    ``verification.secondary_ports[]``). Realized per deployment as ``ipam.Service`` rows linked to
    the instance; this is the *type-level default*."""

    catalog = models.ForeignKey(ServiceCatalog, on_delete=models.CASCADE, related_name="secondary_ports")
    port = models.PositiveIntegerField()
    protocol = models.CharField(max_length=8, choices=ServiceProtocolChoices, default=ServiceProtocolChoices.PROTOCOL_TCP)
    name = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["catalog", "port"]
        verbose_name = "Catalog Secondary Port"
        constraints = [
            models.UniqueConstraint(
                fields=["catalog", "port", "protocol"],
                name="netbox_services_catalogsecondaryport_unique",
            )
        ]

    def __str__(self):
        return f"{self.catalog.name}: {self.port}/{self.protocol}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:catalogsecondaryport", args=[self.pk])


class IntegrationCatalog(NetBoxModel):
    """An allowed integration of a consumer type (about.json ``integrations[]``) + its cardinality.
    ``type`` is the integration name; ``requires_service`` is the provider type. ``provider_scope`` /
    ``consumer_max`` bound the realized :class:`Integration` edges (validated, not DB-enforced)."""

    catalog = models.ForeignKey(ServiceCatalog, on_delete=models.CASCADE, related_name="integration_catalog")
    type = models.CharField(max_length=100, help_text="Integration name (e.g. openbao).")
    requires_service = models.CharField(max_length=100, help_text="Provider catalog name.")
    requires_tokens = ArrayField(models.CharField(max_length=100), default=list, blank=True)
    playbook = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    provider_scope = models.CharField(
        max_length=16, choices=ProviderScopeChoices, default=ProviderScopeChoices.SHARED
    )
    consumer_max = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Max provider instances of this type a consumer may bind (null = unbounded)."
    )

    class Meta:
        ordering = ["catalog", "type"]
        verbose_name = "Integration Catalog"
        verbose_name_plural = "Integration Catalog"
        constraints = [
            models.UniqueConstraint(
                fields=["catalog", "type"], name="netbox_services_integrationcatalog_unique"
            )
        ]

    def __str__(self):
        return f"{self.catalog.name} → {self.type}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:integrationcatalog", args=[self.pk])

    def get_provider_scope_color(self):
        return ProviderScopeChoices.colors.get(self.provider_scope)


class IntegrationCatalogParam(NetBoxModel):
    """A config param an integration *type* accepts (the typed schema for the per-edge params that
    today live inline in each ``integrate_*.yml``: SSO redirect URIs/scopes/claims, cache db-index,
    S3 bucket/prefix, SMTP from-address, …). ``default`` is the catalog default; an edge stores an
    :class:`IntegrationParam` row **only when it overrides** this (or for a required param with no
    default). ``secret`` ⇒ the value is a ``secret_ref`` (OpenBao path), never an inline value."""

    integration_catalog = models.ForeignKey(
        IntegrationCatalog, on_delete=models.CASCADE, related_name="params"
    )
    key = models.CharField(max_length=100, help_text="Param key (e.g. redirect_uris, db_index, bucket).")
    value_type = models.CharField(max_length=16, choices=IntegrationParamValueTypeChoices)
    required = models.BooleanField(default=False)
    default = models.CharField(
        max_length=255, blank=True, help_text="Catalog default; an edge stores a row only when it overrides this."
    )
    secret = models.BooleanField(
        default=False, help_text="When set, the value is a secret_ref (OpenBao path), never an inline value."
    )
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["integration_catalog", "key"]
        verbose_name = "Integration Catalog Param"
        constraints = [
            models.UniqueConstraint(
                fields=["integration_catalog", "key"],
                name="netbox_services_integrationcatalogparam_unique_catalog_key",
            )
        ]

    def __str__(self):
        return f"{self.integration_catalog}: {self.key}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:integrationcatalogparam", args=[self.pk])

    def get_value_type_color(self):
        return IntegrationParamValueTypeChoices.colors.get(self.value_type)


class CatalogConfigParam(NetBoxModel):
    """A declarative config attribute a service *type* accepts (the typed schema for the service's
    OWN source-of-truthable config — listen address, worker count, feature flags, an admin email,
    a secret_ref for an API key, …). This is the service-config analogue of
    :class:`IntegrationCatalogParam` (which types the per-*edge* integration params); it types the
    per-*instance* values stored in :class:`ServiceInstanceConfigValue`. ``default`` is the catalog
    default — an instance stores a row **only when it overrides** this (or for a required param with
    no default). ``secret`` ⇒ the value is a ``secret_ref`` (OpenBao path), never an inline value.
    ``provider_attr`` is the ``resource.attribute`` the in-house ``tofu-services`` provider maps this
    param onto. ``value_type`` reuses :class:`IntegrationParamValueTypeChoices` — the same
    typed-value domain (string / int / bool / url / list / secret_ref)."""

    catalog = models.ForeignKey(ServiceCatalog, on_delete=models.CASCADE, related_name="config_params")
    key = models.CharField(max_length=100, help_text="Config attribute key (e.g. listen_addr, workers, admin_email).")
    value_type = models.CharField(max_length=16, choices=IntegrationParamValueTypeChoices)
    required = models.BooleanField(default=False)
    default = models.CharField(
        max_length=255, blank=True,
        help_text="Catalog default; an instance stores a row only when it overrides this.",
    )
    secret = models.BooleanField(
        default=False, help_text="When set, the value is a secret_ref (OpenBao path), never an inline value."
    )
    provider_attr = models.CharField(
        max_length=200, blank=True,
        help_text="The resource.attribute the tofu-services provider maps this param onto.",
    )
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["catalog", "key"]
        verbose_name = "Catalog Config Param"
        constraints = [
            models.UniqueConstraint(
                fields=["catalog", "key"],
                name="netbox_services_catalogconfigparam_unique_catalog_key",
            )
        ]

    def __str__(self):
        return f"{self.catalog.name}: {self.key}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:catalogconfigparam", args=[self.pk])

    def get_value_type_color(self):
        return IntegrationParamValueTypeChoices.colors.get(self.value_type)


class CatalogExtension(NetBoxModel):
    """A known/default extension (plugin / theme / app / module) of a service *type* — the
    catalog-level inventory used for optional defaults + validation. ``default_version`` is the
    version the type ships/pins by default; ``required`` marks an extension the type mandates. This
    is only the *known* set — an instance may still declare arbitrary extensions beyond it (see
    :class:`ServiceInstanceExtension`)."""

    catalog = models.ForeignKey(ServiceCatalog, on_delete=models.CASCADE, related_name="extensions")
    kind = models.CharField(max_length=16, choices=ExtensionKindChoices)
    name = models.CharField(max_length=200, help_text="Extension name (e.g. akismet, twentytwentyfour).")
    default_version = models.CharField(
        max_length=100, blank=True, help_text="Version the type ships/pins by default (blank = latest)."
    )
    required = models.BooleanField(default=False, help_text="The type mandates this extension.")
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["catalog", "kind", "name"]
        verbose_name = "Catalog Extension"
        constraints = [
            models.UniqueConstraint(
                fields=["catalog", "kind", "name"],
                name="netbox_services_catalogextension_unique_catalog_kind_name",
            )
        ]

    def __str__(self):
        return f"{self.catalog.name}: {self.kind}/{self.name}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:catalogextension", args=[self.pk])

    def get_kind_color(self):
        return ExtensionKindChoices.colors.get(self.kind)


class CatalogTestState(NetBoxModel):
    """Harness test result for a (catalog, distro): which lifecycle stages passed + telemetry. The
    harness (a Semaphore job) writes this back; it is the home of today's about.json ``state{}``."""

    catalog = models.ForeignKey(ServiceCatalog, on_delete=models.CASCADE, related_name="test_states")
    distro = models.CharField(max_length=16, choices=DistroChoices)
    install = models.BooleanField(default=False)
    init = models.BooleanField(default=False)
    customize = models.BooleanField(default=False)
    unlock = models.BooleanField(default=False)
    peak_memory_mb = models.PositiveIntegerField(null=True, blank=True)
    peak_cpu_load = models.FloatField(null=True, blank=True)
    install_duration_s = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["catalog", "distro"]
        verbose_name = "Catalog Test State"
        constraints = [
            models.UniqueConstraint(
                fields=["catalog", "distro"], name="netbox_services_catalogteststate_unique"
            )
        ]

    def __str__(self):
        return f"{self.catalog.name} [{self.distro}]"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:catalogteststate", args=[self.pk])


class CatalogTestIntegration(NetBoxModel):
    """Per-provider integration test result within a :class:`CatalogTestState` (about.json
    ``state.{distro}.integrate.{provider}``)."""

    test_state = models.ForeignKey(CatalogTestState, on_delete=models.CASCADE, related_name="integrations")
    provider_service = models.CharField(max_length=100)
    passed = models.BooleanField(default=False)

    class Meta:
        ordering = ["test_state", "provider_service"]
        verbose_name = "Catalog Test Integration"
        constraints = [
            models.UniqueConstraint(
                fields=["test_state", "provider_service"],
                name="netbox_services_catalogtestintegration_unique",
            )
        ]

    def __str__(self):
        return f"{self.test_state}: {self.provider_service} = {self.passed}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:catalogtestintegration", args=[self.pk])


# --------------------------------------------------------------------------- instance layer


class ServiceInstance(NetBoxModel):
    """A deployed app on a guest VM or raw-OS device — the row the ``tofu-services`` provider reads.
    ``parent`` is the install target (GFK → ``virtualization.virtualmachine`` | ``dcim.device``);
    ports are native ``ipam.Service`` rows linked via ``listeners`` (no port column here)."""

    catalog = models.ForeignKey(ServiceCatalog, on_delete=models.PROTECT, related_name="instances")
    parent_object_type = models.ForeignKey(
        "contenttypes.ContentType", on_delete=models.PROTECT, related_name="+",
        limit_choices_to=PARENT_CT_LIMIT,
    )
    parent_object_id = models.PositiveBigIntegerField()
    parent = GenericForeignKey("parent_object_type", "parent_object_id")
    hostname = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20, choices=ServiceInstanceStatusChoices, default=ServiceInstanceStatusChoices.STAGED
    )
    actual_memory = models.PositiveIntegerField(null=True, blank=True, help_text="MiB.")
    actual_cores = models.PositiveSmallIntegerField(null=True, blank=True)
    actual_disk = models.PositiveIntegerField(null=True, blank=True, help_text="GiB.")
    listeners = models.ManyToManyField(
        "ipam.Service", related_name="service_instances", blank=True,
        help_text="The L4 listeners this instance exposes (ports live in IPAM).",
    )

    class Meta:
        ordering = ["catalog", "hostname"]
        verbose_name = "Service Instance"
        indexes = [models.Index(fields=["parent_object_type", "parent_object_id"], name="netbox_serv_parent__idx")]

    def __str__(self):
        return f"{self.catalog.name} @ {self.hostname or self.parent}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:serviceinstance", args=[self.pk])

    def get_status_color(self):
        return ServiceInstanceStatusChoices.colors.get(self.status)


class InstanceOpenBaoPath(NetBoxModel):
    """An OpenBao path reference for one of an instance's credentials / published tokens
    (about.json ``credentials``/``provides_tokens`` realized per instance). ``key`` is the logical
    name; ``path`` is the OpenBao location — never the secret value."""

    instance = models.ForeignKey(ServiceInstance, on_delete=models.CASCADE, related_name="openbao_paths")
    key = models.CharField(max_length=100, help_text="Logical credential/token name.")
    path = models.CharField(max_length=255, help_text="OpenBao path (reference, never the secret).")

    class Meta:
        ordering = ["instance", "key"]
        verbose_name = "Instance OpenBao Path"
        constraints = [
            models.UniqueConstraint(
                fields=["instance", "key"], name="netbox_services_instanceopenbaopath_unique"
            )
        ]

    def __str__(self):
        return f"{self.instance}: {self.key}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:instanceopenbaopath", args=[self.pk])


def validate_integration_cardinality(integration):
    """Shared cardinality + consistency check for an :class:`Integration`. Called by both
    ``Integration.clean()`` (form/serializer path) and the ``pre_save`` signal (the ORM/seeder/
    migration backstop). ``consumer_max`` is a count check and cannot be a DB constraint, so this
    is validation-only and can race under truly-concurrent writes (documented; acceptable)."""
    if integration.consumer_id and integration.provider_id and integration.consumer_id == integration.provider_id:
        raise ValidationError("A service cannot integrate with itself.")
    if not (integration.consumer_id and integration.provider_id and integration.type):
        return

    catalog_entry = IntegrationCatalog.objects.filter(
        catalog=integration.consumer.catalog, type=integration.type
    ).first()
    if catalog_entry is None:
        raise ValidationError(
            f"{integration.consumer.catalog.name} has no catalog integration '{integration.type}'."
        )
    if integration.provider.catalog.name != catalog_entry.requires_service:
        raise ValidationError(
            f"Integration '{integration.type}' requires a {catalog_entry.requires_service} provider, "
            f"got {integration.provider.catalog.name}."
        )

    # consumer_max limits how many *distinct providers* a consumer binds for this type. A re-save
    # of the same provider is a duplicate edge (caught by the unique constraint), not a new
    # binding, so exclude same-provider siblings — otherwise a duplicate trips this check before
    # the DB constraint can raise IntegrityError.
    siblings = Integration.objects.filter(consumer=integration.consumer, type=integration.type)
    if integration.provider_id:
        siblings = siblings.exclude(provider_id=integration.provider_id)
    if integration.pk:
        siblings = siblings.exclude(pk=integration.pk)
    if catalog_entry.consumer_max is not None and siblings.count() >= catalog_entry.consumer_max:
        raise ValidationError(
            f"{integration.consumer} already binds {catalog_entry.consumer_max} '{integration.type}' "
            f"provider(s) (consumer_max reached)."
        )
    if catalog_entry.provider_scope == ProviderScopeChoices.DEDICATED:
        others = Integration.objects.filter(provider=integration.provider, type=integration.type)
        if integration.pk:
            others = others.exclude(pk=integration.pk)
        if others.exists():
            raise ValidationError(
                f"Provider {integration.provider} is dedicated for '{integration.type}' and already "
                f"serves another consumer."
            )


def _integration_catalog_entry(integration):
    """Resolve the consumer catalog's :class:`IntegrationCatalog` row for an edge's type (or None).
    An :class:`IntegrationParam` is validated against that entry's :class:`IntegrationCatalogParam`
    schema — the params an integration *type* accepts."""
    if not (integration.consumer_id and integration.type):
        return None
    return IntegrationCatalog.objects.filter(
        catalog=integration.consumer.catalog, type=integration.type
    ).first()


def validate_integration_params(integration):
    """Completeness backstop: every required catalog param **without a default** must have an
    instance :class:`IntegrationParam` row on the edge. Guarded on ``pk`` — params can only exist
    once the edge does, so this validates on update (or an explicit re-clean), never blocking the
    edge's first create. Effective config = catalog defaults overlaid with the instance rows."""
    if not integration.pk:
        return
    entry = _integration_catalog_entry(integration)
    if entry is None:
        return
    present = set(integration.params.values_list("key", flat=True))
    missing = sorted(
        p.key for p in entry.params.filter(required=True) if not p.default and p.key not in present
    )
    if missing:
        raise ValidationError(
            f"Integration '{integration.type}' is missing required param(s): {', '.join(missing)}."
        )


class Integration(NetBoxModel):
    """A realized consumer→provider binding (the instance edge the catalog lacks). ``type`` matches
    the consumer catalog's :class:`IntegrationCatalog` entry, against which cardinality is checked."""

    consumer = models.ForeignKey(ServiceInstance, on_delete=models.CASCADE, related_name="integrations_out")
    provider = models.ForeignKey(ServiceInstance, on_delete=models.CASCADE, related_name="integrations_in")
    type = models.CharField(max_length=100, help_text="Integration name (matches the consumer's IntegrationCatalog).")
    requires_tokens = ArrayField(models.CharField(max_length=100), default=list, blank=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["consumer", "type", "provider"]
        verbose_name = "Integration"
        constraints = [
            models.UniqueConstraint(
                fields=["consumer", "type", "provider"], name="netbox_services_integration_unique"
            )
        ]

    def __str__(self):
        return f"{self.consumer} → {self.type} → {self.provider}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:integration", args=[self.pk])

    def clean(self):
        super().clean()
        validate_integration_cardinality(self)
        validate_integration_params(self)


def validate_integration_param_value(catalog_param, value):
    """Parse-check an :class:`IntegrationParam.value` against its :class:`IntegrationCatalogParam`.
    A ``secret`` param (or ``secret_ref`` type) must be an OpenBao **path reference** — it must
    contain ``/`` and must not look like an inline literal (a URL ``://`` or an email ``@``); an
    inline value there is rejected (secret *values* never live in NetBox). Otherwise the value must
    parse for its ``value_type`` (``int`` → ``int()``, ``bool`` → true/false, ``url`` → scheme +
    host). ``string`` / ``list`` carry no structural constraint (``list`` order is preserved by its
    newline-delimited storage)."""
    is_secret = catalog_param.secret or catalog_param.value_type == IntegrationParamValueTypeChoices.SECRET_REF
    if is_secret:
        if "://" in value or "@" in value or "/" not in value:
            raise ValidationError(
                f"Param '{catalog_param.key}' is a secret: store an OpenBao path reference "
                f"(must contain '/', never an inline value), got '{value}'."
            )
        return
    value_type = catalog_param.value_type
    if value_type == IntegrationParamValueTypeChoices.INT:
        try:
            int(value)
        except (TypeError, ValueError):
            raise ValidationError(f"Param '{catalog_param.key}' must be an integer, got '{value}'.")
    elif value_type == IntegrationParamValueTypeChoices.BOOL:
        if value.strip().lower() not in {"true", "false"}:
            raise ValidationError(f"Param '{catalog_param.key}' must be 'true' or 'false', got '{value}'.")
    elif value_type == IntegrationParamValueTypeChoices.URL:
        parsed = urlparse(value)
        if not (parsed.scheme and parsed.netloc):
            raise ValidationError(f"Param '{catalog_param.key}' must be a URL with a scheme, got '{value}'.")


def validate_integration_param(param):
    """Every :class:`IntegrationParam` key must be a declared :class:`IntegrationCatalogParam` for
    the edge's integration type (resolved via the consumer catalog's :class:`IntegrationCatalog`),
    and its ``value`` must satisfy :func:`validate_integration_param_value`."""
    if not (param.integration_id and param.key):
        return
    entry = _integration_catalog_entry(param.integration)
    if entry is None:
        raise ValidationError(
            f"Integration '{param.integration.type}' has no catalog entry; cannot validate param '{param.key}'."
        )
    catalog_param = IntegrationCatalogParam.objects.filter(integration_catalog=entry, key=param.key).first()
    if catalog_param is None:
        raise ValidationError(
            f"'{param.key}' is not a declared param of integration '{param.integration.type}'."
        )
    validate_integration_param_value(catalog_param, param.value)


class IntegrationParam(NetBoxModel):
    """A per-edge config param value on ONE :class:`Integration` — the instance-level SoT for the
    parameters that today live inline in each ``integrate_*.yml``. Stored **only on override** of
    the catalog default (or for a required param with no default); the consumer merges catalog
    defaults with these rows for the effective config. ``value`` is rendered per the matched
    :class:`IntegrationCatalogParam`'s ``value_type`` (``list`` = newline-delimited, order
    preserved; ``secret_ref`` = OpenBao path reference, never the secret value)."""

    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name="params")
    key = models.CharField(max_length=100, help_text="Matches an IntegrationCatalogParam.key for the edge's type.")
    value = models.CharField(
        max_length=255, help_text="Rendered per value_type (list = newline-delimited; secret_ref = OpenBao path)."
    )

    class Meta:
        ordering = ["integration", "key"]
        verbose_name = "Integration Param"
        constraints = [
            models.UniqueConstraint(
                fields=["integration", "key"], name="netbox_services_integrationparam_unique_integration_key"
            )
        ]

    def __str__(self):
        return f"{self.integration}: {self.key}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:integrationparam", args=[self.pk])

    def clean(self):
        super().clean()
        validate_integration_param(self)


def validate_service_instance_config_value(config_value):
    """Validate a :class:`ServiceInstanceConfigValue`. The referenced :class:`CatalogConfigParam`
    must belong to the **instance's own service type** (an instance may only override config params
    declared on its catalog), and its ``value`` must satisfy the param's typed contract via
    :func:`validate_integration_param_value` (the shared typed-value validator: ``int`` parses,
    ``bool`` is true/false, ``url`` has a scheme + host, a ``secret`` param must be an OpenBao path
    reference — never an inline value)."""
    if not (config_value.instance_id and config_value.param_id):
        return
    if config_value.param.catalog_id != config_value.instance.catalog_id:
        raise ValidationError(
            f"Config param '{config_value.param.key}' belongs to {config_value.param.catalog.name}, "
            f"not the instance's service type {config_value.instance.catalog.name}."
        )
    validate_integration_param_value(config_value.param, config_value.value)


class ServiceInstanceConfigValue(NetBoxModel):
    """A per-instance override of ONE of a service type's declarative config attributes — the
    instance-level SoT for the parameters typed by :class:`CatalogConfigParam`. Stored **only on
    override** of the catalog default (or for a required param with no default); the provider merges
    catalog defaults with these rows for the effective config. ``value`` is rendered per the linked
    :class:`CatalogConfigParam`'s ``value_type`` (``list`` = newline-delimited, order preserved;
    a ``secret`` param = OpenBao path reference, never the secret value). This is the service-config
    analogue of :class:`IntegrationParam` (the per-edge override)."""

    instance = models.ForeignKey(ServiceInstance, on_delete=models.CASCADE, related_name="config_values")
    param = models.ForeignKey(CatalogConfigParam, on_delete=models.CASCADE, related_name="instance_values")
    value = models.CharField(
        max_length=255, help_text="Rendered per value_type (list = newline-delimited; secret = OpenBao path)."
    )

    class Meta:
        ordering = ["instance", "param"]
        verbose_name = "Service Instance Config Value"
        constraints = [
            models.UniqueConstraint(
                fields=["instance", "param"],
                name="netbox_services_serviceinstanceconfigvalue_unique_instance_param",
            )
        ]

    def __str__(self):
        return f"{self.instance}: {self.param.key}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:serviceinstanceconfigvalue", args=[self.pk])

    def clean(self):
        super().clean()
        validate_service_instance_config_value(self)


class ServiceInstanceExtension(NetBoxModel):
    """THE per-instance declared extension inventory — one row per installed plugin / theme / app /
    module on a :class:`ServiceInstance`. Arbitrary: any extension may be installed on any instance,
    so this deliberately does **not** FK a :class:`CatalogExtension` (the catalog set is only the
    known/default subset). ``version`` blank ⇒ track latest; ``enabled`` toggles activation without
    removal; ``managed`` marks whether the ``tofu-services`` provider owns this extension's
    lifecycle (vs. an out-of-band install the SoT merely records)."""

    instance = models.ForeignKey(ServiceInstance, on_delete=models.CASCADE, related_name="extensions")
    kind = models.CharField(max_length=16, choices=ExtensionKindChoices)
    name = models.CharField(max_length=200, help_text="Extension name (e.g. akismet, twentytwentyfour).")
    version = models.CharField(max_length=100, blank=True, help_text="Pinned version (blank = track latest).")
    enabled = models.BooleanField(default=True, help_text="Extension is activated on the instance.")
    managed = models.BooleanField(
        default=True, help_text="The tofu-services provider owns this extension's lifecycle."
    )

    class Meta:
        ordering = ["instance", "kind", "name"]
        verbose_name = "Service Instance Extension"
        constraints = [
            models.UniqueConstraint(
                fields=["instance", "kind", "name"],
                name="netbox_services_serviceinstanceextension_unique_instance_kind_name",
            )
        ]

    def __str__(self):
        return f"{self.instance}: {self.kind}/{self.name}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:serviceinstanceextension", args=[self.pk])

    def get_kind_color(self):
        return ExtensionKindChoices.colors.get(self.kind)


class HAMirror(NetBoxModel):
    """A mirror→primary HA pairing for one service (e.g. the mirror WordPress → the primary
    WordPress). The reconciler reads ``mirror.catalog.ha_strategy`` to pick the mechanism; both
    instances must be the same catalog type."""

    mirror = models.ForeignKey(ServiceInstance, on_delete=models.CASCADE, related_name="ha_mirror_of")
    primary = models.ForeignKey(ServiceInstance, on_delete=models.CASCADE, related_name="ha_mirrors")

    class Meta:
        ordering = ["primary", "mirror"]
        verbose_name = "HA Mirror"
        constraints = [
            models.UniqueConstraint(
                fields=["mirror", "primary"], name="netbox_services_hamirror_unique"
            )
        ]

    def __str__(self):
        return f"{self.mirror} ⇒ mirror of {self.primary}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:hamirror", args=[self.pk])

    def clean(self):
        super().clean()
        if self.mirror_id and self.primary_id:
            if self.mirror_id == self.primary_id:
                raise ValidationError("A service instance cannot be its own HA mirror.")
            if self.mirror.catalog_id != self.primary.catalog_id:
                raise ValidationError("HA mirror and primary must be the same service type.")


# --------------------------------------------------------------------------- host-role layer


class HostRole(NetBoxModel):
    """A scoped ansible role/task-file catalog entry — the host-level analogue of
    :class:`ServiceCatalog`, applied to a target regardless of which (if any) application also
    runs there. ``name`` is the stable catalog key; ``playbook`` is the task-file/playbook path
    relative to the ansible repo (e.g. ``common/baremetal/install_fail2ban.yml``); ``ansible_tags``
    scopes which tagged block(s) of a shared playbook to run when the role is one of several tagged
    sections rather than its own file. ``idempotent`` documents whether a re-apply is a safe no-op
    (the consuming tofu module's contract with the operator; not enforced here)."""

    name = models.SlugField(max_length=100, unique=True, help_text="Catalog key (ansible role/task-file identifier).")
    display_name = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True)
    playbook = models.CharField(
        max_length=255, blank=True, help_text="Task-file/playbook path relative to the ansible repo.",
    )
    ansible_tags = ArrayField(
        models.CharField(max_length=100), default=list, blank=True,
        help_text="ansible-playbook --tags scope, when the role is a tagged block of a shared playbook.",
    )
    idempotent = models.BooleanField(default=True, help_text="Safe to re-apply without side effects.")

    class Meta:
        ordering = ["name"]
        verbose_name = "Host Role"

    def __str__(self):
        return self.display_name or self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:hostrole", args=[self.pk])


class HostRoleParam(NetBoxModel):
    """A typed var a host role accepts — the :class:`CatalogConfigParam` analogue for
    :class:`HostRole`. ``default`` is the catalog default; a :class:`HostRoleAssignment` stores a
    :class:`HostRoleAssignmentVar` row **only when it overrides** this (or for a required param with
    no default). ``secret`` ⇒ the value is a ``secret_ref`` (OpenBao path), never inline."""

    role = models.ForeignKey(HostRole, on_delete=models.CASCADE, related_name="params")
    key = models.CharField(max_length=100, help_text="Var key (e.g. wordpress_php_disable_functions).")
    value_type = models.CharField(max_length=16, choices=IntegrationParamValueTypeChoices)
    required = models.BooleanField(default=False)
    default = models.CharField(
        max_length=255, blank=True,
        help_text="Catalog default; an assignment stores a row only when it overrides this.",
    )
    secret = models.BooleanField(
        default=False, help_text="When set, the value is a secret_ref (OpenBao path), never an inline value."
    )
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["role", "key"]
        verbose_name = "Host Role Param"
        constraints = [
            models.UniqueConstraint(fields=["role", "key"], name="netbox_services_hostroleparam_unique_role_key")
        ]

    def __str__(self):
        return f"{self.role.name}: {self.key}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:hostroleparam", args=[self.pk])

    def get_value_type_color(self):
        return IntegrationParamValueTypeChoices.colors.get(self.value_type)


class HostRoleAssignment(NetBoxModel):
    """Which target — a guest VM or a raw-OS device — runs a :class:`HostRole`, and in what apply
    order among the target's other assignments. ``target`` follows the same GFK pattern as
    :attr:`ServiceInstance.parent` (limited to ``dcim.Device`` | ``virtualization.VirtualMachine`` via
    the shared :data:`PARENT_CT_LIMIT`); a role is unrelated to any particular :class:`ServiceInstance`
    on the same target — it applies at the host/OS level regardless of which app(s) run there."""

    role = models.ForeignKey(HostRole, on_delete=models.PROTECT, related_name="assignments")
    target_object_type = models.ForeignKey(
        "contenttypes.ContentType", on_delete=models.PROTECT, related_name="+",
        limit_choices_to=PARENT_CT_LIMIT,
    )
    target_object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("target_object_type", "target_object_id")
    order = models.PositiveSmallIntegerField(
        default=0, help_text="Apply ordering among this target's assignments (ascending)."
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["target_object_type", "target_object_id", "order", "role"]
        verbose_name = "Host Role Assignment"
        indexes = [models.Index(fields=["target_object_type", "target_object_id"], name="netbox_serv_hr_target_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["target_object_type", "target_object_id", "role"],
                name="netbox_services_hostroleassignment_unique_target_role",
            )
        ]

    def __str__(self):
        return f"{self.target} → {self.role}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:hostroleassignment", args=[self.pk])


def validate_host_role_assignment_var(assignment_var):
    """Validate a :class:`HostRoleAssignmentVar`. The referenced :class:`HostRoleParam` must belong
    to the assignment's **own role** (an assignment may only override params declared on its role),
    and its ``value`` must satisfy the param's typed contract via
    :func:`validate_integration_param_value` (the shared typed-value validator)."""
    if not (assignment_var.assignment_id and assignment_var.param_id):
        return
    if assignment_var.param.role_id != assignment_var.assignment.role_id:
        raise ValidationError(
            f"Var param '{assignment_var.param.key}' belongs to role {assignment_var.param.role.name}, "
            f"not the assignment's role {assignment_var.assignment.role.name}."
        )
    validate_integration_param_value(assignment_var.param, assignment_var.value)


class HostRoleAssignmentVar(NetBoxModel):
    """A per-assignment override of ONE of a role's typed vars — the instance-level SoT for the
    parameters typed by :class:`HostRoleParam`. Stored **only on override** of the catalog default
    (or for a required param with no default); the consuming tofu module merges catalog defaults with
    these rows for the effective ``ansible_role`` vars. ``value`` is rendered per the linked
    :class:`HostRoleParam`'s ``value_type`` (``list`` = newline-delimited, order preserved; a
    ``secret`` param = OpenBao path reference, never the secret value). This is the host-role
    analogue of :class:`ServiceInstanceConfigValue`."""

    assignment = models.ForeignKey(HostRoleAssignment, on_delete=models.CASCADE, related_name="vars")
    param = models.ForeignKey(HostRoleParam, on_delete=models.CASCADE, related_name="assignment_values")
    value = models.CharField(
        max_length=255, help_text="Rendered per value_type (list = newline-delimited; secret = OpenBao path)."
    )

    class Meta:
        ordering = ["assignment", "param"]
        verbose_name = "Host Role Assignment Var"
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "param"],
                name="netbox_services_hostroleassignmentvar_unique_assignment_param",
            )
        ]

    def __str__(self):
        return f"{self.assignment}: {self.param.key}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_services:hostroleassignmentvar", args=[self.pk])

    def clean(self):
        super().clean()
        validate_host_role_assignment_var(self)
