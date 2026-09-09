# Nexus Core Wave 3: beginner lesson quality and reliable notes

## Initial lesson findings

The legacy `LessonPage` rendered the summary before objectives, used a generic “Ready to move on?” prompt, and did not catch completion failures. Notes waited 1.5 seconds before saving, cancelled that timer on unmount, hid the Saved label after two seconds, showed no error/retry state, and had neither a local draft nor stale-write protection. Reviewed seed content also taught SFC before DISM while its quiz expected DISM before SFC; APIPA and ping copy sometimes stated a cause more strongly than the evidence supported. Selected lessons contained useful facts but usually began with branching rules rather than a system picture and did not consistently supply a worked evidence chain.

Regression checks now cover lesson structure, all seven presentation contracts, evidence language, SFC/DISM alignment, internal-label leakage, note scoping/conflict behavior, completion failure/retry, rapid edits/navigation, local draft restoration, origin-preserving next activity, mobile overflow, and browser fault injection.

## Lesson template

The exact reusable order is:

1. **WHAT YOU’LL LEARN** — objectives before all teaching content.
2. **WHY THIS MATTERS** — short workplace purpose when reviewed metadata exists.
3. **CORE IDEA / MENTAL MODEL** — a responsive text flow.
4. **CORE LESSON** — existing instructional body, preserved as the graceful fallback.
5. **WORKED EXAMPLE** — symptom → check → observation → suggests → does not prove → next check.
6. **WHAT THE EVIDENCE MEANS** — bounded interpretation.
7. **QUICK UNDERSTANDING PROMPT / NEXT PRACTICE** — prompt and real linked practice when available.
8. **READY TO FINISH?** — lesson-specific readiness plus the explicit completion action.
9. **NEXT ACTIVITY** — the next required lesson or quiz after server confirmation.

Unknown legacy lessons keep their objectives-first body and derive readiness from existing outcomes. No schema or content migration is required. Reviewed legacy text corrections are also applied at read time so already-stored content is safe without a content reload.

## Selected lesson table

| Lesson/category | Old problem | Change made | Mental model | Worked example | Readiness statement | Remaining editorial issue |
| --- | --- | --- | --- | --- | --- | --- |
| Anatomy of a Good Ticket — support/ticket | Facts and practice existed, but no explicit evidence boundary or completion criteria | Added workplace purpose, structured ticket evidence example, prompt, and tailored readiness | symptom → checks/observations → safe action → verification → handoff | One-laptop network report narrowed without calling DNS down | Separate internal/user copy; record the evidence chain; avoid unverified causes | A later editorial pass can shorten duplicated job-purpose prose |
| Storage: Symptoms Before Specs — hardware | Symptom rules preceded a beginner component/evidence picture | Added data-safety-first purpose and evidence-before-replacement example | component → role → symptom → evidence → protect data | Slow, clicking HDD plus health warning; stop write-heavy work and protect data | Explain storage role; connect symptoms; gather evidence before replacement | A labeled PC component asset could supplement, not replace, this flow |
| The Client-Side Network Triage Tree — IPv4/DHCP/APIPA | APIPA and ping branches overstated causal certainty | Added layered network model and corrected seed/read-time language | device → local IP config → gateway → DNS → remote service | One APIPA workstation compared with a working neighbor | Explain DHCP; recognize APIPA; choose a next check without naming an unsupported cause | IPv4/subnetting detail remains in its later module |
| Startup Failures and Recovery Options — Windows | Recovery branches appeared before a troubleshooting picture | Added least-disruptive repair model and Safe Mode evidence example | symptom → stage evidence → supported repair → verification | Normal boot fails after driver change; Safe Mode works; inspect/rollback/verify | Locate stage; use Safe Mode as evidence; verify low-risk recovery | Other Windows lessons still need individual examples in a future editorial pass |
| Network Printing Without Tears — printing | Strong factual path, but ping and destination evidence were not explicitly bounded | Added print-path model and stale-port worked example | app → queue/spooler → destination → network → printer | Queue targets old IP after address change; corroborate ping and verify service | Trace path; compare destination; check before reinstalling | A future annotated queue/port screenshot would be useful |
| Account Lifecycle Support — security/identity | Procedures assumed the learner already separated identity from authorization | Added identity/authorization purpose, model, and urgent-reset example | request → verified identity → authorization → least privilege → audit evidence | Caller cannot pass approved verification; pause/escalate despite urgency | Separate identity/authorization; pause unsafe work; record auditable action | Advanced IAM/SSO/SAML/PAM/JIT/MDM/DLP material should remain reference or become a later split |
| Meet the Command Line — command line | Definition existed, but the lesson still privileged a command list and said output “proves” | Added terminal anatomy, read-only-first framing, and one `ipconfig` interpretation | terminal → prompt → command → output → interpretation | Read IPv4/gateway; state what those fields do and do not establish | Define terminal/prompt; separate command/output; interpret before changing | Full command reference remains secondary as intended |

## Mental models

Seven responsive, text-native flows were added. They require no decorative assets, remain readable at 390px, and cover ticket evidence, hardware evidence, layered networking, Windows repair, printing, identity, and terminal interpretation.

## Worked examples

