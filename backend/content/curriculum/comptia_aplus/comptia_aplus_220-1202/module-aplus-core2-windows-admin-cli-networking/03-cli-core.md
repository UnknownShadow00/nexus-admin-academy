---
lesson_key: lesson.aplus.windows_admin.cli_core
title: 'Windows Command Line: Navigation, Files & Identity'
certification_version: comptia_aplus_220-1202
domain: '1.0'
module: module.aplus.core2.windows_admin_cli_networking
lesson_order: 3
importance: job_critical
learning_relationship: deep_dive
objectives:
- '1.5'
estimated_minutes: 35
status: published
summary: 'Windows Command Line: Navigation, Files & Identity'
quick_check:
  title: "Quick Check \u2014 Windows Command Line: Navigation, Files & Identity"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M11Q007
  - M11Q008
  - M11Q009
  - M11Q031
---

# Windows Command Line: Navigation, Files & Identity

## 1. What is this?
The Windows command line provides fast, repeatable ways to navigate, inspect identity/system information, and manage files. A support technician does not need to memorize every switch, but should know the right tool and how to ask it for help.

## 2. Why does an IT worker care?
Commands are excellent evidence. They can answer simple questions—where am I, which user is running, what host is this, what files exist—without clicking through several menus.

## 3. Watch / Read
**Required:** Professor Messer — *Windows Command-Line Tools (220-1202)*  
https://www.professormesser.com/free-a-plus-training/220-1202/220-1202-video/windows-command-line-tools-220-1202/

**Optional:** Microsoft Learn — *Windows commands*  
https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands

## 4. What you actually need to remember
- Navigation: `cd`, `dir`.
- File/folder work: `md`, `rmdir`, `robocopy`.
- Identity/system: `whoami`, `hostname`, `winver`, `net user`.
- Use `[command] /?` before guessing switches.
- `robocopy` is built for robust file copying; verify source/destination before running write operations.
- `format`, `diskpart`, delete operations, and broad account changes can be destructive—inspect first.

## 5. At work
A technician is unsure which workstation a remote session opened. `hostname` and `whoami` immediately confirm the machine and current security context before any change is made.

## 6. Commands / Tools
Practice: `cd`, `dir`, `whoami`, `hostname`, `winver`, and `robocopy /?`. Use a disposable folder for write practice.

## 7. Interview / Explain
Explain why a command's output can be more useful in a ticket than writing “I checked the PC.”

## 8. Quick Check
Use bank questions **M11Q007, M11Q008, M11Q009, M11Q031**.

