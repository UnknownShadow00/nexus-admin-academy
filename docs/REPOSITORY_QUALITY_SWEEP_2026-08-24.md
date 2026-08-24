# Repository Quality Sweep — 2026-08-24

Scope: read-only architecture and consistency review performed after Phase 4C.2 validation.
No unrelated remediation was authorized or implemented.

## Curriculum consistency

A disposable database was migrated to revision 0060, then run through `seed.py` and
`seed_curriculum.py`. The resulting canonical state was:

- 35 modules and 35 active weeks (0–34);
- 320 activities: 141 required and 179 optional;
- activity types: 4 capstones, 38 guided labs, 79 lessons, 11 networking labs, 38 quizzes,
  13 Service Desk scenarios, and 137 videos;
- roles: Learn 216, Check 38, Practice 23, Troubleshoot 36, Prove 7;
- zero missing content references using each type's actual identity column;
- zero duplicate activity stable IDs;
- zero duplicate `(activity_type, content_ref)` mappings;
- zero duplicate display-order positions within a week.

The repository's curriculum validator returned `valid: true` with no issues. A direct check
also found no required activity hard-gated behind an optional activity and no non-HTTPS or
non-local URL schemes in populated curriculum video/lesson URL fields. External link
availability was not used as a curriculum gate because it is network-dependent; canonical
mapping integrity was validated locally.

No impossible Phase 4C.2 gate, stale target, or hidden activity-count change was found.
Week 21's required Cloud Models video supports its required responsibility-model quiz.

Meaningful existing content concerns:

- Week 23's database title is **Integrated Operations**, while some planning material calls
  it **Integrated Support Operations**. Resolve deliberately in Phase 4C.3 rather than by an
  unrelated title-only edit.
- Week 24 retains three optional environmental/social/governance fallback videos that do not
  support the final-shift goal.
- All four capstones are optional and submission counts as training completion even when the
  capstone run is not passed. The generic renderer does not match Maple & Finch's `stages`,
  `artifacts`, and nested rubric shape.
- The current required Final Support Shift is answer-led, browser-transcript dependent, and
  absent from graduation gating. These are Phase 4C.3 product requirements, not a 4C.2 fix.

## Migration chain

Alembic reports one head: `0060_network_linux_cloud_practical_upgrade`. The reviewed segment
is linear:

`0055 → 0056 → 0057 → 0058 → 0059 → 0060`.

No multiple-head defect was found. The primary chain risk is mutable-code coupling:
revisions 0056–0060 import application sync functions. A future edit can therefore alter an
old migration's behavior. Revision 0058 also has a deliberately destructive downgrade for
phase-owned Service Desk history. Revisions 0059/0060 are safer today because their exact
cycle and historical preservation are tested, but they are not immutable by construction.

Future migrations should freeze their own payloads, preflight exact target sets, preserve
permanent identities/history, and test fresh versus historical convergence. Do not rewrite
the existing chain without a separately reviewed migration strategy.

## Seed architecture

- migrations on an empty database create schema but data sync functions can skip because
  seed records do not yet exist;
- `seed.py` creates foundation data and `seed_curriculum.py` creates/synchronizes curriculum;
- historical populated databases receive each migration's in-place data transformation;
- repeat seed is designed to converge, but internal commits mean the overall run is not one
  atomic transaction;
- Phase 4C.2 sync is guarded by exact revision 0060, so a future head must carry forward the
  4C.2 definition deliberately or a fresh install can diverge from a historical upgrade.

The durable rules are documented in `docs/SEED_MIGRATION_INVARIANTS.md`.

## Highest-value test gaps

### P0

1. **Future-head fresh/historical convergence gate.** When 0061 is introduced, prove a fresh
   migrate+seed and historical 0060→0061 upgrade produce the same 4C.2+4C.3 canonical state.
2. **Final-shift trust and graduation gate.** Before enabling a mandatory Prove, prove exact
   student/template/rubric ownership and reject failed, incomplete, unrelated, old-version,
   or cross-student runs.
3. **Final-shift server authority.** Reject client-forged score, evidence, transcript, action,
   verification, and completion claims.

### P1

1. Capstone contract tests should align payload rendering, submitted versus passed semantics,
   mentor review behavior, and training completion.
2. Seed fault-injection should demonstrate safe recovery after a sync function commits and a
   later sync fails.
3. Permanent migration tests should cover the mutable 0056–0058 lineage and learner-history
   preservation, matching the quality now present for 0059/0060.
4. A full-curriculum validator should continuously check reference resolution, stable/order
   uniqueness, required hard prerequisites, and learning-role vocabulary at the current head.

### P2

1. Add stale/fallback Week 24 content assertions when Phase 4C.3 intentionally replaces or
   retains those videos.
2. Add accessibility and 375×812 overflow coverage for the generic capstone screen if it
   remains student-facing.

## Meaningful technical debt

- mutable application imports make historical migration behavior dependent on future code;
- phase sync functions commit internally, preventing whole-seed transactional rollback;
- capstone submission/completion/pass semantics are inconsistent and there is no complete
  reviewer workflow;
- the capstone UI assumes a data shape not shared by Maple & Finch;
- promotion-gate dispatch can ignore unsupported gate types, so a future `required_lab`
  condition needs an explicit fail-closed evaluator and tests;
- the current structured lab trusts exact client transcript strings and is unsuitable for a
  graduation assessment;
- existing final-role awards must remain append-only when the future final-shift gate lands.

No Critical/High issue directly threatening the Phase 4C.2 fixes was found, so no unrelated
code was changed.
