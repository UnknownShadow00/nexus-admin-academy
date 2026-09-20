---
lesson_key: lesson.aplus.virtualization_cloud.hypervisors_resources
title: Hypervisors, Host Resources & Safe VM Planning
certification_version: comptia_aplus_220-1201
domain: '4.0'
module: module.aplus.core1.virtualization_cloud_foundations
lesson_order: 2
importance: job_critical
learning_relationship: deep_dive
objectives:
- '4.1'
estimated_minutes: 30
status: published
summary: Hypervisors, Host Resources & Safe VM Planning
quick_check:
  title: "Quick Check \u2014 Hypervisors, Host Resources & Safe VM Planning"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M10Q004
  - M10Q005
  - M10Q006
  - M10Q026
---

# Hypervisors, Host Resources & Safe VM Planning

## 1. What is this?
A hypervisor creates and runs VMs. A **Type 1** hypervisor runs directly on hardware; a **Type 2** hypervisor runs on top of a host operating system. Every VM consumes real host CPU, memory, storage, and network resources.

## 2. Why does an IT worker care?
A slow or non-starting VM may be suffering from host resource pressure or a configuration problem, not a guest-OS failure. Support should collect evidence before adding resources or changing settings.

## 3. Watch / Read
**Required:** Microsoft — *Hyper-V host hardware requirements*
https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/host-hardware-requirements

**Optional:** Professor Messer — *Virtualization Services (220-1201)*
https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/virtualization-services-220-1201/

## 4. What you actually need to remember
- Type 1 runs on hardware; Type 2 runs on a host OS.
- Intel VT-x/AMD-V are hardware-assisted virtualization capabilities.
- CPU, RAM, storage, network, and security requirements all matter.
- Do not promise more VM capacity than the physical host can sustain.
- Virtual networking/storage still require normal security and capacity planning.

## 5. At work
A laptop has 8 GB RAM and the user requests three VMs configured for 4 GB each. Capacity planning comes before configuration.

## 6. Commands / Tools
`systeminfo`, Task Manager, firmware/UEFI status, free-storage checks, and hypervisor resource screens provide evidence. Production changes follow Module 5 approval/change discipline.

## 7. Interview / Explain
Explain Type 1 vs Type 2 and name two host resources that can limit VM performance.

## 8. Quick Check
Use bank questions **M10Q004, M10Q005, M10Q006, M10Q026**.

