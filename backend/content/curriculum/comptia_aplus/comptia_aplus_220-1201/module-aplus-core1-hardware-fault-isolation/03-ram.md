---
lesson_key: lesson.aplus.hardware.ram
title: 'RAM: DIMMs, SO-DIMMs, DDR, ECC & Channel Configurations'
certification_version: comptia_aplus_220-1201
domain: '3.0'
module: module.aplus.core1.hardware_fault_isolation
lesson_order: 3
importance: working_knowledge
learning_relationship: deep_dive
objectives:
- '3.3'
- '5.1'
estimated_minutes: 40
status: published
summary: Recognize RAM form factors/features and connect memory symptoms to safe reseat/test/isolation
  methods.
quick_check:
  title: "Quick Check \u2014 RAM: DIMMs, SO-DIMMs, DDR, ECC & Channel Configurations"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M8Q010
  - M8Q011
  - M8Q012
  - M8Q013
---

# 1. What is this?
RAM is active working memory. Desktop systems commonly use DIMMs; laptops/small systems often use SO-DIMMs. A+ expects DDR generations, ECC vs non-ECC, and single/dual/triple/quad-channel concepts.

# 2. Why does an IT worker care?
Wrong RAM may not fit or boot. Failing/mis-seated RAM can create POST errors, crashes, instability, or missing capacity. Technicians need to verify compatibility before ordering and isolate one variable at a time after installation.

# 3. Watch / Read
**Required:** Professor Messer — *An Overview of Memory* and *Memory Technologies (220-1201)*.

# 4. What you actually need to remember
- DIMM vs SO-DIMM is a physical/form-factor distinction.
- DDR generations are electrically/keyed differently; "same GB" does not mean compatible.
- ECC memory can detect/correct certain memory errors when platform support exists; non-ECC does not provide the same correction behavior.
- Multi-channel configurations can improve memory bandwidth when the motherboard/CPU and population rules support them.
- Check motherboard/system documentation for supported generation, module type/capacity, speed behavior, and slot population.

# 5. At work
A PC reports half its expected memory after an upgrade. Verify module detection/slot population and reseat/test modules one at a time before concluding the motherboard is bad.

# 6. Commands / Tools
Firmware memory inventory, OS system information/Task Manager, built-in memory diagnostics, and known-good supported modules where policy permits.

# 7. Interview / Explain
Explain ECC vs non-ECC and why a technician still has to check platform support.

# 8. Quick Check
Use Module 8 Quick Check 3: M8Q010, M8Q011, M8Q012, M8Q013.
