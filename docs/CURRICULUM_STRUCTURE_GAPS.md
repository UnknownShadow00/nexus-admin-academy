# Curriculum Structure Gaps

This report records Phase 4 inputs discovered while grouping the existing
curriculum. Phase 3 intentionally does not solve these content and ordering
issues.

## Highest-priority gaps

- Microsoft 365 administration and troubleshooting are not represented as a
  coherent module.
- Entra ID appears late and thinly inside cloud identity instead of supporting
  the earlier account, access, and endpoint workflow.
- Intune and modern endpoint management are effectively absent.
- Service Desk practice is strongest in a few early storage containers and is
  not consistently threaded through Windows, networking, identity, server,
  Linux, and cloud modules.
- Security is often isolated in optional content. It should become a
  cross-cutting constraint in account verification, least privilege, endpoint
  response, network administration, remote support, Linux, and cloud work.

## Module balance

- **PC Hardware Foundations** is large and video-heavy. It needs a tighter
  support-job scope and more diagnostic practice rather than broad catalog
  coverage.
- **Windows Fundamentals & Diagnostics** combines a large catalog with a small
  required spine. Application, account, and diagnostic topics should be
  separated more deliberately during reorder.
- **Queue & Endpoint Operations** is overcrowded and mixes prioritization,
  printers, mobile devices, security, and support operations. Its content does
  not yet match one crisp skill promise.
- **Linux Production & Security** carries a substantial optional security block.
  The security content duplicates ideas elsewhere and is not integrated with a
  proportionate amount of operational practice.
- **Final Support Shift** is thin for a culminating Prove module. It has a useful
  required assessment path, but the capstone and evidence expectations need a
  deliberate Phase 4 review rather than more incidental optional content.

## Practice and assessment gaps

- Many modules contain Learn and Check activities but no meaningful Practice or
  Troubleshoot activity.
- “Prove” is appropriately rare today, but the final path needs explicit,
  trustworthy demonstrations aligned to module outcomes. A quiz or ordinary
  ticket should not be relabeled as competency proof.
- Identity modules need practical directory, group, permissions, and policy
  scenarios with safe verification and rollback.
- Networking hands-on work is uneven across addressing, DNS, DHCP, switching,
  routing, and connectivity troubleshooting.
- Cloud modules need more troubleshooting evidence and less reliance on concept
  recall.

## Ordering and duplication

- Endpoint support, Microsoft 365, Entra ID, Intune, and Service Desk routines
  should move earlier and reinforce one another.
- Some server, network, Linux, and security material becomes advanced before the
  common modern endpoint and collaboration workflow is established.
- Mobile, endpoint-security, and broad certification videos repeat concepts in
  multiple places. Phase 4 should choose the strongest source or distinguish
  review from new instruction.
- DNS, account/access, remote support, and documentation recur across stages.
  They should be intentionally spiraled with increasing complexity, not
  accidentally duplicated.

## Authoring gap

The current admin screen can inspect Stage/Module grouping while legacy storage
records remain editable. A safe drag-and-drop Stage/Module editor would expand
scope and should wait until Phase 4 settles the target order. Until then, the
single reviewed metadata file and failing validator are the maintenance path.
