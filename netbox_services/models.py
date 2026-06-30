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

Every attribute is a real typed column or a child row — **no config_context, no CustomField
data-blob**. Secret *values* never live here; only OpenBao path references.
"""
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from ipam.choices import ServiceProtocolChoices
from netbox.models import NetBoxModel
from .choices import (
    DatabaseTypeChoices, DistroChoices, HAStrategyChoices, ProviderScopeChoices,
    ServiceInstanceStatusChoices,
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
