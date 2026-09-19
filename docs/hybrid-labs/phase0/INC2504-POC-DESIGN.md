# Hybrid Labs Phase 0 — INC2504 POC Design

Status: Phase 0 target architecture, with a controlled lifecycle POC validated
on 2026-09-19. This document's multi-user topology, trusted evidence, and
durable lifecycle designs are not yet production implementations.

## Validated implementation boundary

The controlled implementation proved one allowlisted, single-instance
INC2504 lifecycle on the shared isolated `vmbr1`: template VM173 clone into
the `nexus-labs` pool, Nexus-owned naming, task-aware start, Windows Guest
Agent provisioning and reboot recovery, exact final-state verification, and
protected destruction of disposable VM172. The temporary Windows password was
not persisted. The live Proxmox role required `Pool.Audit` plus the documented
VM allocation, audit, clone, disk-config, guest-agent, and power privileges.

That result validates the current POC mechanism, not the future topology below.
The current fixed `10.10.10.10` address allows only one active instance, the
Guacamole student path still needs final production validation, and the API
still uses non-durable FastAPI `BackgroundTasks`. Windows licensing/activation,
trusted Proxmox TLS, production secret provisioning, durable reconciliation,
and multi-user capacity/concurrency remain production blockers.

## Scenario

INC2504: “My drawing packets are not printing.”

The smallest useful topology is one disposable Windows workstation and one isolated Linux print endpoint:

```text
Browser -> Nexus -> scoped Guacamole RDP -> NX-2504 (10.26.19.10)
                                             |
                                             | IPP, only after repair
                                             v
                                  ENG-COPIER (10.26.19.94)
                                             |
                                             v
                              trusted receipt/evidence collector
```

Proposed allocations (subject to the still-missing PVE capacity proof):

- `NX-2504`: 2 vCPU, 6–8 GiB RAM, about 80 GiB provisioned disk;
- `ENG-COPIER`: 1 vCPU, 512 MiB–1 GiB RAM, 5–10 GiB provisioned disk.

These are guest allocations. The actual physical storage cost depends on the template, clone mode, changed blocks, snapshots, and backing-store overhead.

Starting state on `NX-2504`:

- Windows Print Spooler running;
- printer `ENG-COPIER` installed with a stale IPP destination using `10.26.19.80`;
- authoritative Nexus asset record states the current endpoint is `10.26.19.94`;
- at least one initial queued job has failed;
- learner has local administrator rights only inside this disposable VM;
- the old address is a controlled black hole, not another real service.

Learner flow:

1. Inspect Print Spooler status and the failed queue.
2. Inspect the configured printer port/destination.
3. Open the authoritative asset/business context in Nexus.
4. Commit a diagnosis in Nexus before changing state.
5. Change only the destination from `.80` to `.94`.
6. Send a new Windows test page.
7. Verify an external receipt, then document the ticket.

## Printer endpoint choice

**Choose CUPS with IPP and a purpose-built sink backend.** A small Linux VM or tightly isolated container can expose `ENG-COPIER` at `10.26.19.94:631`. Windows can use its built-in IPP class support, avoiding a vendor driver and reducing template complexity.

CUPS is preferred over a bare TCP/9100 listener because it has job semantics, identifiers, accepted/completed state, timestamps, source attribution, and a controllable backend. The sink backend should discard document content after computing the minimal receipt metadata needed for the exercise. A raw JetDirect-style receiver is a fallback only if Windows IPP behavior proves unsuitable; it would need extra framing/job validation so “TCP connected” cannot masquerade as “printed.”

Success is **not** ping. It is a new, non-empty print job accepted by the external endpoint after the remediation event, tied to the active attempt, and marked completed by the trusted receiver.

## Trusted evidence model

The Windows VM is student-administered and therefore untrusted. Event Viewer, PowerShell transcripts, screenshots, and files inside it can support mentor review but cannot be the sole source of automatic credit.

Use an append-only Nexus evidence ledger with server timestamps, attempt ID, event type, source, normalized facts, and a hash chain or equivalent tamper-evident sequencing. Trusted events come from systems the student cannot administer.

| Rubric area | Points | Trusted/mentor-reviewed evidence |
|---|---:|---|
| Investigation | 15 | Nexus records that the learner opened the attempt's asset record and inspection prompts before diagnosis. A Guacamole server-side recording can let a mentor confirm spooler/queue/port inspection. Do not claim automatic semantic proof from client telemetry. |
| Diagnosis | 25 | Learner commits one diagnosis through Nexus; server locks and timestamps it before remediation evidence is accepted. Correct hypothesis: stale printer destination, not failed spooler or network reachability alone. |
| Remediation | 30 | External firewall/flow sensor observes the assigned workstation reach the correct endpoint/protocol; CUPS ties the job to the attempt. Mentor recording confirms the narrow destination edit. No credit for touching another printer/attempt. |
| Verification | 20 | CUPS emits a **new** accepted-and-completed job receipt after diagnosis/remediation, with job sequence greater than the seeded failure/baseline. Ping, opening port 631, or reusing a seeded receipt fails. |
| Documentation | 10 | Nexus compares the final note with immutable facts: symptom, stale `.80`, current `.94`, action, receipt/job ID, and outcome. Mentor reviews wording in the first POC. |

