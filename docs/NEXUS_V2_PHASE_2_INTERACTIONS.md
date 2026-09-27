# Nexus V2 Phase 2: native interactions

## Architecture contract (written before implementation)

Phase 2 adds formative practice alongside the existing V2 quiz, practical,
Service Desk and Explain engines. It does not replace those assessment engines
or change legacy Week 0–8 progression. The existing V2 master switch and pilot
allowlist guard every learner route.

`v2_interaction_definitions` contains immutable authored versions. Identity is
`(interaction_key, version)`; each version has a type, module and optional V2
lesson, title, instructions, display order, required flag, pass threshold,
published/retired state and validated JSON content. Only one version per key
may be published for learners at a time. A new version is a new row; the old
row is retired, never edited in place after attempts exist. Definition deletion
is restricted when attempts refer to it. Authors retire versions instead.

`v2_interaction_attempts` stores one row per submitted answer. It references
the exact definition version and also snapshots the authored definition,
student response, grading result, score, pass decision and timestamp. Retries
insert new rows. No student route updates or deletes an attempt. Student
deletion explicitly removes owned attempts and evidence in one transaction.

The six initial types share a public view, strict submission validator and
deterministic grader. Public views expose only display fields. Answer keys,
accepted text and explanations stay server-side until submission. Matching
uses selectable pairs; image identification uses an owned image with alt text;
ordering uses move controls; command/output shows static output and choices;
typed answers use narrow authored normalization; safe action uses one best
choice. All controls have a keyboard path and textual feedback. New types can
join the type registry without changing the common route or attempt schema.

The only trusted-evidence path is: validated response -> server grade ->
immutable attempt flush -> if passed and required, call the Phase 1
`record_trusted_evidence` helper with the authored requirement and an attempt
reference -> commit. The unique evidence constraint makes repeated passes
idempotent. A response payload cannot provide score, pass, answer key,
evidence fields, or a different version. Module mastery remains derived by
`module_progress` from required `V2EvidenceRequirement` records.

Authoring is a small YAML manifest in `backend/content/interactions/` loaded
explicitly for the V2 pilot. Loading validates every type before publishing,
creates/synchronizes the corresponding interaction evidence requirement, and
rejects attempts to change an already authored version. A new published
version supersedes the prior one. The six demo definitions are beginner IT
examples, not a rewrite of the A+ curriculum. Image assets are repository
owned under the frontend public directory.
Drafting a new version leaves the current published version and its evidence
requirement active. A stable key cannot move to another module across versions.

Retries are unlimited and carry no XP or penalty. A passing attempt satisfies
required interaction evidence once. Optional interactions remain practice and
cannot block module mastery. Feedback is authored and deterministic; the
correct answer is revealed only after submission when the definition allows
it. A single interaction is `not_started`, `in_progress` or `passed`, while
module `mastered` remains a separate server status.

Phase 2 does not include a CMS, AI grading, drag-only controls, OCR, a terminal
simulator, the full V2 visual redesign, production deployment, curriculum
rewriting, or new Network+/Security+ content.

## Pilot authoring and operation

After a development database is upgraded to `0075` and the V2 foundation is
loaded, run `python seed_v2_interactions.py --dry-run` from `backend/` to
validate without writing. Then run `python seed_v2_interactions.py` to load
the six pilot examples. The command is opt-in and is not part of deployment.
The manifest fields are `key`, positive `version`, `type`, `module_key`,
optional `lesson_key`, `title`, `instructions`, `required`, `status`,
`display_order`, `pass_percent`, and type-specific `config`. Every config has
an authored `explanation` and optional `reveal_correct` flag. Choice types
define unique `choices` IDs and a valid `correct_choice_id`; matching defines
unique pair IDs; ordering defines unique step IDs; typed answer defines at
least one accepted answer whose normalized text fits the 500-character learner
limit, plus an optional case sensitivity setting.
The published learner API returns only the display subset of this config.

GET `/api/v2/curriculum/modules/{module_key}/interactions/{interaction_key}`
returns the current published interaction, including its opaque `version_id`.
POST to the same path plus `/submit` with
`{ "version_id": <displayed version_id>, "response": ... }` grades only if
that exact definition is still published for the requested key and module.
A version change returns HTTP 409 and requires a fresh load and answer; the
server never silently grades against newer content. An attempt snapshots the
exact graded version and returns feedback and updated progress.

Progress uses one batched SQL window query for all interactions in a module
or lesson. It returns `attempt_count`, pass state, best score/result and latest
attempt time/result without embedding history. An individual interaction view
adds only the five most recent attempts, newest first. All older attempts
remain in the database as immutable history. A future full-history view would
need a separate paginated endpoint; no such UI is part of Phase 2.
For a currently required interaction, `passed` reflects its trusted evidence
record. A pass earned while an earlier version was optional remains in history
but does not make the newly required activity appear complete.
If an interaction's lesson is hidden, that published interaction has no learner
route, so its loader-owned evidence requirement is ignored until the lesson is
visible again. Standalone Phase 1 requirements and the mastery formula are
unchanged. The learner UI clears prior feedback when any retry is rejected.
The aggregate query still scans a learner's matching attempt rows; a
materialized progress counter is deferred until pilot usage shows a need.
The module and lesson responses list the pilot interactions for navigation.
An interaction version remains stored while attempts refer to it; removing
all new interaction tables on downgrade discards Phase 2 attempts and removes
their associated requirements and trusted evidence so 0074 cannot enforce
unreachable interactions. Unrelated Phase 1 requirements and evidence remain.
Back up Phase 2 records before any rollback after pilot use.
