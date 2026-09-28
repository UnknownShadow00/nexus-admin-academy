# Nexus V2 Phase 3A — beginner A+ foundation, Stages 1–3

Status: authoring, automated validation, and human editorial approval complete for Stages 1–3. This is a new versioned Nexus V2 path, not a conversion of legacy Weeks or of the existing A+ exam modules. Production content loading remains a separate, explicitly gated operation.

## Path and learning objectives

The stored certification is `nexus_beginner_aplus`, version `nexus_beginner_aplus_v1`. The three module keys are `module.nexus.beginner.stage1`, `.stage2`, and `.stage3`. Objectives `B1.1`–`B3.3` are Nexus teaching objectives, not a claim that these are official CompTIA exam objective numbers.

| Stage | What the beginner should be able to do | Groups and required interaction | Grouped checkpoints |
| --- | --- | --- | --- |
| Stage 1 — What Is IT? | Name common support areas, describe a technician's job, choose an honest safe action | What IT supports → matching; Support work → ordering; Safe thinking → safe action | Three five-question checks: two Quick Checks and a final module checkpoint |
| Stage 2 — Computer Basics | Explain input, processing, memory, storage and output; recognize basic connections; distinguish files, folders and applications | Inside a computer → matching; Connections → image identification; Files and applications → typed answer | Three five-question checks: two Quick Checks and a final module checkpoint |
| Stage 3 — Operating Systems | Explain Windows as an operating system; navigate accounts, files and paths; choose safe Windows upkeep | Desktop → matching; Accounts and files → ordering; Windows care → safe action. Optional `whoami` output recognition previews later command work | Three five-question checks: two Quick Checks and a final module checkpoint |

Each group has a short original Markdown lesson plus a repository-owned SVG teaching card. The diagram is an openable resource with its own stable key. This gives the learner two closely related teaching pieces before one required interaction and one grouped checkpoint. There are no video links in this batch because no verified, suitably introductory video was selected. No playback claims are made. The existing video resource behavior remains external viewing with separate `opened_at` and self-reported `watched_at` evidence.

The versioned source files are `backend/content/certifications/nexus_beginner_aplus.yaml`, `backend/content/curriculum/nexus-beginner-aplus-v1/`, `backend/content/resources/nexus-beginner-aplus-v1.yaml`, `backend/content/interactions/nexus-beginner-aplus-v1.yaml`, and `backend/content/questions/beginner-stage-{1,2,3}.yaml`. Nine local diagrams live in `frontend/public/v2-interactions/`.

| Learning group | Required diagram resource | Required interaction | Five-question checkpoint |
| --- | --- | --- | --- |
| Stage 1: What IT supports | `res.nexus.beginner.s1.supports` | `interaction.nexus.beginner.s1.supports` (matching) | `assess.nexus.beginner.s1.supports` |
| Stage 1: Support work | `res.nexus.beginner.s1.support_work` | `interaction.nexus.beginner.s1.support_work` (ordering) | `assess.nexus.beginner.s1.support_work` |
| Stage 1: Safe thinking | `res.nexus.beginner.s1.safe_thinking` | `interaction.nexus.beginner.s1.safe_thinking` (safe action) | `assess.nexus.beginner.s1.safe_thinking` |
| Stage 2: Inside a computer | `res.nexus.beginner.s2.inside` | `interaction.nexus.beginner.s2.inside` (matching) | `assess.nexus.beginner.s2.inside` |
| Stage 2: Connections | `res.nexus.beginner.s2.connections` | `interaction.nexus.beginner.s2.connections` (image identification) | `assess.nexus.beginner.s2.connections` |
| Stage 2: Files and applications | `res.nexus.beginner.s2.files_apps` | `interaction.nexus.beginner.s2.files_apps` (typed answer) | `assess.nexus.beginner.s2.files_apps` |
| Stage 3: Desktop | `res.nexus.beginner.s3.desktop` | `interaction.nexus.beginner.s3.desktop` (matching) | `assess.nexus.beginner.s3.desktop` |
| Stage 3: Accounts and files | `res.nexus.beginner.s3.accounts_files` | `interaction.nexus.beginner.s3.accounts_files` (ordering) | `assess.nexus.beginner.s3.accounts_files` |
| Stage 3: Windows care | `res.nexus.beginner.s3.care` | `interaction.nexus.beginner.s3.care` (safe action) | `assess.nexus.beginner.s3.care` |

Stage 2 also has optional `res.nexus.beginner.s2.hardware_software_recap`. Stage 3 has optional `interaction.nexus.beginner.s3.whoami_preview` (command/output recognition). Neither is a prerequisite.

All nine checkpoints explicitly set `pass_percent: 80`; the database default remains 70 and published assessments are untouched. Each group has exactly five questions with one defensible answer and an explanation. The three versioned YAML question banks are imported through the existing question importer as draft banks. They have no entries in the production editorial approval manifest, so loading source files alone cannot publish them or mark their answer keys and explanations validated. A future human approval must add an exact-byte hash and question count to that manifest through the existing approval gate.

## Mastery and navigation

For every stage, the required evidence is all three diagram opens, all three trusted interaction passes, and all three trusted checkpoint passes. Passive lesson completion is ignored by the V2 mastery evaluator. The beginner lesson UI removes the Mark lesson complete action and points back to the next evidence-bearing step. A diagram open alone cannot master a stage. The extra Stage 2 hardware/software recap resource and Stage 3 `whoami` preview are optional and do not enter mastery.

