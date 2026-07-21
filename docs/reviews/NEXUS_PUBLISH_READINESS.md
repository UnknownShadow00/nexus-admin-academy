# Publish Readiness Classification

Date: 2026-07-21. Phase 17. Per-area readiness, followed by exactly one
overall recommendation.

| Area | Classification | Basis |
|---|---|---|
| Navigation | **Ready with fixes** | Structure is sound; onboarding/capstone-visibility gaps (NAV-001/003/004) are cheap, well-understood fixes |
| Week 0 / Onboarding | **Not ready** | No platform onboarding exists anywhere; this is the biggest single gap for total beginners (ONBOARD-001) |
| Curriculum (24 weeks) | **Ready** | Coherent, well-sequenced, no reordering needed; only thin-practice weeks as quality-improvement items |
| Lessons | **Ready** | Consistently strong writing across all 63 lessons; Week 1's missing lesson (LESSON-001) is the one real gap |
| Quizzes | **Ready with fixes** | Required-quiz population is strong; optional/certification tail has real quality gaps (QUIZ-001) that don't block required progression but are student-visible |
| Tickets | **Not ready** | Content and AI grading are strong and live-tested successfully, but TICKET-001 (the A+ unlock gate) currently blocks all ticket work for a fresh student — this alone makes the ticket *system* not ready even though ticket *content* is |
| Labs | **Ready with fixes** | Content is reasonable; XP/mentor-gate/evidence-verification gaps (CUR-001, LAB-002, LAB-003) are real but do not block basic functioning for a small trusted cohort |
| Accessibility | **Ready with fixes** | No blocking defect found; several real gaps (ACCESS-001/002/004) should be fixed but were assessed via source code only, not a live browser pass |
| Mentor/Admin | **Ready** | Core review/reject/verify workflow, AI cost dashboard, and gate config all confirmed working correctly via live testing this session |
| Technical | **Ready** | 176/176 tests, clean Alembic head, clean SQLite integrity/FK, 0 npm vulnerabilities, clean build — all re-verified fresh this session |
| Manual-VM readiness | **Confirmed as claimed** | All 5 labs are browser/evidence-based; no VM dependency exists in the current content |
| Automated-VM (Proxmox/Guacamole) | **Not ready, and correctly disabled** | 0 live VM assignments, 0 lab templates with a VMID — matches the review brief's own framing exactly |

## Overall recommendation

**Ready for five/six-student private launch, conditional on fixing TICKET-
001 and ONBOARD-001 first.**

Neither fix is large. TICKET-001 is a single admin-setting change (or a
small, well-scoped code change to surface the gate's meaning before a
student hits it) — it is currently the one finding that would make the
platform **functionally fail** for a real beginner within their first day
or two, not merely confuse them. ONBOARD-001 is the platform's single
biggest gap against the review's own central question ("does a complete
beginner know what to do next"), and every other structural piece of the
platform (curriculum, tickets, grading, mentor tools) is strong enough that
a short orientation addition would let those strengths actually reach the
student. Everything else in this review (navigation polish, quiz/lab
consistency, accessibility hardening, mentor-workload reductions) is real
but genuinely deferrable to "during Weeks 1-4" or "after the first cohort
begins" without threatening the launch.

This is **not** a recommendation for "Ready for broader launch" — several
findings (evidence not truly verified, no live accessibility audit, thin
practice on the program's hardest concepts) are acceptable risks for a
small, mentor-supervised, five/six-person cohort of friends, but would need
addressing before opening this platform to a larger or less closely
mentored group.
