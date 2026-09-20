---
lesson_key: lesson.aplus.virtualization_cloud.vm_use_cases
title: Why Virtualize? VMs, Sandboxes & Application Isolation
certification_version: comptia_aplus_220-1201
domain: '4.0'
module: module.aplus.core1.virtualization_cloud_foundations
lesson_order: 1
importance: working_knowledge
learning_relationship: new
objectives:
- '4.1'
estimated_minutes: 30
status: published
summary: Why Virtualize? VMs, Sandboxes & Application Isolation
quick_check:
  title: "Quick Check \u2014 Why Virtualize? VMs, Sandboxes & Application Isolation"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M10Q001
  - M10Q002
  - M10Q003
  - M10Q025
---

# Why Virtualize? VMs, Sandboxes & Application Isolation

## 1. What is this?
Virtualization lets one physical computer provide isolated software environments. A virtual machine (VM) behaves like a separate computer with its own guest operating system. A sandbox is a temporary isolated environment. Application virtualization can isolate or deliver an application without rebuilding the whole workstation.

## 2. Why does an IT worker care?
Support technicians encounter test VMs, Windows Sandbox, virtual desktops, and legacy applications. The useful skill is deciding what isolation solves and where the workload actually runs.

## 3. Watch / Read
**Required:** Professor Messer — *Virtualization Concepts (220-1201)*
https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/virtualization-concepts-220-1201/

**Optional:** Microsoft — *Windows Sandbox*
https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/

## 4. What you actually need to remember
- VM = isolated software-defined computer with a guest OS.
- Sandbox = temporary/disposable isolated environment.
- Test/development and legacy/cross-platform software are valid virtualization use cases.
- Application virtualization focuses on application isolation/delivery.
- Isolation reduces risk but does not make unsafe software trustworthy.

## 5. At work
An old accounting utility is not approved for the production image. A disposable sandbox or test VM is safer than installing it directly on the employee’s daily workstation.

## 6. Commands / Tools
Check **Task Manager → Performance → CPU**, `systeminfo`, supported Windows edition, and vendor/OS documentation. Do not enable firmware settings or install a hypervisor without authorization.

## 7. Interview / Explain
Explain when you would use a VM or sandbox instead of installing software directly on a production PC.

## 8. Quick Check
Use bank questions **M10Q001, M10Q002, M10Q003, M10Q025**.

