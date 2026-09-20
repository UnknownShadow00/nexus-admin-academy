---
lesson_key: lesson.aplus.windows_admin.admin_consoles
title: Windows Administrative Consoles & Evidence
certification_version: comptia_aplus_220-1202
domain: '1.0'
module: module.aplus.core2.windows_admin_cli_networking
lesson_order: 2
importance: job_critical
learning_relationship: deep_dive
objectives:
- '1.4'
estimated_minutes: 35
status: published
summary: Windows Administrative Consoles & Evidence
quick_check:
  title: "Quick Check \u2014 Windows Administrative Consoles & Evidence"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M11Q004
  - M11Q005
  - M11Q006
  - M11Q030
---

# Windows Administrative Consoles & Evidence

## 1. What is this?
Windows includes built-in consoles for looking at events, disks, devices, scheduled tasks, certificates, performance, local accounts, and policy. The important skill is choosing the tool that matches the symptom.

## 2. Why does an IT worker care?
Good technicians collect evidence before changing settings. Event Viewer can show when a failure occurred; Device Manager can show a hardware/driver state; Disk Management can show whether storage is present even when File Explorer does not.

## 3. Watch / Read
**Required:** Professor Messer — *The Microsoft Management Console (220-1202)*  
https://www.professormesser.com/free-a-plus-training/220-1202/220-1202-video/the-microsoft-management-console-220-1202/

**Optional:** Professor Messer — *Additional Windows Tools (220-1202)*  
https://www.professormesser.com/free-a-plus-training/220-1202/220-1202-video/additional-windows-tools-220-1202/

## 4. What you actually need to remember
- Task Manager: processes, performance, startup, users, services.
- Event Viewer: time-correlated logs and errors.
- Device Manager: device and driver state.
- Disk Management: partitions, volumes, drive letters, disk visibility.
- Task Scheduler: scheduled triggers/actions and history.
- Certificate Manager: current-user certificate store.
- Performance Monitor/Resource Monitor: resource evidence over time or in detail.
- `msinfo32`: system inventory/configuration.
- Registry Editor and policy tools are powerful—do not make speculative changes.

## 5. At work
A laptop loses a USB device after sleep. Device Manager is a better first evidence source than Registry Editor. A recurring task fails nightly at 2 a.m.; Task Scheduler and Event Viewer are better than restarting the PC.

## 6. Commands / Tools
Common launch commands: `eventvwr.msc`, `devmgmt.msc`, `diskmgmt.msc`, `taskschd.msc`, `certmgr.msc`, `perfmon.msc`, `msinfo32`, `resmon`.

## 7. Interview / Explain
Given a symptom, explain which Windows console you would open first and what evidence you expect to find.

## 8. Quick Check
Use bank questions **M11Q004, M11Q005, M11Q006, M11Q030**.

