# Nexus IT Academy — Student Guide

Welcome. Nexus is a simulated IT workplace, not a video course. You learn by
investigating, fixing, documenting, and communicating — the same things a real
technician is paid to do. This guide covers everything you need for Phase A
(Weeks 1–4, Trainee → Support Technician I) and Phase B (Weeks 5–8, → Support
Technician II). The application also contains the later 24-week curriculum;
your mentor will introduce those phases as your cohort advances.

## How to log in

Your mentor created your account. There is no public sign-up. Use the username
and password you were given at the login screen. If you're locked out, message
your mentor — you can't reset it yourself (that's by design; it's the same in a
real workplace).

## Your home screen: "This Week"

When you log in, the **This Week** panel is the map. It shows, for your current
week, everything you need to do — lessons, quizzes, CLI labs, labs, and
tickets — each marked done, available, or in review. The **Next up** button
always points at the single most useful thing to do next. Follow it when you're
not sure where to go.

Progress percent on that panel is your week, not your life — 100% means this
week's required items are complete, and you can review flashcards or work ahead.

## The learning cycle (do it in this order)

Each week walks the same loop. Don't skip steps — the tickets assume you did
the lessons.

1. **Read the lesson.** Short, practical, written for the job. Every lesson
   lists learning outcomes as actions ("diagnose…", "verify…"). Those actions
   are what you'll be graded on later.
2. **Do the guided practice** in the lesson (worksheets, evidence drills on
   your own PC).
3. **Take the quiz.** It checks reasoning, not memorization. You can retake it;
   every attempt is saved, and your best score counts toward your promotion
   gate. Only your first attempt earns XP, so think before your first submit.
4. **Do the CLI labs / hands-on labs** where the week lists them.
5. **Work the tickets.** This is the real work. See below.
6. **Watch your gate progress** on the promotion status view.

## How to work a ticket

A ticket is a realistic support scenario. Read it, investigate, fix or escalate,
then write it up. Your write-up is graded on **five anchors**, each worth 2
points (10 total):

- **investigation** — did you gather information before acting?
- **root_cause** — did you correctly identify the actual cause?
- **safe_fix_or_escalation** — was your change safe and minimal, or did you
  escalate cleanly when that was the right call? (Escalating is a *correct*
  answer to some tickets — it is not "giving up.")
- **verification** — did you prove the problem is gone, with evidence?
- **communication** — clear internal notes and a plain-language user message?

A ticket passes at a score of 6 or higher, and never with a 0 in verification
or safe_fix_or_escalation. A working fix you didn't verify does **not** pass.
"Claimed success without evidence" is the fastest way to fail a ticket you
actually solved.

### Evidence

Most tickets require screenshots and the commands you used. Screenshot the
*evidence* (the ipconfig output, the Event Viewer entry), not just the final
"it works" screen. Your uploads are private to you.

### Hints

Stuck? Each ticket has up to four hints, revealed one at a time. The button
tells you the XP cost **before** you reveal — the ladder is −5%, −10%, −20%,
−35%, and you always keep at least 40% of the ticket's XP. Try on your own
first, but don't stay stuck for an hour out of pride; a hint and a finished
ticket beats a blank one.

### Your tickets are yours

The same ticket shows different names, addresses, and values to different
students. Copying a classmate's answer will not match your version — and the
whole point is that you can do it yourself.

## Promotion gates

You advance by demonstrating competence, not by watching videos. Each gate
checks real data:

- **Gate 1 (→ Support Technician I), end of Week 4:** Weeks 1–4 lessons done,
  quiz mastery ≥ 70% in the phase domains, at least 8 verified tickets
  (including 2 harder ones), and **Multi-Ticket Simulation 1 passed with no
  hints, score ≥ 7**. No unresolved mentor flags.
- **Gate 2 (→ Support Technician II), end of Week 8:** Weeks 5–8 lessons done,
  mastery ≥ 70% in troubleshooting/networking/security, the required verified
  tickets across difficulties, and **Multi-Ticket Simulation 2 passed with at
  most 1 hint, score ≥ 7**. No unresolved mentor flags.

If you don't pass a gate, you are **not** sent back to the start. You get a
short, targeted remediation list — the specific skills to redo — and you
re-attempt just those. A mentor may leave a flag (a comment) on a submission;
resolving it with the mentor clears it.

## The multi-ticket simulations

Simulation 1 (Week 4) and Simulation 2 (Week 8) drop several tickets on you at
once. **Submit your priority order and one-line justifications first**, then
work them. One ticket will have a misleading description; one will need
escalation, not a fix; one may be a security issue that jumps the queue. The
loudest ticket is rarely the most important — rank by impact and urgency. These
are your gate checkpoints, so do the earlier tickets first to build the skill.

## A few habits that will make you employable

- Ask for evidence, not opinions ("send me a screenshot of the exact error").
- Change one thing at a time, and know how to undo it before you do it.
- Verify with the command that would show the *old* broken state.
- Never expose passwords in screenshots or notes.
- When in doubt on sensitive access or a possible security incident, **escalate
  with a complete note** — that's the professional move, and it scores full
  marks.

Good luck. Work the process, and the competence follows.
