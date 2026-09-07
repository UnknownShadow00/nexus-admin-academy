# P0 Beginner Integrity & Operability Sprint — Execution Plan

Branch-only hardening. Production stays schema 0064, V2 OFF, no enrollment, no
deploy/migrate/content-load. All work on `fix/v2-final-pre-pilot-integration`
(or a dedicated child branch).

Execution model: **staged Codex delegation**. Claude plans each wave into a
Codex task spec, delegates via the `codex` skill, reviews output against
acceptance criteria, iterates. `terra-high` for multi-file waves, `sol-medium`
for the grading-core and simulation-engine waves.

Rubric weights are LOCKED: investigation 15 / diagnosis 25 / remediation 30 /
verification 20 / documentation 10. Do not touch `PROCESS_WEIGHTS`.

## Confirmed findings (investigation, this session)

- **Finding A is systemic.** Every curriculum Service Desk scenario YAML in
  `backend/content/service-desk-scenarios/*.yaml` has a single objective
  `predicateType: action_event_occurred` / `actionType: ticket.add_note` and
  **no** `objective_catalog_version`. `service_desk_grading.compute_grade`
  then falls to `process_points = 100 if resolved else 0`, and `resolved`
  needs only one `ticket.add_note`. One note → 100/100 → module credit, even
  when the authored professional outcome is escalation.
- **Grading engine is sound.** `process-v3` and `realism-v1/v2` profiles grade
  I/D/R/V/Doc from the trusted ledger with ordering constraints (investigation
  and diagnosis must precede first repair; verification after last repair).
  Escalation grading normalizes across applicable categories. Do NOT weaken it.
- **Realism content that exists** (full 5-category profiles): INC2501 profile
  redirect, INC2502 Excel crash, INC2503 dead network jack (esc), INC2504
  stale printer port (self-fix), INC2505 share permissions, INC2506 access
  request (esc), INC2507 recurring lockout, INC2508 phishing/containment
  (esc), INC2509 recurring disk full, INC2510 laptop sign-in failure.
- **Wiring** lives in `backend/content/certifications/comptia_aplus.yaml`
  under each module's `assessments:` list (`assessment_role: service_desk`,
  `service_desk_ref: <scenario stable_key>`). `inc2503` already refs the ip-
  config module; `inc2403` refs win-triage (legacy scenario — verify status).
- **Validation gap.** `service_desk_scenario_validation.validate_scenario_definition`
  accepts a lone `ticket.add_note` objective. `validate_runtime_definition`
  explicitly says "Custom scenarios currently have generic ticket-note
  support." No gate requires a process/realism profile for a V2 student
  assessment.
