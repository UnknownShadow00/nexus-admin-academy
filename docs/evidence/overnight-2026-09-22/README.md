# Isolated overnight evidence — 22 September 2026

All screenshots use freshly seeded local databases and disposable users. Names such as Mentor/Shak are stock seed fixtures, not production records. Password fields are empty in the password-setup screenshot. No credentials, session exports, database files, or browser traces are included here.

`before/` captures the PR #39 candidate before the new student-experience UI. `after/` captures the independent quality branch based on main `07780a9`; it does **not** represent a deployed or merged release. Curriculum JSON/model evidence describes PR #39's intended path, so its totals may differ from the main-based Progress screenshot.

## Representative views

| View | Evidence | Visual assessment |
| --- | --- | --- |
| Today | [Desktop](after/today-desktop.png) | One prominent training action; module requirements visible. |
| Orientation | [Desktop](after/orientation-desktop.png) | Worked ticket example precedes the first quiz; notes are labelled with persistent save status. |
| Lesson | [Desktop](after/lesson-desktop.png) | Readable content, formative note exercise, explicit completion. |
| Quiz before answering | [Before 375px](before/quiz-375.png), [after 375px](after/quiz-375.png), [390px](after/quiz-390.png), [tablet](after/quiz-768.png), [desktop](after/quiz-desktop.png) | Title, instructions, complete answer targets, and wrapping checked. No horizontal overflow at measured widths. Long question moved fully inside its card after screenshot inspection. |
| Keyboard focus | [Mobile focus](recovery/quiz-mobile-focus.png) | Focus ring surrounds the answer card; Space selects it; Next focuses the next question. |
| Imperfect feedback | [Mobile](recovery/quiz-mobile-feedback.png) | Wrong/unanswered status, original answers, correct answers, explanations, and missed-question filter. |
| Passing result | [Desktop](after/quiz-result-desktop.png), [mobile](after/quiz-result-mobile.png) | Score is subordinate to useful feedback and next actions; result focus scroll offset respects the sticky navigation. Toast is transient and can appear in immediate result captures. |
| Failure recovery | [Review before](before/quiz-review-error.png), [review after](after/quiz-review-error.png), [lesson before](before/lesson-false-lock.png), [lesson after](after/lesson-false-lock.png) | Same injected HTTP 500 now has an honest failure message and retry, rather than a false empty attempt or prerequisite lock. |
| CLI | [Mobile](after/cli-mobile.png) | Contained terminal; unfamiliar Cisco vocabulary motivates finding N17. Partial work recovery remains deferred. |
| Service Desk | [Desktop](after/service-desk-desktop.png), [mobile](after/service-desk-mobile.png) | Tool/workspace/evidence/notes hierarchy inspected. No page overflow at 375px. Next.js development badge is local-only. |
| Progress | [Desktop](after/progress-desktop.png), [mobile](after/progress-mobile.png) | Heading matches navigation; course completion is explicitly distinguished from skill evidence. |
| Admin | [Students desktop](after/admin-students-desktop.png) | Password-setup status is visible; more useful intervention fields are a separate follow-up. |

The before/after `findings.json` files contain measured widths, focused-element styles, refresh observations, and successful disposable-account deletion. These are representative checks, not complete WCAG or browser compatibility certification.

## Curriculum/model evidence

- [Curriculum map](curriculum-map.json): fresh seed activity relationships.
- [Time estimates](curriculum-time.json): required/optional activity estimates, not measured learner runtime.
- [Progression through Week 12](progression-through-week12.json): the real progression engine evaluated against synthetic completion records. It reached Week 13, kept password reset at Week 6/MFA at Week 7, opened the switch gate at the start of Week 11, and left Hybrid unavailable. This is not a claim that every Week 5–12 exercise was completed in the UI.

The report distinguishes these model checks from actual Playwright beginner, auth, Service Desk, and Weeks 1–4 journeys.
