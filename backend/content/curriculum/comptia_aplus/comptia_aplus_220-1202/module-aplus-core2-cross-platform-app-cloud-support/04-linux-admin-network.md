---
lesson_key: lesson.aplus.cross_platform.linux_admin_network
title: Linux Administration, Packages, Storage & Network Evidence
certification_version: comptia_aplus_220-1202
domain: '1.0'
module: module.aplus.core2.cross_platform_app_cloud_support
lesson_order: 4
importance: job_critical
learning_relationship: new
objectives:
- '1.9'
estimated_minutes: 40
status: published
summary: Linux Administration, Packages, Storage & Network Evidence
quick_check:
  title: "Quick Check \u2014 Linux Administration, Packages, Storage & Network Evidence"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M12Q008
  - M12Q009
  - M12Q010
  - M12Q011
---

# Linux Administration, Packages, Storage & Network Evidence

## 1. What is this?
Linux includes package managers, administrative privilege tools, filesystem checks/mounting, process/resource tools, and networking commands. A+ expects recognition and safe use—not deep Linux administration.

## 2. Why does an IT worker care?
Commands such as `df`, `ps`, `top`, `ip`, `ping`, `dig`, and `traceroute` collect excellent evidence. `sudo`, package installation, `mount`, and `fsck` can change system state and deserve more care.

## 3. Watch / Read
**Required:** Professor Messer — *Linux Commands Part 2 (220-1202)*  
https://www.professormesser.com/free-a-plus-training/220-1202/220-1202-video/linux-commands-part-2-220-1202/

**Optional:** Ubuntu — *The Linux command line for beginners*  
https://ubuntu.com/tutorials/command-line-for-beginners

## 4. What you actually need to remember
- `sudo` runs an allowed command with elevated privileges; use only when needed.
- `su` changes user context; root has full control.
- `apt` and `dnf` are package managers used by different distribution families.
- `df` reports filesystem free space; `du` estimates file/directory usage.
- `ps`/`top` show process information; `man` provides local documentation.
- `ip`, `ping`, `curl`, `dig`, and `traceroute` provide network evidence.
- `mount` attaches filesystems; `fsck` checks/repairs filesystems and should be used with appropriate procedure.

## 5. At work
A Linux endpoint reports “disk full.” Check `df` first. If one filesystem is nearly full, then use `du` carefully to identify large directories before deleting anything.

## 6. Commands / Tools
`df -h`, `du`, `ps`, `top`, `ip`, `ping`, `dig`, `traceroute`, `man`, plus package-manager queries where authorized.

## 7. Interview / Explain
Explain `sudo` in plain language and why you should not prepend it to every command.

## 8. Quick Check
Use bank questions **M12Q008, M12Q009, M12Q010, M12Q011**.
