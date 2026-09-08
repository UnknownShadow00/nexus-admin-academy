# Nexus Core Wave 2: beginner path and prerequisites

## Initial beginner path

The fresh V1 path exposed seven related problems. Nexus Orientation required the Ticketing Systems Quiz while its three-minute lesson did not define all of the ticket fields in that quiz. Week 1 then treated **Anatomy of a Good Ticket** and **Meet the Command Line** as optional even though the required Ticket Writing Fundamentals check depended on their teaching. With V2 off, My Course was hidden inside generic navigation and learner copy exposed implementation history. Activity load failures looked like locks, locked modules did not provide a precise recovery action, and quizzes/reviews could return to the generic quiz library instead of their module. Required published quizzes also accepted direct detail and submit requests without applying the curriculum teaching gate.

Baseline regression evidence is retained in `backend-before.txt`, `frontend-before.txt`, `browser-before.txt`, and `service-desk-return-before.txt`.

## First-session sequence

The exact fresh-learner order is now:

1. **Welcome to Nexus: Your First Week** — an approximately eight-minute required lesson that explains how Nexus works, what a support ticket is, requester/device/symptom/impact/category/internal progress notes/escalation, and a small worked ticket-field example.
2. **Ticketing Systems Quiz** — the four-question required check remains locked until the lesson is explicitly completed.
3. **Support Workflow Essentials** — the first A+ Foundations module, reached after the orientation lesson and quiz pass.
4. **Anatomy of a Good Ticket** — required teaching.
5. **Meet the Command Line** — required beginner CLI teaching.
6. **Ticket Writing Fundamentals** — the first module knowledge check, locked until both earlier required lessons are complete.

The quiz threshold and Wave 1 score/attempt semantics were not lowered or changed.

## Prerequisite alignment

| Module | Required activity | Required knowledge | Where previously taught | Previous status | Change made |
| --- | --- | --- | --- | --- | --- |
| Nexus Orientation | Ticketing Systems Quiz | Ticket purpose; requester, device, symptom, impact, category, internal/progress notes, escalation | Short orientation plus knowledge assumed by the quiz | Required but incomplete teaching | Expanded the same required orientation to eight minutes with definitions and a small example; hard-gated the quiz behind completion |
| Support Workflow Essentials | Ticket Writing Fundamentals | Ticket structure, internal versus user-facing writing, useful evidence | Anatomy of a Good Ticket | Optional | Made the lesson required and retained its history/content identity |
| Support Workflow Essentials | Ticket Writing Fundamentals and linked CLI practice | Prompt, command, output, safe read-only command, why output is evidence | Meet the Command Line | Optional and assumed basic CLI familiarity | Made the lesson required and added a beginner CLI introduction |
| Client Networking and the Workplace Simulation | Client Network Triage | IP address, subnet, gateway, DHCP, DNS, APIPA, ping limits | The Client-Side Network Triage Tree | Required, but definitions were implicit | Embedded the minimum definitions at the start of the required lesson |
| Client Networking and the Workplace Simulation | Client Network Triage printer questions/practice | Queue, driver, network-printer address/port, DHCP address changes, VLAN context | Network Printing Without Tears | Required, but prerequisites were implicit | Embedded the minimum printer/network definitions at the start of the required lesson |
| Early Windows troubleshooting modules | Their existing required checks | Symptom-first triage and safe evidence gathering | Existing required lessons before each check | Required | No curriculum rewrite; the shared server gate now prevents every required check from opening/submitting before earlier required lesson/video teaching in its module |

## My Course

The primary student navigation remains Today, Service Desk, and Progress. My Course is a visible contextual link on Today, remains in the More menu, labels `/learning-path`, appears in course subnavigation and module back links, and works when V2 is off. Learners see **My Course**, **A+ Foundations**, and **Course Outline** language. Learner-facing **Legacy Learning Path** copy was removed while routes and backend compatibility fields were preserved.

## Today

The dominant card now states the named next activity, its course/module context, why it matters, approximate minutes, and the next required activity. A fresh learner sees **Welcome to Nexus: Your First Week**, the reason it prepares them to understand a first support case, **About 8 min**, **After this: Ticketing Systems Quiz**, and **Continue lesson**. Existing XP, streak, quiz, and ticket statistics remain subordinate.

## Required vs Optional

The exact module explanation is:

- **Required (X): needed to complete and unlock this module.**
- **Optional practice (Y): useful extra work you may skip.**

