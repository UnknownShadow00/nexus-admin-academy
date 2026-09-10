# Hybrid Labs Phase 0 — GO / NO-GO

## Checklist

No optimistic assumptions are used.

| Requirement | Status | Evidence / blocker |
|---|---|---|
| Enough RAM | **UNKNOWN** | Hypervisor total/used/available RAM could not be read; Nexus guest RAM is not host capacity |
| Enough disk | **UNKNOWN** | PVE storage backend, physical free space, thin-pool metadata, and template consumption unknown |
| CPU virtualization suitable | **UNKNOWN** | Nexus is a KVM guest, but physical CPU flags/core topology and BIOS state are unavailable |
| Safe lab network design exists | **PASS** | Deny-by-default `10.26.19.0/24` addressing and trust model documented; implementation/proof remains Phase 1 prerequisite |
| Proxmox management isolated | **FAIL** | Management is directly reachable from Nexus's household/production `/24`; no student network isolation is present/proven |
| Nexus production isolated | **FAIL** | No student lab segment, external deny policy, or attempt microsegmentation exists today |
| Restricted Proxmox API plan | **PASS** | Server-side, pool/tag/template/network allowlisted least-privilege worker plan is defined; actual token ACL still unknown and unconfigured |
| Guacamole path viable | **UNKNOWN** | Code supports scoped RDP access, but no live Guacamole is configured/deployed and no end-to-end RDP test exists |
| Windows template path viable | **UNKNOWN** | Repository names do not prove a PVE template; guest agent/RDP/UEFI/TPM/disk state unverified |
| Windows licensing path identified | **FAIL** | No reliable entitlement/evaluation record; blocker before student use |
| Printer endpoint approach chosen | **PASS** | Isolated CUPS/IPP endpoint with trusted sink receipt at `10.26.19.94` |
| Reset strategy chosen | **PASS** | Fresh disposable clone/generation; export/revoke/destroy old attempt before reprovisioning |
| Evidence trust model defined | **PASS** | External CUPS/network events plus append-only Nexus ledger; student-VM evidence is non-authoritative; POC mentor-reviewed |

Checklist totals: 5 PASS, 3 FAIL, 5 UNKNOWN.

## Decision

# READY AFTER SPECIFIC BLOCKERS

This does **not** authorize Phase 1 yet. It means the repository has enough of a software skeleton and the POC is small enough to continue once the following concrete blockers are closed:

1. Obtain an operator-approved read-only PVE inventory and record version, CPU/core/thread topology, virtualization flags, RAM/load/swap, storage backend and physical allocation, VM/LXC inventory, bridges/VLANs/routes, firewall state, and template inventory.
2. Demonstrate sufficient host RAM and storage headroom under realistic clone/boot I/O. Until then, one or two Windows labs are not recommended.
3. Implement and negatively test a dedicated deny-by-default lab network that cannot reach PVE management, Nexus internals, SSH, household LAN, private networks, or other students.
4. Define and verify a least-privilege PVE identity restricted to the lab pool, approved node/storage/bridge, and template(s). Do not use broad root-like rights.
5. Resolve VMID allocation, durable worker/reconciler, orphan cleanup, restart recovery, ownership-before-delete, quotas, and concurrent launch behavior.
6. Verify or build a sealed Windows evaluation/licensed template with guest agent, RDP readiness, patch baseline, reset/bootstrap, and documented legal use.
7. Deploy and harden Guacamole in the trusted gateway plane: validated certificates/security mode, scoped access, recording/audit, token hygiene, revoke/cleanup, and end-to-end iframe/RDP tests.
8. Validate the CUPS/IPP sink and external evidence ledger in an isolated, operator-controlled staging test.

Beginner-friendly summary: Nexus knows how to ask Proxmox for a clone and how to give one learner a temporary Guacamole link. What is missing is proof that this physical server has room and, more importantly, a network wall around a student who is an administrator inside Windows. Until those facts and controls are verified, do not place a student VM on this host.

## Current classifications

- Isolation today: **UNSAFE FOR STUDENT LABS**.
- Live Proxmox integration: **NOT CONFIGURED / NOT READY**.
- Current Guacamole integration: **NOT READY** (code exists but live service is absent and RDP settings need hardening).
- Windows template: **UNKNOWN — not verified on Proxmox**.
- Windows licensing: **UNVERIFIED — BLOCKER BEFORE STUDENT USE**.
- One Windows lab: **NOT RECOMMENDED until capacity and isolation pass**.
- Two simultaneous Windows labs: **NOT RECOMMENDED**.
