---
lesson_key: lesson.aplus.core2.windows_support_tools.system_commands
title: Windows System and Policy Commands
certification_version: comptia_aplus_220-1202
domain: "1.0"
module: module.aplus.core2.windows_support_tools
importance: job_critical
learning_relationship: new
objectives: ["1.2"]
estimated_minutes: 15
status: published
source_name: "CompTIA A+ 220-1202 objective 1.2; adapted from Nexus Windows Command-Line Diagnostics"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

`netstat` shows connections/listeners, `gpupdate` refreshes Group Policy,
`sfc` checks protected Windows files, and `chkdsk` checks a volume's filesystem.

## 2. Why does an IT worker care?

These commands answer different questions. Using the wrong or most disruptive
tool first wastes time and can interrupt a user.

## 3. Watch / read

- Microsoft Windows Commands reference. *(required)*

## 4. What you need to remember

- `netstat -ano` links connections/listeners to process IDs.
- `gpupdate` refreshes policy; `/force` is not always necessary.
- Start SFC investigation with an approved elevated window; `sfc /verifyonly` checks without repair.
- Plain `chkdsk` reports status without fixing errors; an active volume can
  produce an inconsistent snapshot. Repair switches can need downtime/restart.
- Capture the exact message and follow local authorization.

## 5. Real workplace example

A managed setting has not arrived. The technician checks scope and connectivity,
runs `gpupdate`, records the result, and verifies the setting—not `chkdsk`.

## 6. Commands / tools

`netstat -ano`, `gpupdate`, `sfc /verifyonly`, `chkdsk`.

## 7. Interview / example

**Why avoid repair switches immediately?** Diagnosis should preserve evidence
and minimise interruption; repairs may alter state or require a restart.

## 8. Quick Check

Five formative questions mapped to objective 1.2.
