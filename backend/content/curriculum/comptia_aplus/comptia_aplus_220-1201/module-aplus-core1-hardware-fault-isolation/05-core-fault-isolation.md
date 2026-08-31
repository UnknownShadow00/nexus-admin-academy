---
lesson_key: lesson.aplus.hardware.core_fault_isolation
title: POST, No-Power, Thermal & Core Hardware Fault Isolation
certification_version: comptia_aplus_220-1201
domain: '3.0'
module: module.aplus.core1.hardware_fault_isolation
lesson_order: 5
importance: job_critical
learning_relationship: deep_dive
objectives:
- '5.1'
- '3.3'
- '3.6'
estimated_minutes: 50
status: published
summary: Use symptom patterns, POST evidence, minimal configuration, temperature/power
  clues, and scope boundaries to isolate core hardware faults.
quick_check:
  title: "Quick Check \u2014 POST, No-Power, Thermal & Core Hardware Fault Isolation"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M8Q018
  - M8Q019
  - M8Q020
  - M8Q021
---

# 1. What is this?
Core hardware troubleshooting uses symptom patterns plus controlled tests. A+ includes POST beeps/proprietary error messages, blank/no power, sluggishness, overheating, burning smell, random shutdown, application crashes, unusual noise, swollen capacitors, and inaccurate date/time.

# 2. Why does an IT worker care?
Junior technicians often cause more downtime by replacing three components at once. Strong bench work changes one variable, protects data, records POST/error evidence, and knows when a safety risk requires immediate power-down/escalation.

# 3. Watch / Read
**Required:** Professor Messer — *Troubleshooting Hardware (220-1201)*.

# 4. What you actually need to remember
- No fans/lights: start with external power path, PSU, then motherboard connections.
- Fans/lights but no POST/display: use beep/LED/error evidence; inspect/reseat supported RAM/GPU connections; simplify configuration if authorized.
- Minimal boot isolates to the smallest required set, then parts are added back one at a time.
- Overheating: inspect airflow, fan operation, dust, heatsink/contact, and temperatures—not just "add a bigger PSU."
- Burning smell/smoke: power down, disconnect, do not keep testing energized hardware.
- Inaccurate date/time after power-off can suggest a weak CMOS/RTC battery.
- Crashes/sluggishness can be software or hardware; corroborate with diagnostics/events/temperature/memory/storage evidence.

# 5. At work
A workstation shuts down only during heavy rendering and CPU temperature rises abnormally before shutdown. That evidence makes thermal investigation stronger than a random OS reinstall.

# 6. Commands / Tools
Firmware diagnostics, POST codes, vendor hardware diagnostics, memory tests, temperature/health monitoring, known-good components, and Module 3/4 Windows evidence.

# 7. Interview / Explain
Explain why minimal boot is useful and why changing one component at a time matters.

# 8. Quick Check
Use Module 8 Quick Check 5: M8Q018, M8Q019, M8Q020, M8Q021.
