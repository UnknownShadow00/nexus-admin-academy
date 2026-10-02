# Stage 4 editorial review — human approval recorded

Scope: Nexus V2 Beginner Stage 4, `module.nexus.beginner.stage4`. This is the question-by-question editorial review. The user separately granted human approval on 2026-09-29 for the exact final bank hash below; that approval is recorded in the repository manifest. Production publication and beginner Windows UAT are separate decisions.

## Questions

The final bank has 15 questions: five each for B4.1, B4.2, and B4.3. Every answer below was checked against its preceding lesson, teaching card, and interaction. All 15 have one defensible keyed answer and a useful explanation after the edits below. No answer depends on Stage 5 or 6 material.

| # | Objective / taught concept | Key | Editorial finding |
| --- | --- | --- | --- |
| 1 | B4.1; a checked folder is a limited observation | A | Pass. Other choices overclaim where the file went. |
| 2 | B4.1; extension hints at file type | C | Pass. Key and explanation distinguish the extension from ownership, account, and application state. |
| 3 | B4.1; file, folder, application, and account | B | Pass. The saved document is the file. |
| 4 | B4.1; authorized locating is read-only | D | Pass. Moving, deleting, and copying exceed the task. |
| 5 | B4.1; protect unsaved work | B | Pass after replacing weak distractors with plausible premature close, autosave assumption, and restart choices. |
| 6 | B4.2; Documents differs by signed-in account | D | Pass. The account provides context, not wider permission. |
| 7 | B4.2; Access denied is a boundary | A | Pass. Borrowing credentials, changing permissions, and unapproved admin access are unsafe. |
| 8 | B4.2; authorization differs from technical capability | C | Pass. Whether a folder opens does not settle permission. |
| 9 | B4.2; least privilege | B | Pass. The approved check needs only its authorized access. |
| 10 | B4.2; another person's file | D | Pass. The note must state the access limit and route to an authorized person. |
| 11 | B4.3; current application state before change | C | Pass. Ending a process, reinstalling, or changing settings is premature. |
| 12 | B4.3; Task Manager shows a listed process | A | Pass after replacing a weak distractor with the common but unsupported inference that a listed application works normally. |
| 13 | B4.3; exact error evidence is not diagnosis | D | Pass after replacing an untaught repair-command reference with a guessed setting change. |
| 14 | B4.3; approved software and observation scope | B | Pass after clarifying that the suggestion is recorded and approval checked, without implying an installation is part of Stage 4. |
| 15 | B4.3; observed versus user-verified | A | Pass. The path check cannot be called resolution before confirmation. |

Answer positions are A/B/C/D = 4/4/3/4. Correct choices do not systematically stand out by length. Distractors represent limited-observation overclaims, file and account confusion, permission bypasses, and premature fixes. Questions use terms introduced in the associated lesson before assessment. The bank contains no command-entry, Service Desk, advanced filesystem, registry, service, or diagnostic procedure requirement.

## Other learner material

- All three lessons, required SVG cards, and required native interactions match B4.1–B4.3. The ordering interaction now describes a safe locating sequence and leaves unsaved work open; it does not require a disruptive action. The safe-action interaction respects Access denied. Matching maps File Explorer, the affected application, Task Manager, and Settings to distinct read-only clues.
- The first lesson's worked note and the third lesson's short note practice now use five fields: Reported, Checked, Found, Verified / Not verified, and Next step. The clues card and optional note recap display the same structure. The optional recap remains nonblocking.
- Learner navigation presents Stage 4 as the fourth beginner stage, with no Stage 5/6 cards or required command entry. Generic V2 module wording does not call a selection or written guess hands-on work.

## Guided practical and mentor decision

`assess.nexus.beginner.s4.windows_observation` requires an approved Windows computer and an authorized account. The learner downloads the harmless named practice file, follows the supplied Downloads path in File Explorer, inspects a real application or Task Manager clue without changing work, leaves unsaved work open, and submits two redacted screenshots plus the five-field note. A written guess is insufficient. If no approved Windows computer is available, the learner stops and contacts a mentor.

The mentor rubric separately checks performed evidence, correct observation, safety, privacy/redaction, honest verification, and useful documentation. The performed-evidence criterion now states what each of the two screenshots must show. Submission is pending review and does not grant mastery; all six rubric criteria require mentor confirmation before pass. The existing upload system checks the two-artifact minimum and note fields, while the mentor assesses whether the screenshots are genuine, distinct, relevant, and redacted. This human evidence check remains necessary.

Stage 4 has no destructive Windows directions and does not imply that a restart, process listing, error message, or one observation proves a fix. The exact bank is now in `editorial-approvals.yaml`; its editorial flags are set only when the importer verifies those bytes and all 15 questions. Beginner Windows learner/admin UAT passed.

Final bank SHA-256: `295fcc93f0d117f1db7b91c9b2371e872d4bd5ebe17e19a428dac946f591cdd0`.
