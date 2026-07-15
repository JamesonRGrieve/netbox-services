# netbox-services

NetBox as the source of truth for **application install-data + service integrations**,
consumed by the **`tofu-services`** provider (renamed from `tofu-proxmox-services`) that
deploys/wires services through Semaphore — paired with a `netbox-guests` plugin (the
PVE-guest intent layer that supersedes `netbox-proxbox`).

**Status:** design resolved 2026-06-17; plugin implemented (untested — needs a NetBox env).
See **[DESIGN.md](DESIGN.md)** (decisions of record, data model, critical path, risks) and
**[CLAUDE.md](CLAUDE.md)** (architecture + test discipline).

## Layout

```
netbox_services/
  __init__.py        PluginConfig (base_url 'services'); ready() wires signals
  choices.py         instance status, provider scope, HA strategy, typed config values
  models.py          typed catalog, instance, integration, host-role, and rotation models
  signals.py         pre_save cardinality backstop (catches ORM/seeder writes)
  migrations/0001    hand-authored CreateModel for all models
  api/               REST (NetBoxModelViewSet) — /api/plugins/services/
  filtersets.py forms.py tables.py views.py urls.py navigation.py
  graphql/           placeholder (auto GraphQL via NetBoxModel)
  tests/             real-DB tests (models, api, filtersets) + utils
```

**Catalog layer** (the upstream `about.json` is generated *from*): `ServiceCatalog` + child rows
(`CatalogCredential`, `CatalogToken`, `CatalogSecondaryPort`, `IntegrationCatalog`,
`CatalogTestState`/`CatalogTestIntegration`). **Instance layer** (what the provider reads):
`ServiceInstance` (parent GFK → VM | Device; ports via M2M → `ipam.Service`), `InstanceOpenBaoPath`,
the `Integration` edge (with cardinality), `HAMirror`, and `RotationPolicy` (cadence/on-demand
trigger, atomic host role, and consumer fan-out). Config values support typed string/int/bool/url,
newline lists/maps, finite floats, and OpenBao secret references. No `config_context`, no JSON
blobs; secret *values* are never stored.

## Develop / test

```
python /opt/netbox/app/netbox/manage.py test netbox_services --keepdb -v2
python /opt/netbox/app/netbox/manage.py makemigrations netbox_services --check --dry-run
```

Both require a NetBox 4.6 environment. **Verification owed** (cannot run offline): the migration
check, the full test run, and the version-sensitive surfaces — the `ServiceInstance` parent GFK
(`parent_object_type`/`_id` + `limit_choices_to`), the `ipam.Service` M2M, and the GFK/M2M API
serializer field helpers (`ContentTypeField`, `SerializedPKRelatedField`).
