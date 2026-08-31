---
lesson_key: lesson.aplus.hardware.storage_display_troubleshooting
title: Storage, RAID & Display Troubleshooting
certification_version: comptia_aplus_220-1201
domain: '3.0'
module: module.aplus.core1.hardware_fault_isolation
lesson_order: 6
importance: job_critical
learning_relationship: deep_dive
objectives:
- '5.2'
- '5.3'
estimated_minutes: 50
status: published
summary: Protect data while diagnosing SMART/RAID/drive symptoms and use input/cable/known-good
  tests to isolate display failures.
quick_check:
  title: "Quick Check \u2014 Storage, RAID & Display Troubleshooting"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M8Q023
  - M8Q024
  - M8Q027
  - M8Q031
---

# 1. What is this?
Storage and display problems often look like OS problems. A+ expects recognition of drive/RAID indicators, clicking/grinding, no boot device, corruption, SMART alerts, slow I/O/low IOPS, missing drives/arrays, and display issues such as no signal, dim/fuzzy/flashing output, burn-in/dead pixels, projector shutdown, sizing/distortion, and incorrect input.

# 2. Why does an IT worker care?
Storage mistakes can destroy the only readable copy of data. Display mistakes can waste hours reinstalling Windows when the real issue is an input source or cable. Evidence and data safety come first.

# 3. Watch / Read
**Required:** Professor Messer — *Troubleshooting Storage Devices* and *Troubleshooting Display Issues (220-1201)*.

# 4. What you actually need to remember
- Clicking/grinding HDD + important data: stop unnecessary writes; protect/recover data according to policy before aggressive repair.
- SMART warnings are predictive evidence; back up/replace/escalate rather than pretending the drive is healthy.
- A degraded/failed RAID indicator requires identifying the array state and following platform procedure; RAID is not a backup.
- Missing drive can be power/data connection, firmware detection, controller, or failed drive—check evidence in order.
- No signal: verify monitor power, cable, input source, and known-good display/cable before blaming GPU/board.
- Very dim display, flickering, wrong colors, or lines may be display/cable/adapter/driver/GPU; isolate with known-good substitutions.
- Burn-in/image retention and dead pixels are panel-specific symptoms; they are not fixed by clearing browser cache.

# 5. At work
A user's external monitor says "No Signal" after a desk move. The correct first checks are power/input/cable/known-good source—not motherboard replacement.

# 6. Commands / Tools
SMART/vendor storage tools, firmware/RAID status, Disk Management (where safe), monitor self-test, display settings, and known-good cables/displays.

# 7. Interview / Explain
Explain why a clicking HDD changes your troubleshooting priorities.

# 8. Quick Check
Use Module 8 Quick Check 6: M8Q023, M8Q024, M8Q027, M8Q031.
