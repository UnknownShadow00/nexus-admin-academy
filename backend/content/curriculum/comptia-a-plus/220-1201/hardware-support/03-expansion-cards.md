---
lesson_key: lesson.aplus.core1.hardware_support.expansion_cards
title: Expansion Cards and Internal Connections
certification_version: comptia_aplus_220-1201
domain: "3.0"
module: module.aplus.core1.hardware_support
importance: working_knowledge
learning_relationship: new
objectives: ["3.4"]
estimated_minutes: 12
status: published
source_name: "CompTIA A+ 220-1201 objective 3.4; adapted from Nexus legacy Expansion Cards lesson"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

PCI Express slots accept graphics, network, storage-controller, capture, and
sound cards. Slots have lane sizes such as x1 and x16; some cards also require
PSU power or external antennas/cables.

## 2. Why does an IT worker care?

An upgrade fails if the case, slot, lane availability, power budget, driver,
or connector is wrong—even when the card itself works.

## 3. Watch / read

- Professor Messer — Expansion Cards (220-1201). *(required)*

## 4. What you need to remember

- Check physical clearance, compatible slot, electrical lane availability, and
  power connectors. A slot can be x16 in length but wired for fewer lanes.
- Seat evenly, secure the bracket, reconnect required power, then install an approved driver.
- Confirm the old device is not merely disabled or misconfigured first.
- Verify in Device Manager and with the user's original task.

## 5. Real workplace example

A GPU is detected but crashes under load because its auxiliary power connector
was omitted. Power is corrected and the original workload is retested.

## 6. Commands / tools

Use Device Manager, `msinfo32`, vendor documentation, ESD protection, and a
known-good card where approved.

## 7. Interview / example

**What checks come before installing an expansion card?** Business need,
compatibility, clearance, power, driver support, ESD controls, and rollback.

## 8. Quick Check

Four formative questions mapped to objective 3.4.
