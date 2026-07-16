# SPDX-License-Identifier: AGPL-3.0-or-later
"""Choice sets for the service catalog + instance models. Protocol for catalog ports reuses
core ``ipam.choices.ServiceProtocolChoices`` (not duplicated here)."""
from utilities.choices import ChoiceSet


class ServiceInstanceStatusChoices(ChoiceSet):
    """Lifecycle status of a deployed service instance."""
    STAGED = "staged"
    ACTIVE = "active"
    OFFLINE = "offline"
    FAILED = "failed"
    DECOMMISSIONING = "decommissioning"
    CHOICES = [
        (STAGED, "Staged", "blue"),
        (ACTIVE, "Active", "green"),
        (OFFLINE, "Offline", "gray"),
        (FAILED, "Failed", "red"),
        (DECOMMISSIONING, "Decommissioning", "orange"),
    ]


class ProviderScopeChoices(ChoiceSet):
    """Allowed provider sharing for an integration type. ``shared`` = one provider instance serves
    many consumers (N:1); ``dedicated`` = one provider instance per consumer (1:1)."""
    SHARED = "shared"
    DEDICATED = "dedicated"
    CHOICES = [(SHARED, "Shared", "green"), (DEDICATED, "Dedicated", "orange")]


class HAStrategyChoices(ChoiceSet):
    """Data-sync strategy the reconciler applies to a service *type* when one of its instances is
    an HA mirror. Ingress (HAProxy backup) registration is the separate ``ingress_haproxy_backup``
    boolean, not a strategy value."""
    CONTENT_RSYNC = "content_rsync"
    MARIADB_MASTER_MASTER = "mariadb_master_master"
    NONE = "none"
    CHOICES = [
        (CONTENT_RSYNC, "Content rsync", "blue"),
        (MARIADB_MASTER_MASTER, "MariaDB master-master", "purple"),
        (NONE, "None", "gray"),
    ]


class DistroChoices(ChoiceSet):
    """Harness test distro the per-(catalog, distro) test state is keyed by."""
    DEBIAN = "debian"
    ALPINE = "alpine"
    REDHAT = "redhat"
    CHOICES = [(DEBIAN, "Debian", "red"), (ALPINE, "Alpine", "blue"), (REDHAT, "RedHat", "orange")]


class DatabaseTypeChoices(ChoiceSet):
    """Backing database a service type requires (from about.json ``verification.database_type``)."""
    POSTGRESQL = "postgresql"
    MARIADB = "mariadb"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    CHOICES = [
        (POSTGRESQL, "PostgreSQL"), (MARIADB, "MariaDB"), (MYSQL, "MySQL"), (SQLITE, "SQLite"),
    ]


class ExtensionKindChoices(ChoiceSet):
    """Kind of installable extension in a service's plugin/app inventory: a ``plugin`` (e.g. a
    WordPress/Nextcloud plugin), a ``theme``, an ``app`` (a sub-application), or a ``module``."""
    PLUGIN = "plugin"
    THEME = "theme"
    APP = "app"
    MODULE = "module"
    CHOICES = [
        (PLUGIN, "Plugin", "blue"),
        (THEME, "Theme", "purple"),
        (APP, "App", "green"),
        (MODULE, "Module", "cyan"),
    ]


class IntegrationParamValueTypeChoices(ChoiceSet):
    """Rendered typed value. ``list`` is newline-delimited (order preserved); ``map`` is a flat
    newline-delimited ``key=value`` set (bounded — not a nested/generic blob, so it stays clear of
    DESIGN.md §6's data-blob prohibition; the same shape the Go providers already justify as an
    escape hatch, e.g. ``postgres_config.extra_params``). Secrets are OpenBao path references,
    never secret values (enforced independently of ``value_type`` by the ``secret`` boolean on the
    catalog-param row — see ``validate_integration_param_value``). ``SECRET`` is canonical (100% of
    real tofu-services manifest usage — 187/187 ``secret``-kind params, 0 ``secret_ref``); ``SECRET_REF``
    is kept as a compatibility alias so any already-seeded row on the old spelling stays valid — it
    costs nothing and both resolve identically in the validator, so there is no drift to reconcile."""
    STRING = "string"
    INT = "int"
    BOOL = "bool"
    URL = "url"
    LIST = "list"
    MAP = "map"
    FLOAT = "float"
    SECRET = "secret"
    SECRET_REF = "secret_ref"
    CHOICES = [
        (STRING, "String", "gray"),
        (INT, "Integer", "blue"),
        (BOOL, "Boolean", "purple"),
        (URL, "URL", "cyan"),
        (LIST, "List", "green"),
        (MAP, "Map", "teal"),
        (FLOAT, "Float", "orange"),
        (SECRET, "Secret", "red"),
        (SECRET_REF, "Secret ref", "red"),
    ]


class SecretKindChoices(ChoiceSet):
    """Category of secret a :class:`RotationPolicy` rotates — the vocabulary the atomic
    ``rotate_*.yml`` host role dispatches on. Deliberately enumerated (not free text) so a
    rotation policy's kind is queryable/filterable like every other categorical attribute in
    this plugin; extend the set the same way ``IntegrationParamValueTypeChoices`` grows."""
    ADMIN_PASSWORD = "admin_password"
    API_TOKEN = "api_token"
    SIGNING_KEY = "signing_key"
    OIDC_CLIENT_SECRET = "oidc_client_secret"
    DKIM_KEY = "dkim_key"
    ENCRYPTION_KEY = "encryption_key"
    TLS_KEYPAIR = "tls_keypair"
    DB_SERVICE_ACCOUNT = "db_service_account"
    SEAL_KEY = "seal_key"
    APPROLE_SECRET_ID = "approle_secret_id"
    CHOICES = [
        (ADMIN_PASSWORD, "Admin password", "red"),
        (API_TOKEN, "API token", "blue"),
        (SIGNING_KEY, "Signing key", "purple"),
        (OIDC_CLIENT_SECRET, "OIDC client secret", "orange"),
        (DKIM_KEY, "DKIM key", "cyan"),
        (ENCRYPTION_KEY, "Encryption key", "indigo"),
        (TLS_KEYPAIR, "TLS keypair", "green"),
        (DB_SERVICE_ACCOUNT, "DB service account", "teal"),
        (SEAL_KEY, "Seal key", "yellow"),
        (APPROLE_SECRET_ID, "AppRole secret id", "gray"),
    ]
