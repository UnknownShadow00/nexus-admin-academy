# Curriculum Structure

## Decision

Phase 3 uses a **transitional metadata layer**. `TrainingWeek` and
`TrainingWeekActivity` remain the authoritative storage and sequencing records,
while `backend/app/services/curriculum_structure.py` is the single authoritative
mapping from those records to student-facing Stages and Modules.

No Stage or Module database tables were added. Native tables would currently
duplicate the same 25 sequencing containers, require a data migration, and risk
disconnecting completion records from their existing content identities. The
metadata layer gives Phase 4 a safe place to rename or regroup modules while the
existing progression contract remains intact.

## Current model audit

The codebase does not have persisted `StudentTrainingWeekProgress` or
`StudentTrainingActivityProgress` rows. Training progress is derived from the
canonical completion records for each content type: lesson progress, video
watches, quiz attempts, lab runs, CLI attempts, Service Desk attempts, and
capstone runs.

`week_number` is genuinely required today by:

- seed generation and the transitional `TrainingWeek` storage sequence;
- backend prerequisite and promotion rules that calculate the next available
  storage container;
- quiz, lesson, lab, CLI, Service Desk, and capstone compatibility mappings;
- legacy training URLs and tests that protect those URLs;
- administrative seed/validation diagnostics.

It is only a display or grouping concern in the student Learning Path, current
training card, progress summary, and activity page. Those surfaces now consume
Stage and Module metadata instead.

The safe reinterpretation boundary is therefore the entire student-facing
navigation and presentation layer. Completion, prerequisites, promotion, and
content references stay attached to the existing records. The legacy
`/training/week/:weekNumber` route and week fields in API responses remain for
compatibility, but the stable module route is canonical for new navigation.

## Authoritative identifiers and mapping

Stages use identifiers such as `stage.windows_support`. Modules use identifiers
such as `module.windows.fundamentals`. Identifiers are independent of labels and
display order, so renaming “Windows Diagnostics” or moving a module between
stages does not affect progress.

Each active storage week maps to exactly one Module, and each Module belongs to
exactly one Stage. Structure validation fails on duplicate or malformed IDs,
duplicate storage mappings, missing stages, invalid ordering, unmapped active
activities, invalid learning roles, and broken content references. Fresh-seed
CI asserts that all activities are mapped.

To maintain the structure, edit only `STAGES` and `MODULES` in
`backend/app/services/curriculum_structure.py`, then run the curriculum validator
and tests. Do not create a second mapping in the frontend or seed files. The
admin Curriculum Structure screen reads this same backend representation; it is
an inspection tool, not a full curriculum CMS.

## Learning roles

Every activity receives presentation metadata for one of:

- Learn: lesson or video
- Check: quiz or review
- Practice: guided, networking, command, or terminal exercise
- Troubleshoot: support ticket or Service Desk scenario
- Prove: capstone

An activity can explicitly override its default role in its existing metadata.
The role organizes the module page only. It does not award completion or assert
competency, and Service Desk work is not automatically treated as proof.

## Progression and compatibility

The backend remains authoritative for Completed, Current, Available, and Locked
states. Module lock explanations are derived from existing required-activity
rules. A locked stable module route is rejected by the same backend check as its
legacy week route.

Because no completion record is rewritten or copied, existing, partial,
advanced, and completed students retain their exact activity state. The next
Stage, Module, and Activity are projections of that state. Moving a module in
Phase 4 must preserve its stable module ID and underlying activity identities.

## Current Stage and Module map

1. Technician Orientation
   - Nexus Orientation
2. Endpoint Foundations
   - Support Workflow Essentials
   - PC Hardware Foundations
3. Windows Support
   - Windows Fundamentals & Diagnostics
   - Queue & Endpoint Operations
   - Windows Troubleshooting
   - Accounts & Permissions
   - Endpoint Security & Remote Support
4. Networking Foundations
   - Client Network Triage
   - IP Addressing & Packet Flow
   - Switching & VLANs
   - Routing & Network Services
   - Secure Network Administration
5. Identity & Access
   - Active Directory Foundations
   - Domain Operations & File Access
   - Group Policy
6. Systems & Server Foundations
   - Server Networking & PowerShell
   - Server Operations & Recovery
7. Linux Support
   - Linux Fundamentals
   - Linux Services & Troubleshooting
   - Linux Production & Security
8. Cloud & Infrastructure Foundations
   - Cloud Concepts & Identity
   - Azure Infrastructure
9. Integrated Support & Capstone
   - Integrated Support Operations
   - Final Support Shift
