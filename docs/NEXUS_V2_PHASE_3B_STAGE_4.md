# Nexus V2 Phase 3B — Stage 4 implementation

Status: implemented for disposable pilot validation; **human editorial approval is recorded for the exact Stage 4 question-bank bytes** (SHA-256 `295fcc93f0d117f1db7b91c9b2371e872d4bd5ebe17e19a428dac946f591cdd0`). Manual Windows learner/admin UAT passed the Stage 4 learning, practical submission, mentor rejection, correction, resubmission, approval, and mastery flow. This document does not authorize loading content or enabling learners in production. The separate completed Stages 4–6 design was not present in the requested baseline checkout; the Stage 4 request and the Stage 1–3 contract guided this change.

## Practical feasibility

The existing V2 guided lab supports a non-VM lab template, a learner-owned run, image evidence upload, a structured note, a mentor review queue, and an explicit mentor pass. A learner must have an **approved Windows computer** and an account they are authorized to use. Nexus does not supply that computer. The static `nexus-stage4-practice.txt` file supplies the named practice item; the learner downloads it to their own Downloads folder and follows that path in File Explorer. The practical asks for actual Windows screenshots of the file location and one read-only application or Windows observation. It does not simulate a Windows session or grade a written guess as hands-on work.

No Windows VM, Proxmox template, Guacamole configuration, M365 tenant, Service Desk scenario, or command entry was added. If a learner has no approved Windows computer, they stop and contact the mentor; they cannot honestly complete this practical on a multiple-choice substitute.

## Stage structure

`module.nexus.beginner.stage4` belongs only to `nexus_beginner_aplus_v1`, follows Stage 3 mastery, and has domain `S4`, Everyday Windows Support. The new Nexus objectives are `B4.1` (find and protect work), `B4.2` (accounts and authorization), and `B4.3` (read-only clues and honest documentation).

| Group | Lesson | Required card | Required interaction | Five-question checkpoint |
| --- | --- | --- | --- | --- |
| Find and protect work | `lesson.nexus.beginner.s4.find_protect` | `res.nexus.beginner.s4.find_protect` | `interaction.nexus.beginner.s4.find_protect` — ordering | `assess.nexus.beginner.s4.find_protect` |
| Accounts and access boundaries | `lesson.nexus.beginner.s4.access` | `res.nexus.beginner.s4.access` | `interaction.nexus.beginner.s4.access` — safe action | `assess.nexus.beginner.s4.access` |
| Applications and Windows clues | `lesson.nexus.beginner.s4.clues` | `res.nexus.beginner.s4.clues` | `interaction.nexus.beginner.s4.clues` — matching | `assess.nexus.beginner.s4.clues` |

`res.nexus.beginner.s4.note_recap` is optional. Exactly 15 Stage 4 questions live in `beginner-stage-4.yaml`, five per checkpoint, each with an explanation and one answer. Every checkpoint passes at 80% (four of five). The repository editorial approval manifest now approves only the exact reviewed bytes; the importer checks the hash and question count before setting validated answer-key and explanation flags. Disposable journey tests use a temporary approval manifest for isolation and do not load production content.

## Guided practical and mastery

`assess.nexus.beginner.s4.windows_observation` binds to the guided template `Stage 4 — Windows observation practical`. The learner must upload at least two redacted screenshots and complete Reported, Checked, Found, Verified or Not verified, and Next step note lines. The mentor sees the screenshots, note, and six rubric criteria: performed evidence, correct observation, safety, privacy and redaction, honest verification, and useful documentation. An approval requires the mentor to confirm every criterion. Submission remains `needs_review`; only an approved mentor pass satisfies the practical assessment. Rejection reopens the existing run for correction and resubmission.

Stage 4 mastery requires three required card opens, three trusted interaction passes, three checkpoint passes, and the approved practical pass. Passive lessons and the optional recap cannot substitute for evidence. Stage 5 and 6 are not authored, shown, or required. The beginner pilot switch still defaults off, and the V2 master switch and allowlist still gate access.

## Deferred progression behavior

This cleanup keeps the current mentor approval gate. In a separate implementation before Stage 5 exists, automatically graded requirements plus submission of the required practical should permit provisional access to the next stage. The current stage should read **Awaiting mentor review** and remain unmastered until approval. Rejection should create an outstanding correction with feedback and a direct resubmission route, without removing access to work already unlocked. Final course or capstone completion may require approval of every required mentor-reviewed practical. This deferred continuation grant needs a persisted, auditable state and regression tests; no such grant is added by this cleanup.

## Deferred visual walkthrough

The later UI pass will review correction banner contrast and readability, success panel hierarchy, practical-page density, teaching-resource drawer polish, teaching-card visuals and content, and broader Stage 4 design consistency. These visual changes are outside the final functional cleanup.