`V2_BEGINNER_PATH_ENABLED=true` selects this path for allowlisted V2 pilot learners. The existing `V2_CURRICULUM_ENABLED` master flag and `V2_PILOT_STUDENT_IDS` allowlist still gate all V2 learner routes. With the beginner switch off, these stage modules are hidden and denied; the previous V2 catalog remains as it was. With it on, the entry page shows only Stages 1–3. Stage 2 requires Stage 1 mastery, and Stage 3 requires Stage 2 mastery; direct API calls receive the same prerequisite explanation. No Stage 4–10 cards or content were fabricated.

The learner's `Continue` route finds a missing required resource first, then a required interaction, then the group checkpoint. It skips passive lesson completion for these three stages. The entry page shows the current stage, its purpose, the next action, and the reason a later stage is locked. The path switch is scoped to pilot use and defaults off.

The same beginner version and stage-prerequisite policy protects direct V2 lab detail and new practical starts. A practical from the old V2 version is hidden when the beginner switch is on, including cached URLs. A previously launched run may finish across a path switch only while the learner retains V2 access and its module and assessment remain active. Detail, VM status/access, evidence upload, verification, and submission use the run's recorded student, lab, module, and assessment provenance; supplied module/assessment parameters must match it. A path switch never permits a new start under the old version. Legacy non-V2 lab rules remain unchanged.

Under the beginner switch, verification and submission of a trusted V2 lab run require an `assigned`, `not_started`, or `in_progress` run. A submitted run remains readable as history but cannot be verified or submitted again. A mentor rejection resets the run to `in_progress`, allowing the same trusted run to be corrected and resubmitted.

The shared policy also protects Service Desk attempts. An old V2 assignment cannot create a new attempt after the beginner switch. The assignment list hides it unless an owned, in-progress attempt has a trusted V2 launch marker for the same scenario, mode, module, and assessment. Such a row is `resumable_only`; retrying the assignment URL returns that exact attempt and never creates another. The learner may use the existing attempt's read, event, snapshot, action, hint, and completion routes while V2 access and its active assessment relationship remain valid. After completion, the assignment is hidden again, while the completed attempt remains readable as history under the existing ownership and V2 access rules. A legacy non-V2 Service Desk assignment is unaffected. No Service Desk scenarios or UI were redesigned.

If V2 reused a pre-existing admin assignment, its `assigned_by` value stays intact. Its matching trusted in-progress V2 attempt is likewise shown as resumable and can finish; the old V2 module and assessment query still cannot start a fresh attempt after completion. The assignment's separate legacy authorization remains available under its existing rules.

Local teaching diagrams are allowlisted in `backend/content/assets/v2-interactions.json` with hashes checked against `frontend/public/v2-interactions/` by backend tests. The manifest ships inside the backend-only container, so required resource validation no longer depends on a sibling frontend directory at content-load time.

## Lightweight review

Ten `review-core` questions cover IT, hardware, software, CPU, RAM, storage, files, the operating system, administrator access, and Task Manager. A correctly answered core question receives a next-day review card; a missed core question is due immediately. Both use the existing `FlashcardReview` and `fsrs_service` path. The existing rating scheduler remains unchanged. An enabled beginner pilot sees at most five due cards per request, and `review_due` appears separately from mastery. Review never blocks a stage or revokes mastery.

## Terminology and safety audit

The first appearances expand information technology (IT), central processing unit (CPU), Random Access Memory (RAM), solid-state drive (SSD), operating system (OS), Universal Serial Bus (USB), and High-Definition Multimedia Interface (HDMI). The lessons explain device, application, account, network, browser, help desk, troubleshooting, escalation, file, folder, path, permissions, administrator, File Explorer, Task Manager, installation, restart, shutdown, and update before requiring them in a checkpoint. The optional `whoami` recognition item is introduced in its lesson and requires no command entry.

The Stage 1–3 learner content has no Cisco material and does not require DNS, DHCP, NIC, IP addressing, BIOS/UEFI, domain administration, CLI, MSP, VPN, or registry knowledge. Stage 2 does not ask for connector standards or hardware specifications. Stage 3 mentions macOS and Linux only to explain that Windows is one operating system among several.

Safety checks explicitly say to pause at damaged equipment or possible data loss, never open a power supply, never force a connector, ask before disrupting work, follow workplace permission and update processes, and never claim a change was verified when it was not. The Stage 1 safe-action interaction and checkpoint both test truthful reporting.

## Student journey and loading

The disposable API journey creates a new learner, enables V2 only for that learner, and loads the content in an in-memory SQLite database. It verifies the repository approval manifest against exact bank bytes and confirms the banks are published with validated answer keys and complete explanations in the disposable database. The journey fixture uses a temporary approval manifest only to isolate that flow from repository approval records. The learner opens each required teaching card, passes the native interaction, passes the five-question checkpoint, and reaches Stage 1, then Stage 2, then Stage 3 mastery. It tests an incorrect interaction and a failed checkpoint followed by successful retries; the next stage stays locked until all evidence is satisfied. It also proves the optional recap and command preview are not prerequisites. The journey uses no real student account or production data.

Content files are loaded through the existing `load_module` pipeline; `load_interactions(db, path="content/interactions/nexus-beginner-aplus-v1.yaml")` is a separate explicit pilot operation. There is no new migration. The tests use the 0075 schema models in disposable databases. Production code and database remain at the separately controlled 0073 deployment baseline; this task performs no deploy, Alembic command against production, content load into production, V2 cohort enablement, or student migration.

## Intentionally deferred

Stages 4–10, Windows command practice, detailed ticket workflow, hardware specification memorization, Network+, Security+, Cisco curriculum, Service Desk redesign, and the full Phase 4 visual redesign are outside this batch. Legacy Week 0–8, Today, Progress, video watches, quizzes, Service Desk progression, XP, and the seven current learners remain governed by their existing paths.
