# Phase 4C.1 practical upgrade

## Scope

Phase 4C.1 converts the existing required guided labs in Weeks 3, 5–7, and
13–17 in place. No weekly activity is added, removed, or made newly required.
The existing `TrainingWeekActivity.stable_id`, `content_ref`, and
`LabTemplate.id` remain authoritative, so existing `LabRun` completion stays
attached to the same curriculum identity.

## Evidence-case contract

`EvidenceCaseWorkbench` is a small presentation shell with:

- a domain-authored complaint and guidance level;
- initially collapsed evidence panels;
- required inspection identifiers;
- server-authored diagnosis/action questions;
- a server-gated deterministic after-state; and
- structured Issue, Evidence, Action, and Verification notes.

An incident may add one concise handoff field and may provide a focused
terminal profile. The contract does not model Intune, Active Directory,
Windows, Linux, or cloud resources. Those facts stay in each authored case.
`EndpointEvidenceWorkbench` remains the Phase 4B.2 compatibility wrapper.

## Focused terminal profiles

A profile maps a small command set to case-specific output and optional
inspection identifiers. Unknown commands do not fall through to the global
healthy terminal. `help` lists tool categories rather than the answer or an
exact required sequence. Commands reveal evidence; the backend grades the
resulting diagnosis and safe action, not transcript substrings.

Profiles are local component state and have no shared mutable incident state,
so commands cannot leak state between labs or students.

## Service Desk reuse

Existing tickets are shown only as non-gating reinforcement links. Their pack
unlocks, attempts, trusted events, and grading remain owned by Service Desk.
Phase 4C.1 does not create scenarios or add assessment dependencies.

## Future VM-ready handoff (not implemented)

A future real-VM activity may replace an authored evidence panel or focused
terminal with a server-issued observation while preserving the case boundary:

1. The VM adapter returns an opaque observation ID and display-safe evidence.
2. The lab verification endpoint records that observation ID for the owning
   student and LabRun.
3. The evidence case continues to own diagnosis, safe-action choice,
   documentation, and verification requirements.
4. Proxmox, Guacamole, provisioning, reset, and teardown remain outside the
   workbench component.

High-value future candidates are Windows Event Viewer/services/permissions,
PowerShell server inspection, and multi-machine client/domain/DNS validation.
No VM integration or infrastructure change is part of Phase 4C.1.
