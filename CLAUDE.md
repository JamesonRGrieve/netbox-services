# netbox-services — Agent Operating Guide

Adapted from the sibling `../netbox-system-services` / `../netbox-guests` plugins (same
engineering + test discipline), re-targeted to the **application / service layer**.

`netbox-services` is an **AGPL-3.0** NetBox 4.6 plugin: the **native source of truth for
application install-data + service integrations**. NetBox is the catalog SoT and `about.json`
is generated *from* it; the plugin models deployed app **instances**, their instance-to-instance
**integration edges** (with cardinality), and **HA mirror** pairings — the data the renamed
`tofu-services` provider reads and the Semaphore HA reconciler acts on. See **DESIGN.md** for the
full decision record (§0), data model, critical path, and risks.

**Secret policy (load-bearing):** secret *values* never live here. `InstanceOpenBaoPath.path`
keys an OpenBao location; `CatalogCredential.deploy_var` names the ansible var the generated
value is passed as. NetBox holds the structure; OpenBao holds the secret.

**No config_context, no CustomField data-blob.** Every attribute is a real typed column or a
child row — the `config_context` / JSON-blob approach the lab retires is forbidden (DESIGN §3).
The plugin owns its own models, so nativeness here means flat typed fields + child models for
repeating records (credentials, tokens, ports, openbao paths, test results), never a JSON blob.

---

## Key Directives / Rules

### DO, ALWAYS:
- If functionality won't work without a parameter, make it a **required positional** parameter.
- Any time you modify a source file, ensure its accompanying test under `netbox_services/tests/`
  contains **comprehensive tests for the change WITHOUT MOCKS**, so `manage.py test
  netbox_services` discovers them, and update any `.md` in the same directory.
- Write concise code (avoid obvious comments; one-liners where possible).
- **SPDX header on every source file**: `# SPDX-License-Identifier: AGPL-3.0-or-later`.

### DO NOT, EVER:
- Store a secret value in a model field. Only OpenBao path/var references.
- Re-introduce a `config_context` blob or a CustomField/JSONField used as a data-blob.
- Use frame-local / thread-local state instead of parameters.
- Skip a failing test; keep a broken path as a fallback; or re-implement a function in a second
  place to bypass the original.
- **Mock the database, the ORM, the NetBox API test client, or any integration path.** Tests run
  against a **real test database**; build real `ServiceCatalog` / `ServiceInstance` / core
  `dcim.Device` / `virtualization.VirtualMachine` / `ipam.Service` rows.

### Python / Django Guidelines:
- Import children of `datetime`: `from datetime import date` — never `import datetime`.
- Package-relative imports inside `netbox_services` (`from .models import ServiceInstance`); core
  uses the real path (`from ipam.models import Service`).
- Models inherit `netbox.models.NetBoxModel` (custom fields, tags, journaling, GraphQL — free).

---

## Architecture (NetBox 4.6 plugin)

| File | Responsibility |
|------|----------------|
| `__init__.py` | `PluginConfig` — name `netbox_services`, `base_url='services'`, min/max 4.6; `ready()` wires `signals` |
| `choices.py` | `ChoiceSet`s: instance status, provider scope, HA strategy, distro, database type (port protocol reuses core `ipam.choices`) |
| `models.py` | the 11 models (see below) + `validate_integration_cardinality` |
| `signals.py` | `pre_save` backstop calling `validate_integration_cardinality` (catches ORM/seeder writes that bypass `clean()`) |
| `migrations/0001_initial.py` | hand-authored (NetBox disables makemigrations in prod); verify with `makemigrations --check --dry-run` |
| `api/serializers.py`, `api/views.py`, `api/urls.py` | REST (`NetBoxModelViewSet`) — the contract the provider + seeder read |
| `filtersets.py` | `NetBoxModelFilterSet` per model |
| `tables.py`, `forms.py`, `navigation.py`, `views.py`, `urls.py` | UI (generic NetBox views) |
| `graphql/__init__.py` | placeholder (auto GraphQL via `NetBoxModel`) |

### Model — catalog + instance SoT
**Catalog layer** (`about.json` is generated from it):
- **ServiceCatalog** (the type): identity + resources (flat `install_*`/`runtime_*`/`disk`) +
  lifecycle playbooks + `verification` (health_endpoint, health_status_codes[], requires_database,
  database_type, requires_cache) + `ha_strategy` + `ingress_haproxy_backup`.
- **CatalogCredential** (FK): `cred_id`, `length`, `deploy_var` (credentials[]).
- **CatalogToken** (FK): `name`, `output_var` (provides_tokens).
- **CatalogSecondaryPort** (FK): `port`, `protocol`, `name` (verification.secondary_ports[]).
- **IntegrationCatalog** (FK): `type`, `requires_service`, `requires_tokens[]`, `playbook`,
  `description`, `provider_scope` (shared|dedicated), `consumer_max` (cardinality source).
- **CatalogTestState** (FK): `(catalog, distro)` stages (install/init/customize/unlock) + telemetry
  — the home of about.json `state{}`, written back by the harness (a Semaphore job).
  - **CatalogTestIntegration** (FK test_state): per-provider `integrate` result.

**Instance layer** (what the provider reads):
- **ServiceInstance**: FK catalog; `parent` GFK → `virtualization.virtualmachine | dcim.device`
  (limited via `parent_object_type.limit_choices_to`); `hostname`; `status`; actual resources;
  `listeners` M2M → `ipam.Service` (ports live in IPAM — no port column here).
- **InstanceOpenBaoPath** (FK): `key`, `path` (credential/token references → OpenBao).
- **Integration** (edge): `consumer`/`provider` FK → ServiceInstance, `type`, `requires_tokens[]`,
  `description`; `unique_together(consumer, type, provider)`; cardinality via
  `validate_integration_cardinality` (clean() + pre_save signal). `consumer_max` is a count check,
  so validation-only (cannot be a DB constraint) and can race under concurrent writes.
- **HAMirror** (edge): `mirror`/`primary` FK → ServiceInstance; `unique(mirror, primary)`; both
  must be the same catalog type; the reconciler reads `mirror.catalog.ha_strategy`.

---

## Testing (NO MOCKS — real DB, NetBox test framework)

- Tests live in `netbox_services/tests/` (`test_models.py`, `test_api.py`, `test_filtersets.py`).
  Use `utilities.testing` base classes; build real catalog/instance rows + core
  device/VM/ipam.Service via a `tests/utils.py` helper.
- **Run**: `python /opt/netbox/app/netbox/manage.py test netbox_services --keepdb -v2`.
- **Verification owed (cannot run offline — no NetBox env in the build host):**
  `makemigrations netbox_services --check --dry-run` on an ephemeral NetBox, and a full test run.
  Re-confirm against the pinned NetBox 4.6: the `ServiceInstance.parent` GFK field names +
  `limit_choices_to` Q serialization, and the `ipam.Service` M2M target.

---

## Licensing
- **AGPL-3.0-or-later** (workspace production-IaC standard). SPDX header in every file.