### Ordering and safety rules

- Ledger states advance `INVESTIGATION -> DIAGNOSIS_COMMITTED -> REMEDIATION_OBSERVED -> VERIFIED -> DOCUMENTED`.
- Events cannot be backdated by the VM. Server receipt time and trusted source sequence control ordering.
- A verification receipt must be both new and later than the remediation boundary.
- Endpoint receipts include attempt ID via per-attempt topology mapping, source IP/MAC mapping, job ID, byte count, and timestamps; never trust an attempt ID supplied only by Windows.
- Wrong-target rejection: only the assigned `ENG-COPIER` endpoint for the active attempt can issue the receipt. `.80`, another attempt's endpoint, or arbitrary IPs yield no credit.
- Harmful-action latching: once a trusted policy event or mentor-confirmed prohibited action is recorded, later success does not erase it. Examples include disabling the spooler without cause, broad firewall weakening, changing a non-assigned target, or attempting management/private networks.
- Network deny telemetry is captured outside Windows. Actions visible only inside the VM remain mentor-reviewed for POC 1.
- Screenshots and Windows logs are labeled `student-controlled` in the ledger.
- Automatic competency credit is disabled for the first POC: **PRACTICE ONLY / MENTOR REVIEWED**.

## Reset strategy

Prefer a disposable linked clone from a sealed template plus an idempotent scenario bootstrap. Each attempt receives a fresh clone and fresh isolated print endpoint state. “Reset” destroys the old attempt only after evidence export/revocation succeeds, then creates a new attempt with a new identity; it should not mutate a running attempt in place.

If storage cannot safely support linked clones, use a full clone only after capacity and clone-time measurements. Never use a production VM as the rollback source.

## Lifecycle policy

| Event | Future behavior |
|---|---|
| Launch | On demand; idempotency key per lab run; durable worker claims a persisted provisioning record |
| About 10 minutes inactive | Warning in Nexus and Guacamole; activity must be server-observed, not a VM-supplied heartbeat |
| About 20–30 minutes inactive | Revoke new access, request graceful shutdown, then force-stop only after a bounded grace period if policy permits |
| Reconnect | Rebind a fresh scoped Guacamole identity to the same retained attempt; start it only if policy says retained stopped attempts may resume |
| Completed | Freeze/commit ledger, export trusted evidence, revoke Guacamole user/token/connection, destroy disposable resources |
| Abandoned stopped VM | Delete after 24 hours (proposed), after evidence export; exact retention needs owner approval |
| Hard TTL | 4 hours from launch (proposed), independent of browser activity; exact TTL needs owner approval |
| Reset | Serialized state-machine operation; revoke old access, export evidence, destroy old resources, provision a new attempt |

Provisioning, TTL enforcement, idle shutdown, cleanup retries, orphan discovery, and restart recovery require a durable queue/worker plus periodic reconciler. FastAPI `BackgroundTasks` are acceptable only for best-effort response-following work, not lifecycle guarantees.

## Failure behavior

| Failure | Nexus should eventually do |
|---|---|
| Proxmox API offline | Keep request pending with bounded exponential retry; show unavailable status; do not create a second assignment; alert after deadline |
| Clone task fails | Record sanitized failure/UPID correlation, reconcile whether a VM was partially created, remove it if owned, then allow an operator-controlled retry |
| VM boots but Windows not ready | Distinguish guest-agent, OS-ready, and RDP-ready states; wait to a deadline, then shut down/cleanup or quarantine for operator review |
| RDP unavailable | Retry readiness probes without issuing student access; expire and clean up if deadline passes |
| Guest agent reports wrong IP/interface | Match expected MAC/VLAN/subnet and route; reject loopback, APIPA, management, Docker, and unexpected interfaces |
| Guacamole unavailable | Keep VM retained for a short bounded window, issue no direct RDP credentials, retry broker setup, then gracefully stop/clean up |
| Nexus restarts during provisioning | Durable worker lease expires; reconciler resumes from persisted state and PVE task/ownership metadata |
| Worker restarts | Reclaim expired job lease; operations remain idempotent using attempt ID and resource tags/pool |
| Browser closes | Lab continues until idle/hard TTL; no VM-side heartbeat is trusted; reconnect uses the same attempt while retained |
| Student abandons lab | Idle warning, graceful shutdown, retention, evidence export, then deletion |
| Duplicate launch clicks | Return the same assignment; database uniqueness plus request idempotency; never queue a second clone |
| Two students launch simultaneously | Allocate VMIDs atomically via Proxmox `cluster/nextid` plus reservation/creation handling; apply per-student resource and concurrency quotas |
| Reset mid-session | Lock attempt, block new access, revoke Guacamole, finalize old ledger, destroy owned resources, then create a new generation |
| Evidence endpoint unavailable | Do not award verification; retain job/attempt within TTL, retry trusted receipt ingestion, and offer mentor escalation without fabricating success |

All resource deletions must first verify pool/tag/name/assignment ownership. A failed cleanup remains visible to the reconciler until resolved; “failed” must not become a terminal orphan state.
