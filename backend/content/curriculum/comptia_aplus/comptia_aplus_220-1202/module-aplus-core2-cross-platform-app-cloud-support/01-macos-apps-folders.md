---
lesson_key: lesson.aplus.cross_platform.macos_apps_folders
title: macOS Apps, File Types & System Folders
certification_version: comptia_aplus_220-1202
domain: '1.0'
module: module.aplus.core2.cross_platform_app_cloud_support
lesson_order: 1
importance: working_knowledge
learning_relationship: new
objectives:
- '1.8'
estimated_minutes: 35
status: published
summary: macOS Apps, File Types & System Folders
quick_check:
  title: "Quick Check \u2014 macOS Apps, File Types & System Folders"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M12Q001
  - M12Q002
  - M12Q003
  - M12Q021
---

# macOS Apps, File Types & System Folders

## 1. What is this?
macOS uses familiar desktop ideas but different application packages and system locations. `.dmg` is commonly a disk image, `.pkg` an installer package, and `.app` an application bundle. Important locations include `/Applications`, `/Users`, `/Library`, `/System`, and a user’s `~/Library`.

## 2. Why does an IT worker care?
A technician must know where the application and user data live before reinstalling, deleting, or escalating. Windows assumptions such as “look for setup.exe” do not transfer directly to a Mac.

## 3. Watch / Read
**Required:** Professor Messer — *macOS Overview (220-1202)*  
https://www.professormesser.com/free-a-plus-training/220-1202/220-1202-video/macos-overview-220-1202/

## 4. What you actually need to remember
- `.dmg` = mountable Apple disk image; `.pkg` = installer package; `.app` = application bundle.
- `/Applications` is a standard application location.
- `/Users` contains user home directories.
- `/Library` can hold shared support files; `~/Library` is user-specific.
- `/System` contains operating-system files; do not casually modify it.
- App Store and vendor-supported uninstall methods are preferable to deleting random support files.

## 5. At work
A user says an app “disappeared.” First confirm whether the `.app` exists in `/Applications`, whether the account can launch it, and whether the issue is app-specific before reinstalling anything.

## 6. Commands / Tools
Finder, Applications folder, App Store, Spotlight, and Terminal for read-only checks when appropriate.

## 7. Interview / Explain
Explain the difference between `.dmg`, `.pkg`, and `.app` to a Windows-focused technician.

## 8. Quick Check
Use bank questions **M12Q001, M12Q002, M12Q003, M12Q021**.
