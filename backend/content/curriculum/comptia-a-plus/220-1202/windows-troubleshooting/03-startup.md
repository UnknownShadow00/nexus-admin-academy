---
lesson_key: lesson.aplus.core2.windows_troubleshooting.startup
title: Startup, Boot and Unexpected Shutdowns
certification_version: comptia_aplus_220-1202
domain: "3.0"
module: module.aplus.core2.windows_troubleshooting
importance: job_critical
learning_relationship: new
objectives: ["3.1"]
estimated_minutes: 14
status: published
source_name: "CompTIA A+ 220-1202 objective 3.1"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

Boot problems occur before or during Windows startup. Unexpected shutdowns can
come from power, heat, drivers, updates, hardware, or system faults.

## 2. Why does an IT worker care?

The last successful stage—power, POST, boot device, Windows loader, sign-in,
desktop—narrows the fault dramatically.

## 3. Watch / read

- Microsoft Support — Windows startup and recovery options. *(required)*

## 4. What you need to remember

- Separate no-power/no-POST from Windows boot failure.
- Capture stop code and recent changes; repeated forced shutdowns risk data.
- Use Windows Recovery Environment and Safe Mode only for a reasoned test.
- Check temperature/power when shutdowns occur under load.
- Preserve recovery keys and user data before repair/reset/reinstall.

## 5. Real workplace example

Safe Mode works after a display-driver update. Roll back the driver, boot
normally, reproduce the original task, and record the stable version.

## 6. Commands / tools

Windows Recovery Environment, Safe Mode, startup settings, firmware diagnostics,
Event Viewer, and Reliability Monitor.

## 7. Interview / example

**Why ask where boot stops?** Each stage has different likely causes and tools;
it prevents applying Windows repairs to a machine that never completed POST.

## 8. Quick Check

Four formative questions mapped to objective 3.1.
