# netbox-services — Design

**Status:** design resolved 2026-06-17 (operator decisions); not yet implemented.
Decisions of record in §0.

NetBox as the **single source of truth for application install-data + service
integrations**, consumed by a **`tofu-services` provider** (renamed from
`tofu-proxmox-services`) that deploys and wires services **through Semaphore**. This
replaces the scattered `about.json` + harness install path with **NetBox-intent →
Semaphore-apply**, matching the lab's "NetBox = SoT, sanctioned pipeline = apply engine"
philosophy and mirroring the NetBox⟷ERPNext upstream→downstream pattern
(`ansible/CLAUDE.md` EOS.4).

The direction is **inverted from today**: NetBox becomes the catalog SoT and
`about.json` becomes a **generated, committed projection of NetBox** — one list, one
artifact. Pairs with [`netbox-guests`](../netbox-guests/DESIGN.md) (the guest layer whose
VM/Device rows `ServiceInstance.parent` targets).

---

## 0. Decisions of record (2026-06-17)

| # | Item | Decision |
|---|------|----------|
| 1 | Catalog SoT direction | **Inverted.** NetBox is the catalog SoT; `about.json` is a **generated + committed** projection (commit-hook / CI). |
| 2 | ServiceCatalog | Native plugin model, **full** payload — incl. `verification{}`, `customize_playbook`, `unlock_playbook`, `ha_strategy`, `provider_scope`, `consumer_max`. |
| 3 | IntegrationCatalog | **Child model** of ServiceCatalog; seeder uses **reconcile-delete** (prunes removed entries). |
| 4 | bundles.json | **Out of scope** — stays a separate file; the generator covers `about.json` only. |
| 5 | Non-app system-services | **Out of scope** (no upstream; owned by `netbox-system-services`). |
| 6 | ServiceInstance | Native plugin model with real typed fields — **no `config_context`, no CustomField data-blob.** `parent` GFK → guest VM \| raw-OS `dcim.Device`. |
| 7 | Ports / `ipam.Service` | Plugin-side **`ManyToManyField → ipam.Service`** (join table owned by the plugin → no CF, no core fork). `ipam.Service.parent` stays = host. No `port` field on ServiceInstance. |
| 8 | `parent` GFK / guests coupling | **No `Container` content-type** (netbox-guests models LXC+KVM on core `virtualization.virtual-machine`). `parent` targets core `virtualmachine`\|`device`, both of which **exist today** → ServiceInstance is **not** migration-blocked. It is **adoption-ordered**: guests reclassification lands first so the GFK target rows are stable (netbox-guests §5/§6). |
| 9 | Integration edge | `unique_together(consumer,type,provider)`; enforcement = **serializer/form + `pre_save` signal**; caps **shipped**, default **permissive** (`consumer_max` is validation-only). |
| 10 | HA edges | **Separate model** (`HAMirror`), not overloaded onto `Integration`. |
| 11 | HA wiring execution | **Declarative in NetBox + Semaphore reconciler** — never Tofu resources, so the primary↔mirror cycle is a non-issue. |
| 12 | §7 HA timing | **In v1, sequenced last** (netbox-guests §6 step 6). |
| 13 | Harness test state | `about.json` `state{}` / telemetry → **`CatalogTestState`** child of ServiceCatalog (keyed service×distro×stage); the harness becomes a Semaphore job reading catalog / writing results. |
| 14 | Provider rename | **Now**, pre-adoption (zero state). `tofu-proxmox-services → tofu-services`. |
| 15 | Provider resources | **`services_instance` + `services_integration`** (surface mirrors the NetBox model). |
| 16 | Execution engine | **Provider triggers Semaphore templates.** Tofu owns the graph + state/drift; Semaphore is the executor; the local `internal/ansible.Runner` → a Semaphore client. Services-apply runs in a **separate Semaphore queue** (avoids task-pool starvation). |
| 17 | edge-router adoption | Runs **parallel**; assumed done before any prod apply. |
| 18 | netbox-proxbox | Retire **after guests adoption is 0-diff** (netbox-guests §6 step 3). |

---

## 1. Why