Each reviewed lesson now uses the same evidence sequence: **symptom → technician check → observation → what it suggests → what it does not prove → next check**. The examples are workplace cases, not additional fact paragraphs or exam-only prompts.

## Evidence wording

- APIPA now means normal DHCP configuration was not obtained; it does not identify why.
- Failed ping now means reachability is not confirmed; ICMP blocking and corroborating checks are explicit.
- Command output provides precise evidence for displayed fields; it does not prove every dependent service works.
- Ticket, printer, Windows, hardware, and identity examples distinguish observation from suspected cause.

## SFC/DISM

Before, the Command-Line Diagnostics lesson and outcome said **SFC → DISM**, while the question, correct option B, and explanation said **DISM → SFC**. After, fresh seed text, existing stored lesson read-time text, outcomes, question, answer, and explanation all agree on **DISM `/RestoreHealth` → SFC `/scannow`**. The targeted content test verifies all four surfaces.

## Completion readiness

Completion remains a button action. The learner sees “Ready to finish this lesson?”, three lesson-specific abilities, and: “This records that you finished the lesson. Quizzes and practical work provide separate evidence of understanding.” After server success, the page says “Lesson completion saved.” and links the actual next required lesson or quiz while retaining module origin.

## Completion failure

Previously the request rejection escaped without useful local recovery. Now the page stays open, keeps local completion false, shows “We couldn’t save your lesson completion.” and a **Try again** button. Browser fault injection verified rejection then successful retry.

## Notes

Notes remain scoped by the existing `(student_id, lesson_id)` unique key. The client now displays **Saving…**, **Saved**, or **Couldn’t save**, stores an unsaved draft under learner+lesson local storage until server confirmation, flushes before the lesson’s intentional navigation links and on unmount/pagehide where possible, and provides retry. Saves are serialized so two rapid edits send the newest text; `base_content` optimistic concurrency returns 409 rather than overwriting a newer server version. Tests cover immediate navigation, refresh/local restore, failure, retry, rapid edits, student isolation, and stale writes.

## Internal content leakage

Learner-visible “grading anchor”, `safe_fix`, and `root_cause` wording was removed from reviewed legacy lesson/quiz copy. Internal rubric structures remain available to grading/editorial code and are not rendered by the lesson template. A content check guards the reviewed Phase A/B learner strings.

## Mobile

The 390×844 browser flow passed with objectives visible, note textarea editable, completion action reachable, responsive mental-model wrapping, and no horizontal document overflow. The full-page screenshot was visually inspected.

## Screenshots

- `docs/core-wave3/screenshots/lesson-top-objectives-purpose.png`
- `docs/core-wave3/screenshots/mental-model-worked-example.png`
- `docs/core-wave3/screenshots/note-saving.png`
- `docs/core-wave3/screenshots/note-saved.png`
- `docs/core-wave3/screenshots/note-save-error.png`
- `docs/core-wave3/screenshots/completion-readiness.png`
- `docs/core-wave3/screenshots/completion-success-next-activity.png`
- `docs/core-wave3/screenshots/completion-save-error.png`
- `docs/core-wave3/screenshots/mobile-390-lesson.png`

All screenshots use disposable loopback learners and local data.

## Tests

- Focused backend lesson/notes/training/prerequisite/quiz: **58 passed**.
- Full Core frontend: **74 passed** across 21 files.
- Wave 3 disposable browser: **3 passed**.
- Core Wave 1 truth browser: **4 passed**.
- Core Wave 2 beginner-path browser: **4 passed**.
- Service Desk/shared backend integrity subset: **31 passed**.
- Full backend diagnostic: **1,181 passed, 9 unrelated baseline/environment failures**. Two require the intentionally absent production `backend/nexus.db`; six assert historical migration fixture totals from another phase; one V2 admin-auth case lacks its admin environment. None touches Wave 3 files or failed in the focused contracts.
- Vite production build, Ruff, compileall, scoped Ruff/Prettier formatting, and whitespace checks passed. Core has no ESLint dependency/script, so no valid Core lint command exists.
- `pip-audit`: no known vulnerabilities. Unchanged frontend lockfile: 1 low, 1 moderate, 1 high advisory.

## Git

Dedicated child branch `fix/core-wave3-lessons`, based on Wave 2 commit `29aea87`. Logical implementation and evidence commits are listed in the final handoff. Nothing was pushed or merged.

## Editorial backlog

- Split or progressively disclose the later identity survey that combines MFA, ACLs, SSO/SAML, JIT/PAM, IAM, MDM, and DLP.
- Split or progressively disclose the later Linux survey that combines packages, privilege, processes, storage, and networking.
- Author a labeled PC component diagram, annotated printer destination screenshot, and annotated `ipconfig` output if approved source assets become available.
- Extend the reviewed presentation metadata lesson-by-lesson; do not mechanically rewrite the remaining curriculum.

## Deferred Core Wave 4

- practice vs assessment separation
- retry/answer exposure policy
- stable assessment presentation
- targeted remediation
- assessment feedback quality

## Production safety

Production was not accessed or mutated. The supplied production state therefore remains schema `0064_v2_ai_grading_infrastructure`, V2 OFF, and no pilot enrollment. There was no deployment, migration, production content load, enrollment, VM/Proxmox work, Service Desk P1 continuation, push, or merge to main.
