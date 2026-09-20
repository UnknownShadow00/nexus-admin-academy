---
lesson_key: lesson.aplus.core1.hardware_support.power
title: Selecting and Replacing a Power Supply
certification_version: comptia_aplus_220-1201
domain: "3.0"
module: module.aplus.core1.hardware_support
importance: job_critical
learning_relationship: new
objectives: ["3.5"]
estimated_minutes: 15
status: published
source_name: "CompTIA A+ 220-1201 objective 3.5; adapted from Nexus legacy Computer Power lesson"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

A PSU converts wall AC into regulated DC rails used by the motherboard, CPU,
drives, and cards. Replacements must match form factor, input, wattage,
connectors, and the system's actual load.

## 2. Why does an IT worker care?

An undersized or wrongly connected PSU causes no-power, restart, and under-load
failures. The PSU contains hazardous capacitors and is never opened for repair.

## 3. Watch / read

- Professor Messer — Computer Power (220-1201). *(required)*

## 4. What you need to remember

- Add component demand and leave sensible headroom; wattage is not the only check.
- Confirm 24-pin board, CPU power, PCIe, and SATA connectors.
- Modular means detachable cables; use only cables approved for that exact PSU.
- Confirm local input voltage where a manual selector exists.
- Disconnect mains, discharge, label, replace, then verify idle and load behavior.

## 5. Real workplace example

A PC restarts only during graphics work. The replacement PSU must cover the
GPU load and supply its PCIe connectors—not just fit the case.

## 6. Commands / tools

Use vendor specifications, an approved PSU tester only within training and
policy, and firmware hardware logs. Do not open or probe inside the PSU enclosure.

## 7. Interview / example

**Why not reuse a modular cable from another PSU?** Pinouts are not universally
standard at the PSU end and an incorrect cable can destroy components.

## 8. Quick Check

Five formative questions mapped to objective 3.5.
