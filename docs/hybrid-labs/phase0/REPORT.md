# Nexus Hybrid Labs — Phase 0 Report

Date: 2026-09-10 UTC

Branch: `research/hybrid-lab-phase0`

Base: `7477b93` (`fix/core-wave5-progress-review`)

Supporting documents:

- [Server inventory](SERVER-INVENTORY.md)
- [Network design](NETWORK-DESIGN.md)
- [INC2504 POC design](INC2504-POC-DESIGN.md)
- [GO / NO-GO](GO-NO-GO.md)

## Post-Phase-0 controlled POC validation (2026-09-19)

Phase 0 recorded the evidence available at the time and remains the baseline
for production architecture. A later controlled INC2504 POC has now validated
the narrow single-instance lifecycle described in
[INC2504 live-test notes](../INC2504-LIVE-TEST.md): clone template VM173 into
the `nexus-labs` pool, enforce a Nexus-owned name, wait for clone/start task
completion, confirm running state, provision through the Windows Guest Agent,
recover through a Windows reboot, verify all six expected final-state values,
and safely destroy disposable VM172 after rechecking VMID, pool membership,
and name ownership.

The generated temporary Windows password remained out of persisted state and
transport payload logging. The live role required `Pool.Audit`, `VM.Allocate`,
`VM.Audit`, `VM.Clone`, `VM.Config.Disk`, `VM.GuestAgent.Audit`,
`VM.GuestAgent.Unrestricted`, and `VM.PowerMgmt`. `Pool.Audit` is specifically
needed for the fail-closed resource-pool ownership check before destruction.

This successful lifecycle POC does not supersede the production blockers:
Windows licensing/activation, single-instance fixed-IP `vmbr1`, final live
Guacamole student-access validation, durable worker/reconciler/recovery,
trusted Proxmox TLS verification, production secret provisioning, and broader
capacity/concurrency design. FastAPI `BackgroundTasks` remains a production
blocker for lifecycle durability.

## Executive result

Decision: **READY AFTER SPECIFIC BLOCKERS**.

The repository really does have dormant Proxmox/Guacamole lab plumbing, but the live Nexus service has neither integration configured. The actual PVE endpoint was identified, yet authorized read-only PVE credentials were unavailable, so physical capacity, storage, VM inventory, bridges, and firewall state remain unknown. The network evidence that is available is enough for a conservative conclusion: student labs are unsafe today because Nexus and reachable PVE management share the household/production `/24` and no isolated lab segment has been demonstrated.

## Actual server

Confirmed Proxmox endpoint: `192.168.0.50:8006`; certificate identity `pve.home.lan` with internal SAN `192.168.100.2`. Proxmox version, physical CPU model, cores/threads, RAM, swap, load, storage backends/capacity, and current VM/LXC inventory are **UNKNOWN** because batch SSH and unauthenticated API requests did not grant inventory access.

Do not mistake the measured Nexus VM for the server: it has 4 QEMU vCPUs, 7.3 GiB RAM, 4 GiB swap (3.2 GiB used), and a 60 GiB virtual disk whose root filesystem has only about 2 GiB free.

## Current workloads

Inside the Nexus VM:

- systemd FastAPI/Uvicorn backend;
- nginx frontend container;
- Nexus Service Desk container;
- local SQLite production database configuration (data not queried);
- Docker networking;
- no live Guacamole container/service;
- no live Proxmox or Guacamole environment configuration.

Other VMs/LXCs and their allocations are **UNKNOWN**.

## Capacity

- Current Nexus workloads: **POSSIBLE WITH LIMITS**; currently running with low guest CPU load, but guest disk is 97% full and swap use is high.
- Nexus + one Windows lab: **NOT RECOMMENDED** until physical host headroom is measured.
- Nexus + two Windows labs: **NOT RECOMMENDED**.
- Windows + small Linux printer endpoint: **NOT RECOMMENDED until measured**; this remains the intended smallest POC.
- Future small network lab: **NOT RECOMMENDED** on current evidence.

No claim about host capacity can be made from an individual guest's available memory or disk.

## Current network

Nexus is `192.168.0.101/24`; PVE management at `192.168.0.50:8006` is directly connected on the same subnet. Household/private neighbors are also present. PVE bridge, VLAN, and firewall details are unknown. UFW is active on Nexus, but host-level rules were not readable without elevation.

