---
lesson_key: lesson.aplus.cross_platform.linux_files_config
title: Linux Files, Permissions, Components & Configuration
certification_version: comptia_aplus_220-1202
domain: '1.0'
module: module.aplus.core2.cross_platform_app_cloud_support
lesson_order: 3
importance: job_critical
learning_relationship: new
objectives:
- '1.9'
estimated_minutes: 40
status: published
summary: Linux Files, Permissions, Components & Configuration
quick_check:
  title: "Quick Check \u2014 Linux Files, Permissions, Components & Configuration"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M12Q005
  - M12Q006
  - M12Q007
  - M12Q026
---

# Linux Files, Permissions, Components & Configuration

## 1. What is this?
Linux support often begins in a terminal. A+ expects basic file commands, permissions, key configuration files, and high-level OS components such as the kernel, bootloader, and systemd.

## 2. Why does an IT worker care?
A technician should be able to locate a file, identify permissions, and read the right configuration before editing anything. Many Linux incidents can be narrowed quickly with a few safe commands.

## 3. Watch / Read
**Required:** Professor Messer — *Linux (220-1202)*  
https://www.professormesser.com/free-a-plus-training/220-1202/220-1202-video/linux-220-1202/

**Optional:** Professor Messer — *Linux Commands Part 1 (220-1202)*  
https://www.professormesser.com/free-a-plus-training/220-1202/220-1202-video/linux-commands-part-1-220-1202/

## 4. What you actually need to remember
- Navigation/evidence: `pwd`, `ls`, `find`, `grep`, `cat`.
- File changes: `cp`, `mv`, `rm`; verify path before write/delete actions.
- Permissions/ownership: `chmod`, `chown`.
- Important files: `/etc/passwd`, `/etc/shadow`, `/etc/hosts`, `/etc/fstab`, `/etc/resolv.conf`.
- `systemd` manages services/system startup on many distributions; the kernel is the OS core; the bootloader starts the OS boot process.
- Read first. Do not edit sensitive configuration just because you found it.

## 5. At work
A Linux workstation resolves one internal hostname incorrectly. Reading `/etc/hosts` and resolver configuration is more useful than reinstalling the network adapter.

## 6. Commands / Tools
Practice read-only: `pwd`, `ls`, `cat /etc/hosts`, `grep`, `find`. Use a disposable folder for `cp`, `mv`, or permissions practice.

## 7. Interview / Explain
Explain why `/etc/hosts` and `/etc/resolv.conf` answer different troubleshooting questions.

## 8. Quick Check
Use bank questions **M12Q005, M12Q006, M12Q007, M12Q026**.