- `about.json` (`ansible/playbooks/applications/<app>/about.json`) is **today's** service
  metadata SoT — resources, `tier`, ports, `credentials[]`, `provides_tokens`,
  `playbook`, `integrations[]`, `verification{}`, per-distro `state{}`. Consumed by the
  harness + `create_ct`. It is **per-app catalog data + test state**, **not**
  instance/deployment state, and it is **not** in NetBox.
- The integration model (`ansible/CLAUDE.md` §8.7) is **provider/consumer**:
  `prepare_integration_<app>.yml` (provider, shared) + `integrate_<service>.yml`
  (one per **consumer-provider pair**). `about.json` `integrations[]` is
  **instance-agnostic** — each entry names a service **type**, not which instance.
- NetBox today has core `ipam.services` (an L4 listener record — name/proto/ports +
  `parent` GFK to host), `netbox-inventory`, and the in-house `netbox-*` plugins.
  **None model application install-data or instance-level integration edges.**
  `netbox-proxbox` only syncs Proxmox→NetBox (to be retired).

**Gap:** nothing models the **catalog**, deployed app **instances**, their
**instance-to-instance integration edges**, **cardinality**, or **HA intent** as NetBox
data. That is this plugin — and once it exists, NetBox, not `about.json`, is the catalog
SoT.

---

## 2. Cardinality model (from `ansible/CLAUDE.md` §8.7.3)

- "**One `prepare_integration_<app>.yml` per provider**" → a provider instance is
  **shared**: many consumers bind to one provider instance ⇒ consumer→provider is
  **N:1** for singletons (OpenBao, Authentik, Stalwart, NetBox, Alloy…).
- "**One `integrate_<service>.yml` per consumer-provider pair**" → bindings are
  **pairwise**; a consumer may bind to several provider *types*.
- Realized cardinality is the **edge multiplicity** in NetBox: **N:1** shared provider
  (default), **1:1** dedicated provider, **N:M** consumer bound to multiple instances of
  one provider type.
- The catalog integration carries the **allowed** cardinality (`provider_scope =
  shared|dedicated`, `consumer_max = <int>`). **Caps ship in v1 but default permissive**
  (`shared`, unbounded); set real limits per-integration in NetBox as they emerge.
- **Enforcement** (decision #9): `unique_together(consumer, type, provider)` (DB dup
  guard) + **serializer/form validation** (UX) + a **`pre_save` signal** (the only hook
  that also catches ORM/seeder/migration writes). `consumer_max` is a *count* check — it
  cannot be a DB constraint, so it is **validation-only** and can race under concurrent
  writes. Documented on the model; acceptable for a human/seeder-edited SoT.

---

## 3. Data model (NetBox plugin `netbox_services`)

All models are native `NetBoxModel`s (custom fields, tags, journaling, GraphQL for free),
mirroring the `netbox-system-services` layout. **No `config_context`; no CustomField used
as a data-blob** — every attribute is a real field/relation.

