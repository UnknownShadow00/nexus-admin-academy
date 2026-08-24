# Seed / Migration Invariants

These rules define the curriculum data contract for future migrations and seed changes.
They are especially important after revisions 0056–0060, whose migrations call application
sync functions.

## Current execution paths

### Fresh installation

Alembic creates the schema through the current head. Data migrations may find no canonical
seed rows and therefore skip their transformations. `seed.py` creates foundation records;
`seed_curriculum.py` creates and synchronizes curriculum records. The final data version is
therefore a product of both the migration head and the seed revision gate.

### Historical upgrade

An existing populated database reaches each data migration in order. Revisions 0056–0060
transform existing rows in place. This path must retain learner-owned rows and stable
curriculum identities.

### Repeat seed

Seed functions are intended to converge by stable keys/IDs rather than duplicate records.
Several sync functions commit internally, so the complete seed run is not one transaction.
A failure can leave a partially synchronized database; safe repeatability and target-set
validation are therefore required.

### Future migration

`seed_curriculum.py` currently applies the Phase 4C.2 sync only when Alembic is exactly
`0060_network_linux_cloud_practical_upgrade`. When 0061 exists, future authors must
deliberately carry the 4C.2 canonical state into the future-head path before applying 4C.3.
Otherwise an empty database upgraded directly to 0061 and then seeded could skip 4C.2 even
though a historical database passed through it.

## Required invariants

1. **The Alembic head controls the maximum curriculum definition.** Application code running
   against an older database must not silently inject a future curriculum phase.
2. **Fresh install and historical upgrade converge.** An empty database migrated and seeded
   at revision N must match a populated database upgraded through revision N for canonical
   curriculum definitions and counts.
3. **Stable identities are permanent.** Never recreate or renumber a
   `TrainingWeekActivity.stable_id`, activity ID, `LabTemplate` ID, quiz identity, scenario
   stable key, or other completion target merely to revise its content.
4. **Learner history is append-only unless a separately approved retention policy says
   otherwise.** Migrations and seeds must preserve LabRuns, CLI attempts, Service Desk
   attempts/events/grades, quiz attempts, video watches, XP, current roles, and StudentRole
   awards.
5. **Validate the full target set before mutation.** A missing or unexpected canonical row
   must fail the phase before the first content update, including on databases whose DDL is
   not transactionally rolled back.
6. **Own exact mutations.** Data migrations update only the declared IDs/stable keys and
   assert both the before-state and intended after-state. Do not update broad title, week, or
   type matches.
7. **Downgrades restore frozen prior definitions.** A downgrade must not depend on constants
   that a future application release can mutate. Freeze the before/after payload in the
   migration or an immutable migration-owned module.
8. **Seeds do not reset progress.** Convergence may revise canonical content but must not
   delete, recreate, reassign, or mark complete student-owned records.
9. **Required prerequisites remain satisfiable.** Required activities cannot depend through
   a hard gate on optional, absent, unpublished, or future-version content.
10. **Every curriculum reference resolves.** Validate each activity type against its actual
    identity column (for example, Service Desk `stable_key` and networking CLI string ID),
    not a generic numeric-ID assumption.
11. **Progression gates pin exact assessments.** Gates must include the stable assessment
    identity, student ownership, pass state/score, and grading/rubric version where content
    can evolve. Unrelated activities cannot substitute.
12. **Seed revision guards move forward deliberately.** Adding revision N+1 requires tests
    proving both N definitions and N+1 changes are present after a fresh-head seed, while an
    N-pinned database remains unchanged by N+1-capable code.

## Revisions 0056–0060

- 0056 imports mutable `sync_advanced_networking_resequence`.
- 0057 imports mutable `sync_microsoft_workplace_foundations`; its downgrade removes the
  phase-owned content and restores moved identities.
- 0058 imports mutable endpoint sync code; its downgrade deliberately removes attempts,
  events, grades, and assignments tied to the removed scenarios. That rollback is
  destructive once learners have used those scenarios and must not be treated as an
  ordinary production operation.
- 0059 and 0060 import mutable practical-upgrade sync/restore functions. Their current
  checked-in behavior is covered by historical migration tests, but future edits to those
  functions could change old upgrade/downgrade semantics.

Do not refactor this chain casually. Protect it by freezing future migrations and retaining
tests that reconstruct genuine historical state from pinned source revisions.

## Permanent regression tests

Keep one end-to-end test for every curriculum phase that:

1. reconstructs the real predecessor data definition from a pinned Git revision without
   using `backend/nexus.db` or another developer-local file;
2. upgrades predecessor → phase, downgrades phase → predecessor, and upgrades again;
3. asserts exact canonical counts, target sets, activity roles, and reference resolution;
4. asserts permanent IDs and representative learner histories are unchanged;
5. runs current application seed code against the predecessor revision and proves the future
   phase is not injected;
6. compares an empty fresh-head migrate+seed database with a historical upgrade at the same
   head.

The Phase 4C.2 migration test is the baseline pattern. Future phase tests must extend its
coverage rather than replacing its predecessor reconstruction with mutable local state.
