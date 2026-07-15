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
    """Rendered typed value. Lists and flat string maps use newline-delimited storage; secrets
    are OpenBao path references, never secret values. ``secret_ref`` remains as a compatibility
    spelling for existing integration rows while manifests use canonical ``secret``."""
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