- **Service Desk frontend** is `service-desk-app/apps/web` (Next.js). Launcher
  files: `WorkspaceToolLauncher.tsx`, `ActiveToolPane.tsx`, `ToolsPanel.tsx`,
  `TicketWorkspace.tsx`, `useNexusReturnTarget.ts`,
  `lib/nexus-service-desk-client.ts`. Sim engine:
  `packages/simulation-engine/src/apply-action.ts` (the "does not exist in
  this simulation" string, line 186).

## Section 3 mapping decision (user-approved: Path B)

Bind only where the cert objective genuinely matches; mark the rest
**unavailable** for pilot. No new scenario authoring. Proposed table (Codex
to verify each module's stated objectives in `comptia_aplus.yaml` +
`content/curriculum/.../NN-*.md` before applying):

| V2 module | old scenario ref | new ref / action | reason |
|---|---|---|---|
| core1 ip_configuration | `inc2503` | keep `inc2503` | already realism; office-move connectivity fits IP-config triage |
| core1 printers_mfds | `service_desk.aplus.printers.hr_queue` | → `inc2504` | stale printer port; strongest tutorial fit |
| core1 network_services_troubleshooting | `service_desk.aplus.network.loading_dock_wifi` | → `inc2503` OR unavailable | INC2503 is a wired jack, YAML is Wi-Fi; if it collides with ip_configuration binding, mark unavailable |
| core2 windows_admin_cli_networking | `sd.aplus.windows_admin.project_share_after_vpn` | → `inc2505` | share access after VPN == team-folder permissions |
| core2 threat_malware_response | `sd.aplus.security.suspicious_attachment_endpoint` | → `inc2508` | phishing/credential-compromise containment |
| core2 service_desk_workflow | `curriculum-...-service-desk-01` | → `inc2506` | access needs approval → escalate; authored outcome is escalation |
| core2 identity_endpoint_hardening | `sd.aplus.security.approved_app_standard_user` | → `inc2507` OR unavailable | recurring lockout is identity-adjacent; confirm objective fit, else unavailable |
| core1 hardware_fault_isolation | `service_desk.aplus.hardware.render_shutdown` | **unavailable** | no realism scenario for hardware fault isolation |
| core1 mobile_device_support | `service_desk.aplus.mobile.intermittent_charge_mail_sync` | **unavailable** | no realism scenario for mobile hardware |
| core2 connected_endpoint_mobile_security | `sd.aplus.security.mobile_secure_wifi_profile` | **unavailable** | no realism scenario for mobile Wi-Fi profile security |
| core2 cross_platform_app_cloud_support | `sd.aplus.cross_platform.unlicensed_suite_mac` | **unavailable** | no realism scenario for macOS licensing |
| core2 win-triage | `inc2403` | verify: keep if realism/process-graded, else unavailable | legacy ref — confirm it is not itself note-only |

"Unavailable" = assessment availability resolves false via the Section 2/11
gate (preferred) — not deletion. Legacy note-only YAMLs stay on disk for
non-V2 use but must not yield V2 competency credit.

## Waves

### Wave 0 — Reproduce every finding as a FAILING regression test (mandatory first)
- A: `backend/tests/` — assigning a note-only V2 SD scenario, one
  `ticket.add_note`, close → assert current `passed=True, score=100`; mark
  xfail/￼TODO so it flips to `passed=False` after Wave 2.
- B: backend + `simulation-engine` — for every V2 student-available SD
  assessment, construct its scenario from the published definition and
  execute one real client action; today several raise "does not exist in
  this simulation".
- C: `service-desk-app/tests/e2e` — authenticated Playwright hitting the
  exact launch URL `/service-desk/tickets/<id>?returnTo=...&v2ModuleKey=...&v2AssessmentKey=...`,
  click a suggested tool, assert tool state lost today.
- D: component/e2e — invalid Resolution Note submission clears textarea, no
  visible feedback.
- E: test — student sets status → Resolved before meaningful work; header
  shows RESOLVED while assessment is failed.
- Acceptance: 5 red tests committed, each tied to a finding ID.

### Wave 1 — Section 1 inventory (generated + tested)
- Script/test that emits `| module | assessment key | scenario | catalog
  version | process profile | browser-operable | student-visible |` for every
  `assessment_role=service_desk` row, and asserts the Wave-2 invariant once
  it lands. Output checked into `docs/` and wired to CI.

### Wave 2 — Section 2 + Section 11 gates (HIGHEST PRIORITY) — `sol-medium`
- `service_desk_scenario_validation`: a V2 student-assessment scenario with
  no supported process/realism profile → validation error.
- Hard assertion (unit + CI): no V2 student-available SD assessment may have
  `process_weights: null` or an empty grading category set.
- Assessment availability resolves false when no supported profile (find the
  availability resolver in `v2_curriculum_service.py` / `v2_content_loader`).
- Do NOT fabricate category points. Do NOT auto-convert custom → realism.

### Wave 3 — Section 3 binding — `terra-high`
- Apply the mapping table in `comptia_aplus.yaml`. Return the final table
  with per-row reason. Mark the 4 (+ any that fail verification) unavailable.

### Wave 4 — Section 4 first-three progression — `terra-high`
- Ticket 1 tutorial INC2504; Ticket 2 guided INC2505; Ticket 3 guided
  escalation INC2503 or INC2506 — subject to cert-objective alignment for
  whichever modules are first in the beginner path. Report conflicts.

### Wave 5 — Section 5 + 6 tool launcher + persistent context — `sol-medium`
- Fix searchParams change clearing `activeToolSlug` in the Service Desk web
  app; ticket workspace is authoritative. Integrated tool mode must not ask
  which ticket. Keep legacy standalone `/tools/...` selectors. Playwright on
  the real V2 URL shape.

### Wave 6 — Section 7 + 8 + 9 — `terra-high`
- Note failure UX: preserve textarea, visible typed feedback, no evidence
  leak. Resolved≠Passed: operational status vs learner outcome (PASSED /
  NEEDS ANOTHER ATTEMPT / AWAITING REVIEW / ESCALATED SUCCESSFULLY); one
  unmistakable sentence post-completion. Debrief lies: no "repaired and
  verified" on escalation where verification N/A; never render empty
  PROCESS/What counted; consistent attempts-remaining; category-specific
  failure summary; no answer leak while retries remain.

### Wave 7 — Section 10 leakage — `terra-medium`
- Remove `Local fixture record only`, `Directory and Asset Management remain
  placeholder workspaces`, unresolved-close review instructions from
  student-facing surfaces. Placeholder tools not offered to students.

### Wave 8 — Section 11 + 12 CI gates + beginner Playwright — `terra-high`
- Wire the 14 acceptance gates into CI. Full beginner-path Playwright via the
  real curriculum route (no `/tools/...` shortcut).

### Wave 9 — Full verification + FINAL REPORT
- Backend (disk permitting; 9.1G free — use focused suites + scratch DB per
  `tasks/lessons.md`), grading, V2 curriculum, SD scenario validation,
  assignment availability, anti-gaming matrix, SD shared/sim/web/UI packages,
  authenticated V2 Playwright, frontend build, Ruff, compileall, diff checks.
- Produce the 15-section final report. Confirm production untouched.

## Guardrails (from tasks/lessons.md)
- Never run `alembic`/DB commands without an explicit scratch `DATABASE_URL`;
  confirm the URL in output. `NEXUS_ALLOW_PROD_MIGRATION` stays unset.
- Never `>/dev/null` a command that can mutate unscoped state.
- `backend/nexus.db` IS production — read-only inspection only.
