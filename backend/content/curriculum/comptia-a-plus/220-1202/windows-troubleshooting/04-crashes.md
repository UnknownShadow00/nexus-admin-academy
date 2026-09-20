---
lesson_key: lesson.aplus.core2.windows_troubleshooting.crashes
title: Application Crashes, BSODs and Reliability Evidence
certification_version: comptia_aplus_220-1202
domain: "3.0"
module: module.aplus.core2.windows_troubleshooting
importance: job_critical
learning_relationship: new
objectives: ["3.1"]
estimated_minutes: 14
status: published
source_name: "CompTIA A+ 220-1202 objective 3.1; adapted from Nexus PDF-editor ticket"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

An application crash affects one process; a BSOD is a Windows stop error.
Reliability Monitor and Event Viewer correlate failures with time, application,
module, driver, update, and stop information. A named faulting module is a lead,
not proof of root cause by itself.

## 2. Why does an IT worker care?

The exact error and repeatable boundary distinguish a document/app issue from
a broader OS, driver, storage, memory, or thermal problem.

## 3. Watch / read

- Microsoft — Reliability Monitor and Event Viewer support guidance. *(required)*

## 4. What you need to remember

- Capture exact error/stop code before it disappears.
- Test another file, user, or machine to isolate scope.
- Check supported app/driver/OS versions and recent change history.
- Do not download random “fix” tools or delete logs.
- Verify with the same action that originally failed.

## 5. Real workplace example

A PDF editor exports one page but crashes on a large annotated package. That
repeatable boundary and disk/app evidence guide escalation better than reinstalling Windows.

## 6. Commands / tools

Reliability Monitor (`perfmon /rel`), Event Viewer, Task Manager, vendor logs,
disk-space view, and approved app repair/update controls.

## 7. Interview / example

**What evidence belongs in a crash ticket?** Exact action, timestamp/error,
scope, reproducible sample, version/change history, logs, test, and result.

## 8. Quick Check

Four formative questions mapped to objective 3.1.
