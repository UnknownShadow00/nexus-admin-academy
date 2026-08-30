---
lesson_key: lesson.aplus.service_desk.ticket_notes_user_updates
title: Internal Notes, User Updates & Resolution Notes
certification_version: comptia_aplus_220-1202
domain: '4.0'
module: module.aplus.core2.service_desk_workflow
importance: job_critical
learning_relationship: deep_dive
objectives:
- '4.1'
- '4.7'
lesson_order: 2
quick_check:
  title: "Quick Check \u2014 Internal Notes, User Updates & Resolution Notes"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - Q002
  - Q004
  - Q005
  - Q006
---

# Lesson 2 — Internal Notes, User Updates & Resolution Notes

**Importance:** Job Critical  
**Relationship:** Review / Deep Dive  
**Objectives:** 220-1202 4.1, 4.7

## 1. What is this?
A good ticket tells the story of the work without becoming a novel. Internal notes are written for technicians. User-facing updates are written for the requester.

A useful internal record answers:
- What was reported?
- What did I check?
- What evidence did I find?
- What did I change or decide?
- How did I verify the result?
- What is the current state / next step?

## 2. Why does an IT worker care?
Another technician may inherit your ticket. A supervisor may audit it. The user may call back tomorrow. If the note says "fixed it," everyone starts over.

## 3. Watch / Read
**Required:** Professor Messer — *Ticketing Systems (220-1202)*  
https://www.professormesser.com/free-a-plus-training/220-1202/220-1202-video/ticketing-systems-220-1202/

## 4. What you actually need to remember
**Internal notes:** technical facts, tests, exact errors, commands, results, changes, verification, escalation details.  
**User-facing update:** plain language, impact acknowledged, current status, what happens next, realistic timing.

Never:
- blame the user without evidence
- paste secrets/passwords into notes
- claim success without verification
- write vague statements such as "ran some commands, seems fine"

## 5. At work
Bad note:
> PC was broken. Fixed it.

Better:
> User reported internal sites failed while public sites loaded. Confirmed IP connectivity and reproduced DNS failure with `nslookup`. Corrected the approved DNS setting and repeated the original hostname test successfully. User confirmed the scheduling portal opens normally.

User-facing:
> Your computer was using the wrong service to look up internal site names. I corrected the setting and confirmed the scheduling portal opens again.

## 6. Commands / Tools
Commands are not the lesson, but **evidence from earlier modules belongs in the ticket** when relevant: `ipconfig`, `ping`, `nslookup`, Event Viewer entries, service state, screenshots, etc.

## 7. Interview / Explain example
**Question:** "What makes a good ticket note?"  
A strong answer says another technician should understand the symptom, evidence, work performed, result, verification, and next step without making the user repeat the story.

## 8. Quick Check
Use bank questions: **Q002, Q004, Q005, Q006**.
