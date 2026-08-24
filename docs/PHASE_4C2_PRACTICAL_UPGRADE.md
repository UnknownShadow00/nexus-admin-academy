# Phase 4C.2 network, Linux, and cloud practical upgrade

## Verified baseline and scope

The pinned production-lineage baseline is Alembic `0059` with 35 modules,
320 activities, 143 required, 177 optional, and no unmapped activities. Its
learning-role totals are Learn 216, Check 38, Practice 29, Troubleshoot 31,
and Prove 6.

Repository inspection changed several assumptions from the preliminary audit:

- Week 10 cabling and connector media was already optional.
- All 13 Week 20 security-theory videos were already optional.
- Week 9 already contained valuable stateful addressing and packet-flow work,
  including historical submitted progress, so it was left unchanged.
- The existing network simulator models access switching but not routed DHCP
  relay. Week 11 therefore uses the shared evidence workbench for the routed
  incident and links its existing stateful access-port exam as non-gating
  reinforcement rather than pretending the simulator supports a new domain.
- The Week 8 Service Desk activity has a stable ID ending in `inc2504` but its
  authoritative `content_ref` is `inc2407`; neither identity was rewritten.

## In-place conversions

Existing LabTemplate IDs 2, 10, 11, 16, 17, 18, and 20 are converted in
place for Weeks 8, 11, 12, 18, 19, 20, and 22. Their corresponding
TrainingWeekActivity identities remain unchanged. No activity, networking lab,
Service Desk scenario, or curriculum module is added or removed.

The cases use the Phase 4C.1 `EvidenceCaseWorkbench` contract. Domain facts,
commands, answer keys, safe actions, and verification states remain authored
inside each case; the component is not a workflow engine or a simulator.

## Deterministic terminal profiles

Weeks 8, 18, 19, and 20 receive focused profiles. Commands map only to
case-specific display output and optional inspection IDs. Nothing executes on
the host. Unknown commands return a case-scoped unsupported-command response,
not a generic healthy state. The backend grades inspected evidence and the
selected plan, never terminal transcript substrings.

Guidance fades deliberately: Week 18 names useful Linux tools and paths, Week
19 suggests evidence categories without an exact order, and Week 20 supplies
only the symptom and environment. Week 20 includes coherent distractors: nginx
is running and configured correctly, its listener exists, and the firewall is
healthy while the full root filesystem and runaway logs explain the outage.

## Curation and final totals

Week 21 videos 54 and 56 become optional. Video 55, "Cloud Models," remains
required because it is the concise teaching source for IaaS/PaaS/SaaS
responsibility boundaries assessed by the required Week 21 check; video 53
also remains required. Existing Week 10 and Week 20 media remain accessible
under their already-optional status.

The resulting totals are 35 modules, 320 activities, 141 required, 179
optional, Learn 216, Check 38, Practice 23, Troubleshoot 36, Prove 7, and zero
unmapped activities.

## Migration and progress contract

Migration `0060_network_linux_cloud_practical_upgrade` is schema-free and
reversible. Upgrade requires the complete set of seven target lab/activity
pairs and the two Week 21 video rows before changing anything; a partial
canonical state fails before mutation. Completely unseeded databases remain
safe for the subsequent canonical seed.

Downgrade restores the exact 0059 lab payloads, roles, terminal profile names,
and Week 21 required flags. Week 12 remains a Troubleshoot case because its
structured choice mechanics do not meet the independent-performance Prove bar.
Upgrade, downgrade, re-upgrade, and repeated seed do
not replace target rows. Existing LabRuns, CLI attempts, video completion,
student XP/rank data, and activity IDs remain attached to their original
records.

Fresh-seed validation also exposed a pre-existing LabTemplate identity drift:
fresh databases assigned IDs 19–24 differently from the production lineage.
The canonical seed now supplies the historical IDs 19–25 explicitly, allowing
fresh and historical 0060 databases to converge without changing production
identities.

Repeat-seed validation exposed a second pre-existing issue: the base seed and
Week 1–4 retirement pass still treated LabTemplate IDs 1 and 2 as their old
early-course labs after those identities had become the Week 9 and Week 8
practicals. Re-seeding could therefore regress ID 1, delete/recreate its Week 9
activity, and create an obsolete network template; it could also recreate the
Week 8 activity. Base seeding now prefers IDs 1–4 over stale titles, preserves
evolved structured/evidence templates, and restricts retirement to templates
that still belong to Weeks 1–4.

## Future migration maintenance note

Revision 0060 imports its upgrade and downgrade functions from mutable
application service code. This is safe enough for the current branch because
the imported 4C.2 definitions and the exact 0059 restoration payload are
covered by a pinned historical-lineage upgrade/downgrade/re-upgrade test, and
the seed entrypoint applies the 4C.2 synchronization only when the database is
exactly at revision 0060. Current application code run against a database
intentionally pinned at 0059 is also tested not to inject 0060 definitions.

Future migration authors must not assume that a fresh database upgraded
directly through 0061 or later will receive 4C.2 data from the seed gate. Before
adding the next revision they must either freeze the 0060-owned constants and
restore payload in migration-stable code, or deliberately carry the 4C.2
canonicalization forward in the new revision/seed gate. They must preserve the
same LabTemplate and TrainingWeekActivity identities and must not make the 0060
downgrade depend on future-mutated definitions.

The permanent regression is the pinned real-lineage cycle: build the historical
database through the pinned 0059 sources, prove current seeding at 0059 is a
no-op for 0060 content, upgrade 0059 → 0060, downgrade 0060 → 0059, then
re-upgrade 0059 → 0060 while checking target identities, progress, quiz/role
records, requirement flags, and fresh-install convergence.
