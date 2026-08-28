# Service Desk Realism — Phase 1: Architecture & Inventory

Status: **investigation/design only.** No infrastructure, no VMs, no new engines.
Baseline commit: `3d0bba1` (production). Author: Claude (session 2026-08-28).

The headline finding: **most of the platform the realism project needs already
exists.** Nexus already has a versioned scenario/attempt/event/grade contract, an
append-only hash-chained trusted-evidence ledger, deterministic server-side
*process* grading, a Proxmox clone/start/ip/destroy service, a Guacamole
connection/scoped-access service, and a VM lifecycle with TTL expiry + background
teardown. The gaps are: (1) those lab services are wired to **Guided Labs**, not
Service Desk; (2) they are **dormant in production** (no `PROXMOX_*` / `GUACAMOLE_*`
env); (3) there is **no real-machine evidence collection** (no SSH/WinRM/guest-agent
exec); (4) there is **no AI requester chat** (AI service exists, chat is scripted
fixtures); (5) the ticket `definition_json` has **no `lab` block**.

---

## A. Current Service Desk map (with classification)

Legend: **KEEP** (use as-is) · **EXTEND** (add to it) · **MERGE** (fold another
thing into it) · **REPLACE** (eventually swap out) · **REMOVE LATER** (delete once
successor lands).

