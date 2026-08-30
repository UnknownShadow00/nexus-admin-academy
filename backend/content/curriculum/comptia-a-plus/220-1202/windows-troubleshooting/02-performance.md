---
lesson_key: lesson.aplus.core2.windows_troubleshooting.performance
title: Slow Performance and Resource Pressure
certification_version: comptia_aplus_220-1202
domain: "3.0"
module: module.aplus.core2.windows_troubleshooting
importance: job_critical
learning_relationship: new
objectives: ["3.1"]
estimated_minutes: 14
status: published
source_name: "CompTIA A+ 220-1202 objective 3.1; adapted from Nexus slow-PC scenario"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

Slow performance can come from sustained CPU, exhausted memory, paging, disk
space/I/O, startup load, updates, thermal throttling, or one failing application.

## 2. Why does an IT worker care?

“Slow” is not a diagnosis. Measuring the constrained resource prevents random
cleanup, unsafe registry changes, and unnecessary hardware replacement.

## 3. Watch / read

- Microsoft — Task Manager and Windows performance guidance. *(required)*

## 4. What you need to remember

- Reproduce and compare idle vs affected workload.
- Sort Task Manager by CPU, Memory, Disk, and Network; record sustained behavior.
- Check free space and startup impact; identify the owning process.
- Correlation is not cause—confirm by a safe controlled test.
- Retest the original workflow after the fix.

## 5. Real workplace example

Startup reaches 100% CPU because several approved apps and a scan launch
together. Schedule/disable only approved unnecessary items, reboot, and time again.

## 6. Commands / tools

Task Manager, Resource Monitor, Settings > Apps > Startup, `tasklist`, and
Performance Monitor where available.

## 7. Interview / example

**A PC is slow. What next?** Define when/where, inspect live bottlenecks and
space, test the leading cause safely, then measure the same workload again.

## 8. Quick Check

Five formative questions mapped to objective 3.1.