## Isolation verdict

**UNSAFE FOR STUDENT LABS.** There is no demonstrated external control preventing a local administrator in a same-bridge Windows VM from reaching PVE management, Nexus, SSH, household devices, arbitrary private networks, or future peer labs. Application authorization is useful but is not a network security boundary.

## Existing Nexus Proxmox integration

Verified in [proxmox_service.py](../../../backend/app/services/proxmox_service.py), [labs.py](../../../backend/app/routers/labs.py), [vm_assignment.py](../../../backend/app/models/vm_assignment.py), and tests:

What works in code:

- Proxmox API-token authentication from environment variables, with configurable TLS verification;
- VMID pool scan, clone request, linked-clone eligibility checks for LVM-thin/ZFS/RBD/Btrfs, and full-clone fallback;
- clone task polling with timeout and exit-status check;
- VM start;
- QEMU guest-agent IPv4 polling;
- stop/delete destruction;
- persisted assignment states, error text, retry counter, start/expiry/destruction timestamps;
- authenticated ownership path from current student to lab run to assignment;
- duplicate assignment guard via unique `lab_run_id`;
- tests for clone mode, asynchronous HTTP response, duplicate clicks, persisted provisioning stages, expiry, scoped access, and cleanup.

Gaps before real students:

- `_find_free_vmid()` is read-then-use and races across concurrent launches;
- provisioning/cleanup run in FastAPI `BackgroundTasks`, which are not durable across process crashes/restarts;
- no startup/periodic reconciler resumes provisioning, expires idle labs, or discovers orphans;
- clone completion can leave an orphan if the process dies before persisting VMID;
- failed assignments with known resources are not automatically reconciled;
- guest IP selection accepts the first non-loopback IPv4 without expected MAC/subnet/interface validation;
- VM start task/readiness and RDP readiness are not polled;
- no template allowlist, resource pool, tag, node/storage, network/bridge, quota, or per-student concurrency restriction is enforced in service code;
- actual API token permissions are unknown because no token is configured;
- destruction does not revalidate VM ownership/pool/tag/name before stop/delete;
- cleanup errors become `failed` without guaranteed retry;
- expiry cleanup is request-driven or a manual admin endpoint, not scheduled/durable.

## Existing Guacamole integration

Verified in [guacamole_service.py](../../../backend/app/services/guacamole_service.py), [LabPage.jsx](../../../frontend/src/pages/LabPage.jsx), and tests:

- server authenticates with configured Guacamole administrator credentials;
- creates an RDP connection to discovered VM IP/3389;
- creates a random temporary user and grants only `READ` on that connection;
- obtains a student token; admin token is not returned;
- deletes the previous temporary user on access refresh;
- deletes user/connection on submit/cleanup;
- frontend embeds the scoped URL in an iframe and offers a new tab;
- connection and per-user limits are set to one.

Limitations:

- live Guacamole is absent/unconfigured;
- only Windows RDP is implemented; no SSH connection path;
- RDP uses `ignore-cert=true` and `security=any`;
- no connection history/recording configuration, durable expiry sweeper, or independently verified token revocation exists;
- cleanup is tied to non-durable background/manual flows;
- end-to-end iframe, CSP, cookie, token-leak, and RDP readiness tests were not possible.

Classification: **NOT READY**. The code skeleton is promising but needs live deployment and security hardening.

## Windows template

**UNKNOWN — NOT VERIFIED ON PROXMOX.** Repository prose names `WS2022-DC` and `Win11-Enterprise`, but no production template VMID is configured and source text is not infrastructure evidence. No stopped VM was booted.

## Windows licensing

**UNVERIFIED — BLOCKER BEFORE STUDENT USE.** No reliable licensing evidence was found. No key was exposed and activation was not attempted.

## Proposed lab network

Use a dedicated, externally firewalled `10.26.19.0/24` lab segment: gateway `.1`, optional evidence gateway `.2`, `NX-2504` `.10`, deliberately stale/unused printer `.80`, and real isolated `ENG-COPIER` `.94`. VLAN/bridge identity remains TBD after collision review. Deny all private/management/Nexus/peer destinations by default. Permit Guacamole-to-Windows RDP and Windows-to-printer IPP only, plus narrowly approved services.

