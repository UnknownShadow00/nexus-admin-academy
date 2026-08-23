# Microsoft Workplace Curriculum (Phase 4B.1)

Status: Phase 4B.1 built on `feature/microsoft-workplace-core`, not merged,
not deployed. Covers the first content slice of the previously-empty
`stage.microsoft_workplace` Stage ("Microsoft 365, Entra & Endpoint
Management"). Intune/Autopilot/device-lifecycle/MDM content is explicitly
deferred to Phase 4B.2 -- see "Deferred to Phase 4B.2" below.

## Scope

Five modules, new `week_number` 25-29 (existing 0-24 never renumbered):

1. **Microsoft 365 Support Foundations** (week 25) -- tenant, licensing at
   technician depth, admin centers, how M365 services relate to one Entra
   identity.
2. **Entra Users, Groups & Access** (week 26) -- Entra user/group
   administration, account state, sign-in log evidence, MFA-reset under
   identity verification. Built on the existing Lesson 58 content, moved
   here (see "Existing-content reuse" below).
3. **Sign-In & MFA Troubleshooting** (week 27) -- Conditional Access
   interpretation, current authentication-method guidance, SSPR, diagnostic
   order for "can't sign in" tickets. This module's quiz is the graduation
   gate quiz for this stage.
4. **Exchange Online & Outlook Support** (week 28) -- Full Access vs Send As
   vs Send on Behalf, distribution groups vs M365 Groups, Outlook client vs
   server-side diagnosis.
5. **Teams, OneDrive & SharePoint Support** (week 29) -- Teams client/device
   permission issues, OneDrive sync failures and Known Folder Move,
   SharePoint permission-vs-sync-failure diagnosis. Ends with the stage's
   integrated capstone.

## Current official sources (verified 2026-08-23)

- Microsoft Entra sign-in logs and diagnostics: Monitoring & health ->
  Sign-in logs; Authentication Details tab shows the policy chain and exact
  failure reason; a Sign-in diagnostic tool gives root cause + remediation.
  ([Microsoft Learn](https://learn.microsoft.com/en-us/entra/identity/monitoring-health/howto-use-sign-in-diagnostics))
- **Passkeys become the default Entra ID authentication method starting
  September 1, 2026** -- SMS/voice-enrolled users are auto-prompted to
  register a passkey at next MFA. Microsoft-hosted SMS/voice delivery
  retires February 1, 2027 (third-party telecom still selectable).
  ([Microsoft Security Blog](https://www.microsoft.com/en-us/security/blog/2026/07/13/microsoft-entra-id-security-updates-passkeys-are-the-default-authentication-method-in-entra-id/),
  [Entra blog](https://techcommunity.microsoft.com/blog/microsoft-entra-blog/microsoft-entra-id-security-updates-what-organizations-need-to-do-now/4522024))
- **SSPR requires an explicitly registered authentication method starting
  November 9, 2026**, with a registration-nudge campaign from October 5,
  2026. ([Petri](https://petri.com/microsoft-entra-id-registered-authentication-methods/),
  [Merill Message Center archive](https://mc.merill.net/message/MC1325414))
- Exchange Online shared mailbox permissions: Full Access alone cannot
  send; Send As makes mail appear to come from the mailbox; Send on Behalf
  shows "User on behalf of Mailbox" and can only be granted via
  `Set-Mailbox -GrantSendonBehalf` (not in the EAC).
  ([Microsoft Learn: shared mailboxes](https://learn.microsoft.com/en-us/exchange/collaboration-exo/shared-mailboxes),
  [Can't send with Full Access](https://learn.microsoft.com/en-us/troubleshoot/exchange/mailflow/cannot-send-email-with-full-access))
- OneDrive/SharePoint sync failures: mostly path-length/unsupported
  characters/storage, Known Folder Move confusion, and permission loss at
  the site/library level presenting as a sync failure.
  ([Microsoft Learn: resolve OneDrive sync issues](https://learn.microsoft.com/en-us/troubleshoot/sharepoint/sync/troubleshoot-sync-issues))

**Volatile areas**: exact admin-center click paths, and the passkey/SSPR
rollout dates above, will drift. Lessons are written around *what a
technician is trying to determine and where the evidence lives*, not
click-by-click UI paths, so minor Microsoft UI changes should not invalidate
them. Re-verify the 2026-2027 authentication-method rollout dates before
reusing this content past mid-2027.

## Minnesota job-market rationale

Real Minneapolis/St. Paul Help Desk, Desktop Support, and IT Support
listings (Indeed/Glassdoor/ZipRecruiter, checked 2026-08-23) confirmed --
not merely assumed -- that Microsoft 365 (Teams/Outlook/OneDrive/
SharePoint/Exchange Online) support, Entra ID (Azure AD) account/MFA/
permission work, and Intune are explicitly listed requirements at $17.50-
$72/hr depending on level. No evidence was found to expand scope beyond
what Phase 4B.1/4B.2 already plan (no signal that deep Exchange
administration, hybrid federation, or Defender administration are entry-
level expectations for these roles).

## Existing-content reuse

Audited existing Nexus content for Azure AD/Entra/M365/MFA/Outlook/
Exchange/Teams/OneDrive/SharePoint/identity/cloud/authentication/phishing/
lockout before writing anything new.

| Item | Classification | Action |
|---|---|---|
| `mfa-reset` Service Desk scenario ("Approval prompts go to an old phone"), `starter-support` pack, legacy week 1 | **KEEP WHERE IT IS** | Read in full: generic, beginner, product-agnostic MFA re-registration ticket. No overlap with the new, more advanced, Entra-specific scenarios. |
| Lesson 58 "Entra ID: Cloud Identity Administration" | **MOVE** | Was at week 21 (`module.cloud.identity`, 9 weeks after Identity & Access and after where the M365 stage sits). Already covered Entra users/groups, account state, sign-in-log-first diagnosis, MFA-reset with identity verification, and hybrid/Entra Connect sync at a strong technician level. Moved to week 26 (`module.m365.entra_access`) rather than duplicated. |
| Guided lab "Route the Cloud Identity Ticket" (LabTemplate 19) | **MOVE + trim** | Moved from week 21 to week 26, retitled "Investigate the Entra Identity Ticket." Its cloud-responsibility/IaaS question (out of scope for an identity module) was dropped in favor of a new group-based-access question; its two Entra-relevant questions were kept unchanged. |
| Quiz 23 "Cloud Concepts and Entra ID" | **KEEP AS-IS** | Left at week 21 with its existing questions untouched (including the Entra-adjacent ones) rather than split -- splitting a quiz with live `QuizAttempt` history for a handful of overlapping review questions was not worth the risk. New M365 modules got their own fresh gate-quiz instead. |
| Lesson 57, videos 53-56 (general cloud concepts/virtualization/cloud models), video 132 "Cloud Productivity Tools" | **KEEP WHERE IT IS** | Genuinely general cloud-computing literacy (provider-agnostic), appropriate for the later Cloud & Infrastructure Foundations stage; no real overlap with M365-specific technician skills. `module.cloud.identity`'s title was updated to "Cloud Computing Foundations" since it no longer teaches identity content. |

## Final module structure

See "Scope" above. Module count: 25 -> 30. Stage count unchanged (11) --
`stage.microsoft_workplace` was already reserved by Phase 4A.1.

## Depth classification

**MUST PERFORM**: locate/administer a user in Entra; distinguish disabled/
locked/authentication-method problems; read sign-in-log and Conditional
Access evidence; verify identity before any MFA/password reset; recognize
and escalate a suspicious MFA event instead of resetting it; distinguish
Full Access from Send As/Send on Behalf; separate an Outlook client problem
from a server-side mailbox problem; diagnose OneDrive sync failures
including Known Folder Move; distinguish a SharePoint permission failure
from a sync-engine failure; document and escalate correctly.

**WORKING KNOWLEDGE**: M365 licensing model at a level sufficient to
recognize "no license assigned" as a cause; distribution groups vs M365
Groups; hybrid identity/Entra Connect sync direction awareness; Autodiscover
awareness; current (2026) authentication-method guidance (Authenticator/
passkey default, SSPR registration requirement).

**RECOGNIZE only, intentionally excluded from depth**: deep Exchange
transport architecture; hybrid Exchange/federation; advanced Conditional
Access engineering; PowerShell/Graph automation; advanced compliance/
eDiscovery; Teams voice architecture; Defender/Sentinel administration.
None of these were added -- this list documents what was deliberately left
out, not what exists elsewhere in the curriculum.

## Practical environment strategy

No live/licensed Microsoft 365 tenant is assumed. Two levels were actually
used, and a third was found infeasible for this phase:

- **Level A -- live Nexus simulation** (server-graded): used for the two
  Entra/account-state tickets, which reuse the existing `directory.*`
  evidence vocabulary in `service_desk_objectives.py`
  (`inspect_account`, `reset_mfa`, `verify_identity`, `enable_account`,
  `record_diagnosis`, `test_primary_auth`) -- the same tooling `mfa-reset`,
  `locked-user-account`, and `password-reset` already use.
- **Level B -- guided evidence-interpretation exercises**: used for
  Exchange mailbox permissions, Outlook connectivity, OneDrive sync,
  SharePoint access, and the suspicious-MFA scenario, via the same
  question-based `guided_lab` mechanism already proven by "Route the Cloud
  Identity Ticket" (`success_criteria.questions`, single-choice with
  explanations).
- **Level C -- real tenant exercises**: intentionally not built. Documented
  here as a future opportunity if a training tenant is provisioned; would
  primarily benefit the Exchange/OneDrive/SharePoint/Teams topics that
  currently have no simulation-tool surface (see next section).

### Why Level A stopped at two tickets, not seven

The original design targeted 5-8 live Service Desk tickets across all five
topics. During implementation, `service_desk_objectives.py`'s grading
vocabulary was found to have **no `mailbox.*`/`onedrive.*`/`sharepoint.*`
evidence actions**, and **no "forbidden action" primitive** to penalize an
unsafe shortcut (e.g. resetting MFA on a suspicious prompt instead of
escalating). Building tickets that reference tool actions the simulator
cannot evaluate would produce content that looks graded but isn't. Rather
than do that:

- The two tickets that map cleanly onto the existing `directory.*`
  vocabulary (Entra authentication-method troubleshooting, sign-in/
  Conditional Access investigation) were built as live, server-graded
  Service Desk scenarios.
- Suspicious MFA, shared-mailbox Send As, Outlook connectivity, OneDrive
  sync, and SharePoint access became Level B guided-lab exercises instead.
  For suspicious MFA specifically, this is arguably the *better* fit
  regardless of the tooling gap: the core skill is judgment ("recognize
  this, do not act, escalate correctly"), which a reasoning exercise
  targets more directly than free-form tool interaction would anyway.

Building `mailbox.*`/`onedrive.*`/`sharepoint.*` simulation tool support and
a forbidden-action grading primitive is real platform engineering, not
content authoring -- it belongs in a future phase if live-simulation depth
is wanted for those topics.

## Service Desk scenarios

| stable_key | Type | Week | Difficulty | Root skill |
|---|---|---|---|---|
| `m365-entra-auth-method` | Live ticket | 26 | 2 | Re-register a broken authentication method (not a full reset) when the user has other working registered methods -- least-disruptive fix judgment, distinct from the existing `mfa-reset`'s total-loss scenario. |
| `m365-signin-conditional-access` | Live ticket | 27 | 2 | Distinguish a Conditional Access risk-block from a credential failure using sign-in log evidence; verify identity before re-enabling. |
| Suspicious MFA prompt | Guided lab (troubleshoot role) | 27 | 2 | Recognize account-takeover risk; escalate with evidence instead of resetting and closing. |
| Mailbox permission ticket | Guided lab (troubleshoot role) | 28 | 2 | Full Access vs Send As/Send on Behalf; least-privilege mailbox grants. |
| Collaboration ticket (OneDrive/SharePoint) | Guided lab (troubleshoot role) | 29 | 2 | Wrong-account sync, Known Folder Move, SharePoint permission vs. sync failure. |
| "Microsoft Workplace Support Shift" | Capstone (prove role) | 29 | -- | Integrated: prioritize, investigate, resolve/escalate, verify, document across a sign-in issue, a mailbox permission issue, an OneDrive sync issue, and a suspicious MFA event in one shift. |

The `microsoft-workplace` `ServiceDeskPack` (`service_desk_progression.py`)
covers only the two live tickets (`required_week=26`, chained after
`advanced-troubleshooting`, `required_prior_passes=3`).

## Security, cross-cutting

- **Password/MFA reset**: every account-state change in this stage's live
  tickets requires identity verification first (reusing the existing
  `_account_process` pattern's `approved-identity-check` objective) --
  same discipline as `mfa-reset`/`password-reset`/`locked-user-account`.
- **Suspicious MFA**: explicitly taught and graded (via the guided lab) as
  "investigate and escalate," not "reset and close." The lesson content
  states this is an account-takeover indicator (MFA fatigue/push-bombing),
  not routine support work.
- **Mailbox permissions**: lesson and guided lab both teach granting only
  what a request's stated task and authorization justify, not the broadest
  convenient permission (Full Access + Send As "just in case").
- **Least privilege in Entra**: group-based access preferred over
  individual grants, carried over from the existing AD-safety framing.

## Integrated assessment

"Microsoft Workplace Support Shift" (capstone, week 29): four unrelated
requests (blocked sign-in, mailbox permission complaint, OneDrive sync
failure, suspicious MFA prompt) in one shift. Student must prioritize the
suspicious-MFA and blocked-sign-in items appropriately, investigate before
acting on all four, avoid over-granting/over-resetting, and leave an
evidence-based note or escalation reason for each. Scoped to this stage's
content -- not the final Nexus capstone.

## Dual progression systems

**System A** (`TrainingWeek.display_order`, Learning Path/"Today"): the five
new weeks get `display_order` 13-17, sitting between Identity & Access
(10-12) and Network Administration & Infrastructure (now 18-20, shifted
+5 from their post-0056 13-15). Only `TrainingWeek.display_order` moves for
the 12 existing rows in that shift; `week_number` is never touched on any
existing row.

**System B** (legacy, `progression_service.py` / `service_desk_progression.py`):
was hardcoded to weeks 0-24 in three places that all had to be reconciled,
not just made harmless:

1. `progression_service.MODULE_WEEKS` -- extended with `MOD-025`..`MOD-029`
   -> 25-29 (new legacy `Module` rows, one per new week, same pattern as
   `MOD-000`..`MOD-024`).
2. `derive_current_week`'s `for week in range(25)` -- changed to
   `range(max(MODULE_WEEKS.values()) + 1)`, so it derives the applicable
   range from the curriculum that actually exists rather than a hardcoded
   ceiling. This also fixes `service_desk_progression.py`'s
   `curriculum_unlocked_keys` mechanism, which was silently capped by the
   same assumption.
3. **The `PromotionGate` rows for the graduating role** (`Junior
   Infrastructure Administrator`, rank 6) -- this is the part that actually
   matters for graduation, not the range fix by itself. Extended:
   - `min_completed_lessons.module_codes` += `MOD-025`..`MOD-029`.
   - a second `required_quiz` gate row, `{"week": 27}` (the Sign-In & MFA
     module's quiz), alongside the existing `{"week": 23}` row.
   - a `min_service_desk_passes` gate row, `{"pack_key":
     "microsoft-workplace", "min_passed": 2}`.

   Without step 3, a student could reach every existing gate and graduate
   without ever touching the Microsoft stage, purely because the legacy
   gate system was unaware five new required modules existed -- range
   fixes alone do not prevent that; the gate rows are what actually
   requires the content.

**Known, accepted divergence**: System A's Learning Path shows the M365
stage right after Identity & Access (early). System B's *sequential* week
(which gates tickets/labs/capstones and drives the new pack) only reaches
week 25+ after a student clears legacy weeks 0-24, because
`derive_current_week` walks week_number in numeric order. This means M365
*lessons and quizzes* are reachable early via the Learning Path (System A
doesn't gate on `require_week_reached`), but the *live tickets* (Level A,
gated through the new pack) only unlock once a student's System B position
reaches week 26 -- i.e., after finishing the rest of the numbered
curriculum. This is the same class of divergence Phase 4A.1 already
accepted for Identity vs. Network Administration (System A display order
and System B rank order already disagreed there); it is not a new kind of
inconsistency, and it does not weaken the graduation-completeness fix,
since PromotionGate evaluation checks concrete completion records, not
System B's current-week position.

## Existing students

`StudentRole` is a permanent award record with no re-evaluation logic --
extending `PromotionGate` rows for rank 6 cannot retroactively revoke a
promotion already granted, so:

- **Fresh / before Identity / currently in Identity**: no visible change
  except the M365 stage now appearing (with real content) at its intended
  Learning Path position. No behavior change to their current or completed
  work.
- **Past Identity, not yet graduated** (mid Server/Linux/Cloud/Integrated):
  continues from their current position, unthrown-back. The M365 lessons
  appear in their Learning Path immediately; the M365 tickets and the
  updated graduation gate become reachable once they finish the rest of
  the numbered curriculum (System B's existing sequential behavior,
  unchanged in kind).
- **Already at/near final capstone, not yet promoted to rank 6**: once
  `derive_current_week` clears week 24 (now dynamically extends past it
  instead of stopping there), it correctly proceeds into weeks 25-29 --
  this is the case the `range(25)` fix specifically targets.
- **Already promoted to rank 6 (graduated) before this migration**: their
  `StudentRole` grant is untouched -- no historical completion is revoked.
  The M365 content is visible in their Learning Path like any other
  content (Learning Path is not role-filtered), effectively presenting as
  optional refresher material for them, without any code change required
  to make that so.

## Curriculum counts

| | Before | After |
|---|---|---|
| Total activities | 273 | 288 |
| Required | -- | -- (unchanged split logic; all new required content is Learn/Check/Troubleshoot/Prove as itemized below) |
| Learn (lesson) | 200 | 205 (5 new; Lesson 58 moved, not new) |
| Check (quiz) | 28 | 33 (5 new) |
| Practice (guided_lab, default role) | 33 | 33 (unchanged -- see below) |
| Troubleshoot | 9 | 15 (+2 live tickets, +4 guided labs whose `learning_role` is explicitly overridden to `troubleshoot` since they are diagnostic/evidence-interpretation exercises, not build/practice labs -- this includes the moved "Investigate the Entra Identity Ticket" lab) |
| Prove (capstone) | 3 | 4 (+1, "Microsoft Workplace Support Shift") |
| Stages | 11 | 11 |
| Modules | 25 | 30 |

Total new activities: 16 (Lesson 58 and LabTemplate 19 were moved, not
newly created; the fresh-install path additionally creates them directly
since nothing else creates that content there -- see
`sync_microsoft_workplace_foundations`'s comments).

## Files changed

- `backend/app/services/curriculum_structure.py` -- 5 new `ModuleDefinition`
  rows under `stage.microsoft_workplace`; `module.cloud.identity` retitled;
  Stage description updated.
- `backend/app/services/progression_service.py` -- `MODULE_WEEKS` extended;
  `derive_current_week` range made dynamic.
- `backend/app/services/service_desk_progression.py` -- new
  `microsoft-workplace` `ServiceDeskPack`.
- `backend/app/services/service_desk_objectives.py` -- two new
  `SCENARIO_OBJECTIVES` entries.
- `backend/app/services/training_curriculum_seed.py` -- new
  `sync_microsoft_workplace_foundations`; the `WEEKS_19_22_QUALITY` week-21
  lab spec removed (content moved); `sync_advanced_networking_resequence`
  guarded against re-firing once Phase 4B.1 has run.
- `backend/seed_curriculum.py` -- wires in the new sync call.
- `backend/alembic/versions/0057_microsoft_workplace_foundations.py` --
  new migration (schema-free; pure data), with a full downgrade.
- `backend/tests/test_orientation_seed.py`,
  `backend/tests/test_training_service.py`,
  `backend/tests/test_training_curriculum_realignment.py` -- updated
  hardcoded curriculum-count/lab-count assumptions.
- `docs/MICROSOFT_WORKPLACE_CURRICULUM.md` -- this document.

## Technical debt / follow-ups

- `mailbox.*`/`onedrive.*`/`sharepoint.*` simulation-tool actions and a
  "forbidden action" grading primitive do not exist yet -- needed before
  Exchange/OneDrive/SharePoint topics can become live, server-graded
  tickets instead of guided-lab reasoning exercises.
- No real Microsoft 365 training tenant exists yet (Level C, deferred by
  design for this phase).
- The System A / System B sequential-position divergence (documented above)
  is accepted, not fixed -- a full reconciliation (making System B's rank
  order match System A's display order) would be a materially larger
  change than this phase's "smallest durable reconciliation" scope allowed.

## Deferred to Phase 4B.2

Intune, Windows enrollment, Autopilot, configuration profiles, compliance,
device lifecycle, onboarding/offboarding, mobile/MDM. Also explicitly out
of scope for 4B.1 per the phase brief: real Microsoft tenant integration,
PowerShell/Graph automation depth, advanced Exchange administration,
hybrid Exchange, federation architecture, advanced Conditional Access
engineering, Defender/Sentinel administration, the final competency
engine, portfolio, and the persistent-company capstone.