| # | Component | Where | Classification | Notes |
|---|---|---|---|---|
| 1 | Student SD screens | `service-desk-app/apps/web/app/(app)/{tickets,tools,analytics,achievements}` (Next.js), proxied at `/service-desk` | **KEEP / EXTEND** | This is the realistic ticket UI. Canonical simulator front end. |
| 2 | Admin/mentor SD screens | `apps/web/app/admin/{scenarios,test-students}` + Nexus `frontend/src/pages/admin/AdminServiceDeskReviewPage.jsx` | **KEEP / EXTEND** | Scenario authoring + attempt review + mentor feedback already persisted server-side. |
| 3 | Ticket/scenario models | `backend/app/models/service_desk.py` — `ServiceDeskScenario`, `ServiceDeskScenarioVersion` (immutable, hashed `definition_json`), `ServiceDeskKnowledgeArticle` | **KEEP / EXTEND** | Versioned + publish-locked. Extend `definition_json` with a `lab` block (see C). |
| 4 | Assignment system | `ServiceDeskAssignment` (student×scenario×mode, `is_required`, `due_at`, `maximum_attempts`) + `service_desk_progression.py` packs (`required_week`, `required_prior_passes`) | **KEEP / EXTEND** | Extend for "unlimited practice" pool assignments (Phase 9). |
| 5 | Attempts / sessions | `ServiceDeskAttempt` — `current_state` (JSON) + `current_state_hash` + `state_version`, `mode` (learning/simulation), `experience_mode` (guided/practice/assessment), `attempt_number`, `admin_reset_*` | **KEEP / EXTEND** | Add `lab_session_id` FK when labs land. Resume already works off `current_state`. |
| 6 | Event tracking | `ServiceDeskAttemptEvent` — **append-only** (SQLAlchemy `before_update`/`before_delete` guards), per-attempt `sequence_number`, `idempotency_key`, `previous_state_hash`→`resulting_state_hash` **hash chain**, `trusted` flag | **KEEP** | Best-in-class. Real-lab evidence becomes new `trusted` event types on the same ledger. Do not rebuild. |
| 7 | Grading | `service_desk_grading.py` (`compute_grade`, deterministic, recomputed from definition+events) + `service_desk_objectives.py` (`process-v3`: investigation→diagnosis→remediation→verification→documentation with temporal ordering; `PROCESS_WEIGHTS`) | **KEEP / EXTEND** | Already evidence-based, not click-based. Extend predicate set for real-lab evidence (see C). |
| 8 | Hints | `definition_json.hints[]` (≥3 progressive, `pointPenalty`); `/attempts/{id}/hints`; `FREE_HINT_COUNT=1`, `HINT_PENALTY_POINTS=5` | **KEEP** | |
| 9 | Snapshots / resume | `ServiceDeskAttempt.current_state` + `/attempts/{id}/snapshot` (`persist_snapshot`, `_validate_resume_snapshot`); client `packages/simulation-engine/{serialize,attempt,progress-read-model}.ts` | **KEEP** | Clean-browser restore already tested (Playwright `service-desk-integration.spec.js`). |
| 10 | Remaining localStorage | `apps/web/components/TicketSessionProvider.tsx` (offline outbox + drafts), `HintDialog.tsx`, `layout.tsx` (theme), `useNexusReturnTarget.ts` / `lib/nexus-return.ts` (return deep-link) | **KEEP (outbox) / EXTEND** | Outbox retry is deliberate. The earlier "6 state domains persist only incidentally" concern (chat/asset/pc_shelf/server_room/deployment/shipping) still applies — fold into `current_state` in Phase 2. |
| 11 | `service-desk-app` architecture | pnpm monorepo: `apps/web` (Next.js UI) · `apps/api` (**empty placeholder** — `apiStatus = 'not-started'`) · `packages/{shared,simulation-engine,ui}` | **KEEP web+packages / REMOVE LATER `apps/api`** | `apps/api` is a stub and must never become a 4th engine. `simulation-engine` = client reducer + client objective mirror; backend stays authoritative. |
| 12 | Nexus backend integrations | `routers/service_desk.py` (1074 ln — student runtime: assignments, attempts, events, **`/actions`** trusted transition, hints, snapshot, complete, progression) · `routers/service_desk_bridge.py` (progress, `admin-check`, `admin-authorize`) · `routers/admin_service_desk.py` (scenario/version CRUD, validate, publish, assign, review, feedback) | **KEEP / EXTEND** | `/attempts/{id}/actions` is the seam where a real `LabProvider.collectEvidence()` feeds `trusted` events. |
| 13 | Auth Nexus↔SD | nginx `auth_request` → Nexus `/auth/me` (student JWT + `student_session` cookie) for `/service-desk/*`; → `/api/service-desk/admin-authorize` for `/service-desk/admin/*`. JWT parity (`JWT_SECRET_KEY`/`JWT_ALGORITHM`) between backend `.env` and the `nexus-service-desk` container env (predeploy-checked). | **KEEP** | Solid. No change needed. |
| 14 | DB tables (SD) | `service_desk_scenarios`, `_scenario_versions`, `_attempts`, `_attempt_events`, `_attempt_grades`, `_assignments`, `_knowledge_articles`, `_audit_logs`, `_beta_enrollments`. Migrations `0032,0034,0035,0036,0040,0042,0043,0047`. | **KEEP / EXTEND** | New tables for labs: `lab_sessions`, `lab_evidence` (Phase 4). Reuse `service_desk_*` for everything ticket-side. |
| 15 | APIs | `/api/service-desk/*` (student) + `/api/service-desk/admin/*` + bridge. All server-authoritative; browser never supplies `success`/`trusted`/`state` on `/actions`. | **KEEP / EXTEND** | Add `/api/service-desk/attempts/{id}/lab/*` (start/access/evidence/reset) in Phase 4. |
| 16 | Container deploy | `nexus-service-desk` container (image `nexus-service-desk:<sha12>`, built from `service-desk-app/docker/web.Dockerfile`), private `nexus-production` Docker net, loopback `:13000`, `--restart unless-stopped`, healthcheck. Rollback pair kept (`nexus-service-desk-predeploy`). | **KEEP** | Predeploy check now validates this container (PR #30), not a host `.next` build. |
| 17 | CLI labs | `frontend/src/features/cli-labs/**` — client-side Cisco IOS + PC-command simulator (`networkSim`, `stpSim`, `macTable`, `trunking`, `etherchannel`, `interfaceCommands`, `pcCommands`, `objectiveTracker`); backend `cli_lab.py` model + `cli_labs.py` router + `cli_lab_seed.py`; tables `cli_lab`, `cli_lab_attempt` (`command_log` JSON) | **KEEP (as its own product) / MERGE selectively** | Great for pure switching/STP theory. For *Service Desk network tickets* prefer a real lab (GNS3) so `ipconfig`/`ping`/`nslookup`/`tracert` produce real output. The client engine can stay as the "simulated" `LabProvider` tier. |
| 18 | VM / Proxmox code | `services/proxmox_service.py` (`clone_template` linked/full, `start_vm`, `get_vm_ip` via guest-agent, `destroy_vm`; VMID pool 200–299) · `models/vm_assignment.py` (`vmid`, `lab_run_id` **unique = 1:1 isolation**, `status`, `ip_address`, **`guac_conn_id`/`guac_username`**, `retry_count`, **`expires_at` indexed**, `destroyed_at`) · `routers/labs.py` (`_queue_assignment`, `_destroy_vm_task`, TTL `LAB_VM_TTL_MINUTES=120`, `/vm-status` self-expires, `/vm-access` scoped Guac URL) · migrations `0028`, `a1b2c3d4e5f6` | **KEEP / EXTEND / MERGE** | This is 70% of `LabProvider(Proxmox)` + lifecycle. **Dormant in prod** (no `PROXMOX_*` env). Generalise from `LabRun` to a provider-agnostic `lab_sessions` table and reuse for Service Desk. Missing: `suspend()`, `reset()`, `collectEvidence()`, `health()`. |
| 19 | SSH / evidence collection | **None.** No `paramiko`/`asyncssh`/`winrm`/guest-exec anywhere in `backend/`. `get_vm_ip` uses guest-agent network-get-interfaces only. | **BUILD NEW** (Phase 5) | Prefer Proxmox `agent/exec` + `agent/exec-status` (VE 8) over opening SSH to student VMs — keeps isolation, no inbound ports. `asyncssh` as the fallback provider for LXC/containers. |
| 20 | AI integration | `services/ai_service.py` — OpenAI-compatible (`AI_BASE_URL`/`AI_MODEL`/`AI_API_KEY`), local detection (`AI_IS_LOCAL`), per-`(user_id,feature)` rate limit (`rate_limiter.py`), `DAILY_AI_BUDGET`, `json_mode`, `extract_json_payload` (dirty-JSON tolerant), usage logged to `ai_usage`. Used by `ticket_generator.py` (requester blurb), `ticket_grader.py`, quiz gen, question explanations. **LIVE in prod.** | **KEEP / EXTEND** | Add a `service_desk_requester_chat` feature: turn-based persona conversation grounded in `definition_json.requester` + hidden root cause, with the same budget/rate-limit/injection-delimiter guards. Do **not** add a second AI client. |

### Legacy ticket engine (context)

`models/ticket.py` (`Ticket`, `TicketSubmission`) — the *old* engine: `root_cause`,
`required_checkpoints`, `scoring_anchors`, `parameters` (per-student randomization
via `ticket_params.resolve_parameters` — `options[student_id % len]`), AI write-up
scoring, before/after screenshot evidence. **Retired** by migration
`0043_retire_legacy_tickets`. Routers `tickets.py` / `admin_tickets.py` still exist.

- **`ticket_params.py` randomization pattern → KEEP (port the idea)** into
  `definition_json.randomization` for Phase 9.
- **`Ticket`/`TicketSubmission` tables + `tickets.py`/`admin_tickets.py` → REMOVE
  LATER** once no data/UI references them (verify first).
- **`ticket_grader.py` (AI write-up rubric) → MERGE** the "communication" sub-score
  idea into the SD `documentation` process category; drop the standalone path.

---

## B. Canonical simulator — CONFIRMED (matches your preference)

The structure you proposed is **already the built architecture**; adopt it as
canonical and do not deviate:

```
Nexus (React + FastAPI)
  └─ student identity, curriculum, weeks, XP ledger, promotion gates, progress

service-desk-app/apps/web (Next.js, container `nexus-service-desk`)
  └─ THE realistic ticket UI + in-browser tool panels + requester chat
     (client simulation-engine = optimistic UX mirror only)

Nexus backend  /api/service-desk/*   ← single source of truth
  └─ assignments · attempts · append-only trusted event ledger · deterministic
     process grading · hints · resume snapshots · progression · mentor feedback

External lab services (NEW, behind one interface)
  └─ real Linux/Windows/network environments per attempt, one student per session
```

`service-desk-app/apps/api` stays a **stub and is deleted** — it is the only thing
that could become a 4th engine. The client `simulation-engine` package is **not** a
second engine: it is a client-side reducer/preview; the backend `/actions`
transition graph + `evaluate_objectives` are authoritative and already enforce
that browser-supplied `success`/`trusted` are ignored.

**One dissent worth noting:** the `cli-labs` client engine and the
`simulation-engine` workstation emulator overlap in intent ("terminal you can
type into"). Keep both for now (they serve different tiers — see the `LabProvider`
`simulated` implementation), but Phase 2 should pick **one** client terminal
component and reuse it for both simulated and real (xterm.js over a WS to the
provider) so students see one consistent terminal.

---

## C. Realistic Ticket Contract (design — not yet implemented)

Extend `ServiceDeskScenarioVersion.definition_json`. Everything below already
exists **except** the `lab` block, the real-evidence predicate types, and
`randomization`. Existing keys (validated in
`service_desk_scenario_validation.py`): `title, slug, category, priority,
difficulty, explanation, pointValue, description{issue,reportedByLine,
businessImpact,troubleshooting[]}, requester{name,department,email,contact,
location}, device{assetTag,deviceName,kind,operatingSystem,state}, sla{dueAt,
target}, initialWorldState{directoryOverlaySeeds,assetOverlaySeeds,
chatMessageSeeds[]}, objectives[]{id,description,predicateType,predicateParams,
required,pointValue}, requiredActions[], forbiddenActions[], hints[]{id,text,
pointPenalty}`.

### Proposed additions

```jsonc
{
  // ...all existing keys...

  "requester": {
    "name": "…", "department": "…", "email": "…", "contact": "…", "location": "…",
    "persona": {                        // NEW — drives AI chat (Phase 3)
      "tone": "flustered|calm|impatient|apologetic",
      "techLiteracy": "low|medium|high",
      "constraints": ["in a meeting in 30 min", "on VPN from home"],
      "willReveal": ["error text on screen", "what they clicked"],
      "willNotReveal": ["password", "that they changed the hosts file"],
      "groundTruthHints": ["laptop worked yesterday", "only this site fails"]
    }
  },

  "rootCause": {                        // NEW — hidden; never sent to student UI
    "summary": "Static DNS 9.9.9.9 set on the NIC; resolves external but not intranet",
    "type": "dns_static_override",
    "injectedBy": "lab.break_script step 2"
  },

  "lab": {                             // NEW — the whole realism hook
    "provider": "simulated|docker|lxc|proxmox_vm|gns3|gns3_proxmox",
    "profile": "win11-domain-joined|ubuntu22-desktop|net-branch-office|…",
    "resources": {
      "vm": { "templateVmid": 9001, "cpu": 2, "ramMb": 4096, "os": "windows|linux" },
      "network": { "gns3ProjectTemplate": "branch-office-v3", "attachVmToNode": "PC1" },
      "containers": [ { "image": "…", "role": "…" } ]
    },
    "access": { "kind": "guacamole_rdp|guacamole_vnc|guacamole_ssh|web_terminal",
                "idleSuspendMinutes": 20, "hardTtlMinutes": 120 },
    "breakScript": [ /* ordered steps run on the provisioned env to inject the fault */ ],
    "resetScript": [ /* return env to pre-break baseline without full reprovision */ ],
    "cleanup": [ /* destroy-time steps (revoke creds, purge home dir) */ ],
    "evidence": [                      // what the grader can verify from the real env
      { "id": "dns-fixed",
        "collector": "guest_exec",     // guest_exec | ssh | file_read | http_probe | service_state
        "spec": { "os": "windows",
                  "command": ["powershell","-c","(Get-DnsClientServerAddress -AddressFamily IPv4).ServerAddresses"],
                  "expect": { "notContains": "9.9.9.9" } } }
    ]
  },

  "objectives": [
    { "id": "o1", "required": true, "pointValue": 40,
      "predicateType": "lab_evidence_matches",     // NEW predicate family
      "predicateParams": { "evidenceId": "dns-fixed" } },
    { "id": "o2", "required": true, "pointValue": 20,
      "predicateType": "action_event_occurred",    // existing — still used for chat/notes/AD
      "predicateParams": { "actionType": "ticket.add_note", "payloadMatch": { "ticketId": "SD-DNS-01" } } }
  ],

  "randomization": {                   // NEW — port of ticket_params.py idea
    "seedFrom": "attempt_id",          // deterministic per attempt (replayable)
    "variables": {
      "USERNAME":  ["mfields","tnguyen","rkhan","apatel","jlopez"],
      "HOSTNAME":  ["BR-LT-014","BR-LT-021","BR-LT-033"],
      "BAD_DNS":   ["9.9.9.9","1.1.1.1","208.67.222.222"]
    }
    // substituted into breakScript / evidence / description via {{VAR}} placeholders,
    // exactly like ticket_params.substitute(); anchors written variable-aware.
  },

  "acceptableFixes": [                 // NEW — grader accepts any of these end-states
    { "evidenceId": "dns-fixed", "note": "set NIC to DHCP" },
    { "evidenceId": "dns-fixed", "note": "set correct static DNS 10.0.0.10" }
  ]
}
```

### New predicate types needed (grader)

| predicateType | verifies | source |
|---|---|---|
| `lab_evidence_matches` | a `lab.evidence[]` collector result matched its `expect` | `lab_evidence` rows (Phase 5) |
| `lab_command_output_matches` | ad-hoc command output regex/contains | guest_exec / ssh |
| `lab_service_state` | a Windows/Linux service is running/stopped | `service_state` collector |
| `lab_file_state` | file exists / contains / hash | `file_read` collector |
| `lab_network_reachable` | host/port reachable *from inside the lab* | `http_probe` / guest_exec ping |

Existing predicate types (`action_event_occurred`, `directory_group_membership`,
`directory_user_field`, `ticket_verified_resolved`) stay for the **simulated**
world (AD overlay, asset overlay, chat, ticket notes). A single scenario mixes
both: e.g. reset the AD account (simulated predicate) **and** confirm the client
can reach the DC (real-lab predicate).

Ticket types the schema must cover (all expressible with the above): password/
lockout (simulated AD), DNS / hosts file / DHCP / static-IP / gateway / NIC
(real Linux or Windows VM), mapped drive / shared-drive / permissions (real VM +
simulated AD), printer / browser-proxy / firewall-rule / stopped-service (real
VM), AD account (simulated + real DC reachability), software install / VPN /
RDP failure (real VM), Linux networking (real VM or GNS3 node).

---

## D. LabProvider interface (design)

One async interface, several implementations, selected by `definition_json.lab.provider`.

```python
class LabProvider(Protocol):
    async def provision(self, spec: LabSpec) -> LabHandle: ...
        # create the env from a template/profile; apply randomization; run breakScript.
        # idempotent per attempt (retry-safe); returns a handle with ids only.
    async def start(self, h: LabHandle) -> None: ...
        # power on / unsuspend; wait until guest-agent (or health()) responds.
    async def get_access(self, h: LabHandle, student_id: int) -> AccessGrant: ...
        # scoped, expiring browser URL (Guacamole) or WS terminal endpoint;
        # one student per session, ephemeral creds, revoked on reset/destroy.
    async def collect_evidence(self, h: LabHandle, specs: list[EvidenceSpec]) -> list[EvidenceResult]: ...
        # run each collector inside the env; return {id, raw, matched, collectedAt}.
        # results become `trusted` ServiceDeskAttemptEvent rows via /actions.
    async def reset(self, h: LabHandle) -> None: ...
        # run resetScript to baseline; cheaper than reprovision; keeps the handle.
    async def suspend(self, h: LabHandle) -> None: ...
        # idle saver (~20 min no activity). RAM->disk for VMs; stop for containers.
    async def destroy(self, h: LabHandle) -> None: ...
        # run cleanup; revoke Guac conn+user; delete VM/container; mark destroyed_at.
    async def health(self, h: LabHandle) -> LabHealth: ...
        # {state: provisioning|running|suspended|error|destroyed, detail, lastSeen}
```

`LabHandle` persists to a **new** `lab_sessions` table (generalises `vm_assignments`):
`id, attempt_id (FK, unique → 1 student/session), provider, external_refs (JSON:
{vmid, gns3_project_id, container_ids, guac_conn_id, guac_username}), status,
access_url_hint, idle_since, expires_at, provisioned_at, suspended_at,
destroyed_at, error, retry_count`.

| Implementation | Backs onto | Reuse | Build |
|---|---|---|---|
| `SimulatedProvider` | the existing client `simulation-engine` + `cli-labs` engine | ~all | thin adapter so "no real env" still fits the interface |
| `DockerProvider` | local Docker (already on host) | container run/exec/rm | idle stop, evidence via `docker exec` |
| `LxcProvider` | Proxmox LXC or host LXD | `asyncssh` for exec | template clone, snapshot reset |
| `ProxmoxVmProvider` | **`proxmox_service.py`** (exists) | `clone_template`/`start_vm`/`get_vm_ip`/`destroy_vm` | add `suspend` (`qmsuspend`), `reset` (restore snapshot), `collect_evidence` (`agent/exec`), `health` |
| `Gns3Provider` | GNS3 server REST API `:3080` (`gns3fy`) | — | project-from-template, node start/stop, evidence via node console or attached VM |
| `Gns3ProxmoxProvider` | GNS3 topology + a Proxmox VM bound to a GNS3 cloud/host node | both of the above | the "realistic branch office with a real Windows client" case |

Lifecycle orchestration (TTL, idle-suspend, background destroy, retry) already
exists in `routers/labs.py` — **lift it into a provider-agnostic
`services/lab_orchestrator.py`** and drive it from a periodic task instead of
per-request `BackgroundTasks`.

---

## E. Open-source stack (2026 research)

All self-hostable, all permissive/OSS. No paid SaaS required.

| Need | Pick | Why / license | Notes |
|---|---|---|---|
| Network topology labs | **GNS3** (server REST API `:3080`, `gns3fy` Python client) | GPLv3, mature REST API, template→project→nodes/links programmatically | Runs on the Proxmox host or its own VM. Use `gns3fy` (davidban77) or raw REST. |
| Browser remote desktop | **Apache Guacamole 1.6.0** (Jun 2025) — RDP/VNC/SSH → HTML5 | Apache-2.0; **already integrated** (`guacamole_service.py`) | REST API has no official docs but is stable; community OpenAPI spec exists (`guacamole-operator/guacamole-rest-api`). Keep it. |
| VM host + API | **Proxmox VE 8** + `proxmoxer` | AGPL host, permissive client; **already integrated** | VE 8 `agent/exec` + `agent/exec-status` = command execution **and output** on the guest → use for evidence, no SSH into student VMs. `command` param is now an **array** (VE8 breaking change). |
| Local LLM (requester chat, ticket gen, grading assist) | **Ollama** (OpenAI-compatible `/v1`, tool calling stable as of 2026) | MIT; **already integrated** via `ai_service.py` (`AI_IS_LOCAL`) | Models with reliable tool calling: Qwen3, Llama 4 Scout, Mistral Small 3.1. Keep budget + rate-limit guards. `vLLM` is the scale-up path if one box isn't enough. |
| Open WebUI | **skip** for now | not needed | Only useful as a human chat console; our AI is API-driven. Revisit only for staff prompt tuning. |
| Evidence via SSH (containers/LXC fallback) | **`asyncssh`** | Eclipse Public License / it's fine; async fits FastAPI; ~15× faster multi-host than paramiko | Only where guest-agent isn't available. Prefer guest-agent/`docker exec`. |
| Windows remote admin (evidence) | **Proxmox `agent/exec` running PowerShell** first; `pypsrp`/WinRM only if agent unavailable | keeps one code path | Avoid `paramiko`+Win32-OpenSSH unless a profile needs it. |
| Idle detection / lifecycle | **home-grown** on `lab_sessions.idle_since` + a periodic task; Guac "last active" + guest-agent CPU/session probe as signals | — | 20-min idle → `suspend()`; `hardTtlMinutes` → `destroy()`; nightly sweep destroys anything `suspended` > N hours. |
| Remote desktop alternatives (noVNC / MeshCentral / RustDesk) | **noVNC only** (already inside Guacamole's stack conceptually) | — | RustDesk/MeshCentral are agent-based fleet tools — wrong shape for ephemeral per-attempt VMs. Guacamole is the right abstraction; don't add a second. |

---

## F. Phased implementation plan

Your rough order is right; two swaps and some splitting:

| Phase | Deliverable | Depends on | Notes vs your list |
|---|---|---|---|
| **1** | *This document.* Inventory + contracts + stack decision. | — | done |
| **2** | **Canonical ticket/session contract v2.** Extend `definition_json` (`lab`, `rootCause`, `requester.persona`, `randomization`, `acceptableFixes`); add `lab_evidence_*` predicate *stubs* (return "unverifiable" until Phase 5); `lab_sessions` migration; fold the 6 incidental client state domains into `current_state`; pick one xterm terminal component. **No provider yet.** | 1 | unchanged |
| **3** | **AI requester chat.** New `ai_service` feature `service_desk_requester_chat`: turn-based, grounded in `requester.persona` + `rootCause` (server-side only), injection-delimited, budgeted, rate-limited; transcript stored as (untrusted) events; optional `chat.extracted_fact` trusted event when the student elicits a ground-truth hint. | 2 | unchanged |
| **4** | **First real lab: `DockerProvider` + `SimulatedProvider` adapter.** Implement `LabProvider` interface; `lab_orchestrator.py` (TTL/idle/destroy lifted from `labs.py`); one Linux ticket end-to-end (e.g. broken `/etc/resolv.conf` or `hosts` file) in a container, browser web-terminal (xterm over WS). Docker is already on the host → zero new infra. | 2, 3 | **swap:** do Docker before GNS3/Proxmox — fastest path to "student types real commands", no Proxmox creds needed |
| **5** | **Evidence-based grading for real labs.** `collect_evidence()` for Docker (`docker exec`) + guest-exec path; wire `lab_evidence_matches` / `lab_command_output_matches` / `lab_service_state` / `lab_file_state` predicates into `evaluate_objectives`; evidence rows become `trusted` events via `/actions`. Retire trust in any client-only "resolved" flag for lab tickets. | 4 | unchanged |
| **6** | **`ProxmoxVmProvider`.** Configure `PROXMOX_*` (staging Proxmox first); add `suspend`/`reset`(snapshot)/`collect_evidence`(`agent/exec`)/`health` to `proxmox_service.py`; one Windows ticket (stopped service / static DNS) via Guacamole RDP. Reuse `vm_assignments`→`lab_sessions`. | 4, 5 | **swap:** Proxmox VM before GNS3 — Windows/Linux desktop tickets are the bulk of a help desk; GNS3 is a narrower slice |
| **7** | **`Gns3Provider`.** GNS3 server on the Proxmox host; project-from-template; network tickets (gateway, DHCP, VLAN, routing) with a real client node; evidence via node console or an attached Proxmox VM (`Gns3ProxmoxProvider`). | 6 | was Phase 6 |
| **8** | **Browser remote desktop hardening.** Guacamole scoped access already exists; add per-session recording (optional), clipboard/file-transfer policy, connection cleanup audit, mobile fallback. | 6 | unchanged |
| **9** | **Randomization / unlimited practice.** `randomization` block live (deterministic per `attempt_id`); "practice pool" assignments (draw a random published scenario in a domain, no attempt cap, no XP or reduced XP); ticket queue UI. | 5 | unchanged |
| **10** | **Idle suspend / shutdown / resource queue.** Periodic task: 20-min idle → `suspend`, hard TTL → `destroy`, nightly sweep; a global concurrency cap with a fair queue ("your lab starts in ~3 min"); admin dashboard of live `lab_sessions` + force-destroy. | 4–9 | unchanged |

**Cross-cutting, every phase:** keep the append-only event ledger authoritative;
never let a browser assert resolution; every provider action is
audit-logged; production changes only through `scripts/deploy.sh`.

---

## What Phase 2 builds first (concrete)

1. **Migration** `xxxx_service_desk_lab_contract`:
   - `lab_sessions` table (schema in §D).
   - `service_desk_attempts.lab_session_id` nullable FK.
   - no change to `_scenario_versions` (the `lab` block lives inside the existing
     `definition_json` — no column change, stays SQLite/PG-portable).
2. **`service_desk_scenario_validation.py`**: accept + validate the new optional
   `lab`, `rootCause`, `requester.persona`, `randomization`, `acceptableFixes`
   keys; a scenario with **no** `lab` block stays 100% valid (backward compatible).
3. **`service_desk_objectives.py`**: register `lab_evidence_matches` (+ siblings)
   as known predicate types that currently evaluate to
   `{"server_verifiable": false}` — so authors can write them now and Phase 5
   makes them real.
4. **`packages/shared/src/scenario-types.ts`**: mirror the new optional fields.
5. **Client**: choose one `<Terminal>` component (xterm.js) and route both the
   `cli-labs` engine and a future real WS through it; fold `chat/asset/pc_shelf/
   server_room/deployment/shipping` into the serialized `current_state`.
6. **Delete** `service-desk-app/apps/api` (stub) after confirming nothing imports it.
7. **Docs**: `docs/service-desk-realism/PHASE-2-CONTRACT.md` with the frozen v2
   `definition_json` schema + one worked example scenario JSON (no lab, then with
   a Docker lab) for authors.

No infrastructure, no providers, no VMs in Phase 2 — it is purely the contract +
storage + validation + type mirror, all shippable through normal CI + deploy.

---

## Blockers / open questions

1. **Proxmox access.** Is there a **staging/non-prod Proxmox** (or a safe VMID
   range + API token) we can target for Phases 6–7, or is it the same box that
   serves other workloads? Need: `PROXMOX_HOST`, an API token scoped to a
   resource pool, a VMID pool that won't collide, and Windows/Linux **templates**
   with `qemu-guest-agent` installed and `guest-exec` enabled.
2. **Guacamole instance.** `guacamole_service.py` expects `GUACAMOLE_URL` +
   admin creds + a `postgresql` datasource. Is there a running Guacamole, or does
   Phase 6 stand one up (guacd + guacamole + its Postgres — 3 containers)?
3. **Windows licensing.** Windows 10/11 + Windows Server eval templates are
   180-day; acceptable for a lab that reprovisions from template, but confirm
   we're comfortable with eval activation and periodic template refresh.
4. **Host capacity.** `/` is at 81% after cleanup (11 GB free). Concurrent
   Windows VMs (4 GB RAM, ~15 GB thin disk each) need real headroom — how many
   **concurrent** students in the pilot, and is lab storage on the same LV or a
   separate pool?
5. **GNS3 appliances.** Which router/switch images are we licensed to run
   (Cisco IOSvL2/IOSv need a CML/VIRL entitlement; open alternatives: FRR,
   VyOS, Arista cEOS-lab free-with-account, Nokia SR Linux)? Pick the free set
   now so scenario authors target it.
6. **Idle/session policy.** Confirm the "20-min idle → suspend, 120-min hard TTL,
   nightly destroy of anything suspended > 24 h" defaults, and whether an
   in-progress **assessment** attempt is exempt from idle-suspend.
7. **XP for unlimited practice.** Does replayable practice grant XP (risk:
   farming) or 0 XP / one-time XP per scenario? Affects Phase 9 + progression.
8. **`nexus-staging` stack.** Still running (4 containers). If it's the intended
   staging target for lab work, keep it; if obsolete, reclaiming it frees the
   host for lab VMs. Needs an owner decision (also noted in the cleanup report).