## INC2504 POC

One disposable Windows clone (2 vCPU, 6–8 GiB RAM, about 80 GiB provisioned disk) plus one small isolated CUPS/IPP endpoint (1 vCPU, 512 MiB–1 GiB RAM, 5–10 GiB provisioned disk). The workstation begins with a running spooler, a failed queued job, and stale destination `10.26.19.80`. Nexus holds authoritative asset data for `10.26.19.94`. The learner investigates, commits a diagnosis, changes the destination, sends a new test page, verifies an external CUPS completion receipt, and documents the ticket. CUPS with a sink backend is preferred because it produces real accepted/completed job semantics; ping never counts.

First POC status: **PRACTICE ONLY / MENTOR REVIEWED**, with no automatic competency credit.

## Trusted evidence

Do not trust arbitrary Windows logs/screenshots. Use server-timestamped Nexus actions, external firewall flow evidence, CUPS job acceptance/completion, attempt-specific topology identity, and an append-only/tamper-evident ledger. Lock diagnosis before remediation, require a new receipt after repair, reject `.80` and other attempts, and latch harmful actions so later success cannot erase them. Guacamole server-side recording can support mentor verification of UI inspection, but client telemetry is not automatic proof.

The existing Service Desk rubric remains Investigation 15, Diagnosis 25, Remediation 30, Verification 20, Documentation 10.

## Lifecycle

On-demand launch; warning at about 10 inactive minutes; graceful shutdown at about 20–30; reconnect to the retained attempt; proposed 24-hour stopped-attempt retention; proposed 4-hour hard TTL; on completion export evidence, revoke Guacamole access, and destroy owned disposable resources. Reset creates a fresh generation rather than repairing a dirty clone in place.

A durable queue/worker and periodic reconciler must own provisioning, leases, retries, restart recovery, idle/TTL enforcement, orphan detection, evidence export, and cleanup. FastAPI background tasks are insufficient for these guarantees.

## Failure handling

All provisioning calls must be idempotent and state-machine driven. API/broker outages retry within bounded deadlines. Wrong IPs are rejected by expected subnet/MAC/interface. Duplicate clicks return the same assignment. Simultaneous launches use atomic allocation and quotas. Browser closure does not abandon ownership. Reset serializes revoke/export/destroy/recreate. Evidence outage never fabricates verification. Every partial resource remains discoverable until reconciled.

## GO / NO-GO

| Requirement | Result |
|---|---|
| Enough RAM | UNKNOWN |
| Enough disk | UNKNOWN |
| CPU virtualization suitable | UNKNOWN |
| Safe lab network design exists | PASS |
| Proxmox management isolated | FAIL |
| Nexus production isolated | FAIL |
| Restricted Proxmox API plan | PASS |
| Guacamole path viable | UNKNOWN |
| Windows template path viable | UNKNOWN |
| Windows licensing path identified | FAIL |
| Printer endpoint approach chosen | PASS |
| Reset strategy chosen | PASS |
| Evidence trust model defined | PASS |

## Recommendation

**READY AFTER SPECIFIC BLOCKERS.** Do not begin Phase 1 until the PVE inventory proves capacity, the isolated network is implemented and negatively tested, API permissions and lifecycle durability are designed, the Windows template/licensing path is verified, and Guacamole is deployed and hardened.

## Git and production safety

This documentation branch is a child of the supplied Wave 5 tip. The original `feature/service-desk-p1-workspace` worktree had unrelated pre-existing changes; they were preserved and not mixed into this worktree. No application behavior was edited.

Production remains at the supplied state: schema 0064, V2 off, no pilot enrollment, and no deployment from this branch. These supplied production-state facts were not revalidated by querying production data because Phase 0 prohibited production-data changes/access beyond safe configuration inspection.

Safety confirmation:

- no VM created, cloned, started, stopped, rebooted, or deleted;
- no container created, started, stopped, changed, or deleted;
- no snapshot created or deleted;
- no network, bridge, VLAN, route, or firewall changed;
- no Proxmox configuration or storage changed;
- no Guacamole configuration changed;
- no API token created, rotated, or exposed;
- no package installed;
- no deployment or migration;
- V2 remains off;
- no production data queried or changed;
- no merge to main and no INC2504 implementation.