Activity badges use **Required** and **Optional practice**. The module no longer adds Job Critical/Know It/Awareness labels to the required-versus-optional decision.

## Locked states

Prerequisite failures use the structured `PREREQUISITE_NOT_MET` response with the locked activity, exact missing prerequisite, and an internal recovery route. The UI renders **Quiz locked** or **Module locked**, a specific explanation, and **Go to [prerequisite]**. HTTP 404 renders **[Activity] unavailable**. Network/server failures render **Unable to load [activity]**, a retry, and My Course. These states no longer share generic lock copy.

## Navigation

Module activity links carry a validated `returnTo` and bounded `returnToLabel` in the URL as well as router state. Quiz entry, result, saved/historical review, lesson and Service Desk flows therefore survive refresh and return to the named originating module. Service Desk accepts V1 module routes and stores the same named return target. `/progress` is the canonical learner route and its primary navigation item stays active.

## Direct assessment access

One server policy now protects both required quiz detail delivery and submission. It evaluates required curriculum mappings, reached-week/module gates, and unfinished earlier required lesson/video teaching. Direct page and API requests receive 403 before questions are delivered or attempts/credit are created. Intentionally optional practice remains available. Mentors and learners with an already-earned pass retain access, retries, monotonic completion, and historical review.

## Browser beginner flow

Against a newly generated temporary SQLite database, V2 explicitly off, and one disposable learner, Playwright passed:

Login → Today → inspect the obvious next action → My Course → verify a future module's recovery lock → return to Today → open the orientation lesson → confirm quiz remains hidden until explicit completion → complete lesson → answer the taught four-question check → receive 100%/Passed feedback → open saved review → reload → return to **Nexus Orientation** → continue to **Support Workflow Essentials** → inspect required/optional counts → deny direct future required quiz access → follow recovery to **Anatomy of a Good Ticket** → complete it → verify Today advances to **Meet the Command Line** → verify Today/module at 390px without document overflow.

Separate browser checks passed V2-off My Course visibility, Progress active state, direct-access recovery, all four Wave 1 truth flows, and the Service Desk P1 desktop/mobile plus P0 authenticated integrity gates.

## Screenshots

- `docs/core-wave2/screenshots/fresh-today.png`
- `docs/core-wave2/screenshots/my-course.png`
- `docs/core-wave2/screenshots/first-required-module.png`
- `docs/core-wave2/screenshots/required-optional.png`
- `docs/core-wave2/screenshots/locked-prerequisite.png`
- `docs/core-wave2/screenshots/first-quiz-entry.png`
- `docs/core-wave2/screenshots/return-to-module.png`
- `docs/core-wave2/screenshots/mobile-today.png`
- `docs/core-wave2/screenshots/mobile-module.png`

## Tests

- Backend: 276 tests passed (272 combined curriculum, quiz, Wave 1/Wave 2, V1/V2 and Service Desk contract tests; 4 additional study-tracker/squad tests).
- Core frontend: 68 tests passed; the final return-label hardening rerun passed 7 focused tests.
- Service Desk: 519 unit tests passed (37 shared, 268 simulation, 36 UI, 178 web).
- Browser: 11 tests passed (4 Wave 2 beginner, 4 Wave 1 truth, 2 Service Desk P1 desktop/mobile, 1 Service Desk P0 authenticated beginner).
- Core and Service Desk production builds passed. Service Desk lint/typecheck, scoped Core ESLint, Ruff, compileall, Python/JS/TS formatting and whitespace checks passed.
- Python audit reports no known vulnerabilities. The unchanged Core frontend lockfile retains one high Browserslist and one low `postcss-selector-parser` advisory; dependency remediation was outside this curriculum/navigation wave.

## Git

Dedicated child branch: `fix/core-wave2-beginner-path`, based on Wave 1 commit `a32357b`. Logical implementation, navigation and evidence commits are recorded in the final handoff. Nothing was merged or pushed.

## Deferred Core Wave 3

- full lesson template redesign
- worked examples and diagrams beyond the small orientation example
- completion readiness treatment
- notes/autosave reliability
- content contradictions, including SFC/DISM corrections

## Production safety

No production service, database, content or learner was accessed or changed. No deployment, migration, production content load, pilot enrollment, VM/Proxmox work, V2 enablement, or merge to main occurred. Production therefore remains at the supplied starting state: schema `0064_v2_ai_grading_infrastructure`, V2 off, and no pilot enrollment.