### ServiceCatalog  *(template — the catalog SoT; `about.json` is generated from it)*
`name, display_name, description, tags, repo, docs, license, default_port,
resources{install,runtime}, tier, credentials[] (id/length/deploy_var),
provides_tokens{}, requires_gpu, playbook, init_playbook, customize_playbook,
unlock_playbook, verification{health_endpoint, health_status_codes[], secondary_ports[],
requires_database, database_type, requires_cache}, ha_strategy`.
Full mirror of the `about.json` payload (decision #2) — anything a consumer reads is here.

### IntegrationCatalog  *(child of ServiceCatalog — the allowed integration types)*
`FK→ServiceCatalog, type, requires_service, requires_tokens[], playbook, description,
provider_scope (shared|dedicated), consumer_max`. Seeded with **reconcile-delete**
(decision #3): removed `about.json` entries are pruned, not just upserted.

### CatalogTestState  *(child of ServiceCatalog — harness test matrix, decision #13)*
`FK→ServiceCatalog, distro, install, init, customize, unlock, integrate{}, telemetry
{peak_memory_mb, peak_cpu_load, install_duration_s}`. Keyed **(catalog, distro, stage)** —
the home of today's `about.json` `state{}`; the harness (now a Semaphore job) **writes**
it back. Distinct grain from a deployed instance's runtime status.

### ServiceInstance  *(deployed — the row the provider reads)*
`FK→ServiceCatalog`, **`parent` GFK → virtualization.virtualmachine | dcim.device**
(decision #6/#8 — a guest VM, or a raw-OS device; both are core content-types, no
`Container` type). An install target is **required** (no `ServiceInstance` without one).
`hostname`, **`listeners` M2M → ipam.Service** (ports live in IPAM; no `port` field —
decision #7), `resources` (actual), `openbao_paths{}` (credential + provides_tokens
**references** — values stay in OpenBao), `status` (staged/active/…),
`high_availability_of` (nullable self-FK → primary, N:1).

### Integration  *(edge — the instance binding the catalog lacks)*
`FK consumer→ServiceInstance, FK provider→ServiceInstance, type (= IntegrationCatalog
type), requires_tokens, description`. `unique_together(consumer, type, provider)`;
cardinality enforced per §2.

### HAMirror  *(edge — HA pairing, separate from Integration, decision #10)*
`FK mirror→ServiceInstance, FK primary→ServiceInstance, ha_strategy (resolved from the
catalog)`. Same-type peer edges (WP→WP, MariaDB→MariaDB) have **no** IntegrationCatalog
entry, so they live here rather than overloading `Integration.type`.

---

## 3a. Guest layer — `netbox-guests` (replaces `netbox-proxbox`)

§3 is the **application** layer; it sits on a **guest** (a VM/CT) or a raw-OS device.
`netbox-guests` is its own repo — see [`../netbox-guests/DESIGN.md`](../netbox-guests/DESIGN.md).
Shape (operator decision 2026-06-17): **native VM + custom fields, no core fork.** Both
LXC containers and KVM VMs are modeled on core `virtualization.virtual-machine`,
distinguished by a `guest_type` custom field; net intent is native (`VMInterface` + IPAM +
802.1Q VLAN + MAC, with `bridge`/`gw` as per-iface CFs); PVE scalars (`vmid`, `node`,
`storage`, `cloud_init`, …) are typed CFs; `mounts[]` is a thin `GuestMount` model. This
is "native" as real typed queryable objects — **not** the proxbox CustomField-blob /
`config_context` approach being retired — and the explicit per-iface IP/gw/vmid is what
de-hardcodes the `hv/pve` module (the routable-fleet blocker).

Because guests are core `virtualmachine` rows (not a new content-type), **ServiceInstance
is not migration-blocked**; it is **adoption-ordered** — guests reclassification lands
first so the `parent` GFK target rows are stable (netbox-guests §5/§6).

Two-layer SoT, both NetBox-anchored: `netbox-guests` (box → `proxmox` provider) ←
`netbox-services` (`ServiceInstance.parent` → the guest → `tofu-services` provider).
**Retire `netbox-proxbox` once guests adoption is 0-diff** (decision #18).

---

## 4. Components / what needs doing

1. **`netbox_services` plugin** (this repo): models §3 + REST API + GraphQL + admin + UI,
   following the in-house `netbox-*` conventions (mirror `netbox-system-services`).
   Hand-authored migrations (NetBox disables `makemigrations` in prod); tests **no mocks**
   against a real test DB. Cardinality validation per §2.
2. **Catalog bootstrap + reverse generator** (decision #1):
   - **One-time seeder** (idempotent, pattern: `prod-lab/scripts/seed_lab_features.py`):
     scans every `ansible/playbooks/applications/*/about.json`; upserts ServiceCatalog +
     IntegrationCatalog (reconcile-delete). Run **once** to bootstrap NetBox.
   - **Reverse generator** `NetBox → about.json`, wired to a **commit-hook / CI** job.
     **Must be byte-deterministic** (stable key ordering) or every NetBox edit churns the
     file. CI drift-guard = "regenerated == committed" (a codegen/lockfile-style check).
   - **Harness becomes a Semaphore job**: reads the catalog from NetBox and **writes
     `CatalogTestState`** back (its per-distro results + telemetry).
   - `bundles.json` and non-app system-services are **out of scope** (decisions #4, #5).
3. **`tofu-services` provider** (renamed from `tofu-proxmox-services`, decisions #14–16):
   reads `ServiceInstance` + `Integration` from NetBox via `services_instance` /
   `services_integration`; Tofu's graph orders **providers→consumers** via token refs;
   each install/init/customize/integrate is run by **triggering the existing Semaphore
   ansible templates** (the local `internal/ansible.Runner` becomes a Semaphore client).
   The services-apply runs in a **separate Semaphore queue** so a `tofu apply` task that
   blocks on child ansible tasks can't starve the pool. Plan-first / 0-diff per
   `ai-prompts/tofu.md`; secrets ephemeral from OpenBao.
4. **HA reconciler** (decision #11): a separate idempotent Semaphore job reads the
   `HAMirror` edges + `ha_strategy` and materializes the mechanisms (§7). HA is **never**
   modeled as Tofu resources, so the primary↔mirror cycle never has to be acyclic.
5. **Adoption**: import-first/0-diff — guests reclassify the CTs (netbox-guests), then
   services import `ServiceInstance`s against them, then the provider's first plan is
   0-diff.

---

## 5. SoT direction & boundaries

- **NetBox is the catalog + instance + edge + HA SoT** (decision #1). `about.json` is a
  **generated, committed** downstream artifact; the harness reads NetBox and writes test
  state back. Never hand-maintain two lists (EOS.4) — one list (NetBox), one projection.
- **Secrets → OpenBao** (NetBox holds only paths/refs); **runtime/telemetry → monitoring**
  + `CatalogTestState`; **config/intent → NetBox** (per `prod-lab/docs/netbox-modeling.md`).
  The plugin stores credential *references*, never values — consistent with
  `netbox-system-services` ("logical OpenBao key, never the secret").
- Distinct from the **asset** register (`netbox-inventory` + ERPNext, EOS.4): this is the
  **service/install** layer. An owned box is an asset; a *service running on it* is a
  `ServiceInstance`.
- **Ports stay in `ipam.Service`** (the native L4 object), linked from the plugin via
  M2M — not duplicated onto ServiceInstance.

---

## 6. Open questions — resolved

The original open questions are resolved in §0:

- Plugin vs. extend `ipam.services` + custom fields → **plugin** (the relational edges +
  cardinality a CF can't do; a CF data-blob is the `config_context`-style approach the lab
  retires). Note the nuance from netbox-guests: individual *typed* CFs to extend a *core*
  model (avoiding a fork) are acceptable; a JSON/data-blob CF is not.
- Cardinality enforcement → **serializer/form + `pre_save` signal** (#9).
- How the provider triggers deploys → **Semaphore templates** (#16).
- Bundles / non-app system-services → **out of scope** (#4, #5).
- EOS.4 cross-links → asset vs service-instance stay distinct layers (§5); cross-link by
  host where useful.

---

## 7. High-availability mirrors (`high_availability_of`) — in v1, sequenced last

Declarative failover (folds in a house mirror of a primary CT): mark a service instance as
the **HA mirror** of a primary; the reconciler enforces the sync + failover wiring.

- **`ServiceInstance.high_availability_of`** — nullable self-FK (mirror → primary),
  **N:1**. **Per-service `HAMirror` edges**: the mirror CT's WordPress instance → the
  primary's WordPress, AND its MariaDB → the primary's MariaDB (co-located: two edges,
  two mechanisms).
- **`ServiceCatalog.ha_strategy`** — per service *type*:
  - `wordpress` → **`content_rsync`** (daily `wp-content/uploads` primary→mirror over WG)
    + **`ingress_haproxy_backup`** (register the mirror's edge as a `backup` server in the
    primary's HAProxy ingress pool).
  - `mariadb` → **`mariadb_master_master`** (circular repl over WG; `server_id`, `log_bin`,
    `binlog_format=ROW`, repl user, `CHANGE MASTER`, `auto_increment_offset/increment`).
    With HAProxy `backup` serving one side this is **active-passive with a warm standby** —
    document as such (no dual-write; last-write-loss possible on mid-checkout failover).
  - `valkey` → **`none`** (ephemeral cache; WC sessions live in the MariaDB
    `wp_woocommerce_sessions` table, covered by DB repl).
- **Reconciler** — Semaphore-triggered, idempotent: per mirror, reads `ha_strategy` +
  primary → materializes the mechanism(s). LB/WG objects + guest-side wiring are in
  [`../netbox-guests/DESIGN.md`](../netbox-guests/DESIGN.md) §7. Modeled **in NetBox**,
  executed out-of-band — **not** in the provider's resource graph (decision #11).
- **Failover semantics** — mirror is **hot**; cutover is automatic at the **HAProxy layer**
  (auto-revert on recovery). No promotion engine. **Boundary:** fires only if the primary's
  edge router survives; total-edge-loss needs a separate Cloudflare/DNS tier (optional).

**Prerequisites (v1, sequenced last per netbox-guests §6 step 6):**
1. HAProxy `backup` via the in-house **`netbox-load-balancing-acl`** plugin (`LBMemberHA`:
   FK→base Member/Pool, `backup` bool) → joined in `net/routers` → emitted as the `backup`
   keyword.
2. A `netbox-wireguard` reader in `net/routers` (allowed-ips from the plugin; keys in
   OpenBao).
3. ansible: WordPress content-rsync, MariaDB master-master, initial primary→mirror seed.
4. The reconciler + its Semaphore template.
5. The **edge-router `net/routers`** import-first adoption — runs **parallel**; assumed
   done before any prod apply (decision #17).
6. A routable repl `/32` range + its `wg2` AllowedIPs.

---

## 8. Critical path

Nests under the netbox-guests §6 build sequence (NetBox→latest · Tofu de-hardcode · guests
plugin + 0-diff adoption + retire proxbox · flip module reader to native CFs):

- **Phase A — parallel foundations:** netbox-load-balancing-acl (`LBMemberHA`) ·
  netbox-wireguard reader in `net/routers` · edge-router `net/routers` adoption → apply.
- **Phase B — plugin:** ServiceCatalog + IntegrationCatalog + CatalogTestState ·
  ServiceInstance (parent → core VM/Device) · Integration · HAMirror · REST/GraphQL/admin/
  UI · hand-authored migration · no-mock tests. (Model not blocked on guests; *adoption*
  is.)
- **Phase C — inversion:** one-time bootstrap seeder · reverse generator + drift-guard ·
  harness → Semaphore job.
- **Phase D — provider:** rename now · `services_instance` / `services_integration` ·
  Semaphore-client execution in a separate queue.
- **Phase E — adoption:** import-first 0-diff (guests reclassified → services imported →
  provider plan 0-diff).
- **Phase F — HA (last):** reconciler materializing the three `ha_strategy` mechanisms
  (gated on Phase A + the guest multi-NIC work).

---

## 9. Residual risks

1. **netbox-guests gates services *adoption*** (not the model): guest rows must be
   reclassified + stable before `ServiceInstance`s point at them. Less severe than a
   content-type block, but still an ordering dependency.
2. **HA-in-v1 makes v1 a multi-repo program**; its long pole runs through the
   **an edge-router apply on a PROTECTED production target** (every touch needs explicit
   operator permission per the configured access rules).
3. **The reverse generator must be byte-deterministic** or every NetBox edit churns
   `about.json` and the drift-guard cries wolf.
4. **Harness write-back is a new prod-NetBox write path** from CI/Semaphore — scope its
   token so `CatalogTestState` writes can't mutate intent fields.
5. **Semaphore task-pool starvation** from the apply→child-template recursion — the
   separate-queue mitigation must be designed in, not bolted on.
6. **`consumer_max` races** (validation-only, no DB constraint) — documented, accepted.
7. **master-master MariaDB is really active-passive** (HAProxy `backup` serves one side).
8. **The plugin-side M2M to `ipam.Service`** technically permits one port shared by two
   instances — enforce "one listener → one instance" in `clean()` if that's the intent.

---

## 10. References

- `ansible/CLAUDE.md` — §8.7 integration model (§8.7.3 cardinality), §12.1 `about.json`
  schema, §12.2 `bundles.json`, EOS.4 NetBox⟷ERPNext SoT direction.
- `prod-lab/docs/netbox-modeling.md` (SoT boundary), `netbox-tofu-bao.md`
  (NetBox→Tofu→OpenBao wiring).
- `ai-prompts/tofu.md` (provider/module standards, ephemeral secrets, stable-key
  `for_each`).
- In-house plugin reference: `netbox-system-services` (layout to mirror).
- Seeder reference: `prod-lab/scripts/seed_lab_features.py`.
- Sibling: [`netbox-guests`](../netbox-guests/DESIGN.md) (guest layer).
