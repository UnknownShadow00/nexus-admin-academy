---
lesson_key: lesson.aplus.core2.windows_support_tools.os_filesystems
title: Operating Systems, Filesystems and Support Boundaries
certification_version: comptia_aplus_220-1202
domain: "1.0"
module: module.aplus.core2.windows_support_tools
importance: working_knowledge
learning_relationship: new
objectives: ["1.1"]
estimated_minutes: 13
status: published
source_name: "CompTIA A+ 220-1202 objective 1.1"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

An operating system manages hardware, applications, users, storage, and
security. Workstations commonly use Windows, macOS, ChromeOS, or Linux; phones
and tablets use mobile operating systems. Filesystems such as NTFS, exFAT,
APFS, and ext4 organise stored data and provide different capabilities.

## 2. Why does an IT worker care?

The OS version, edition, architecture, filesystem, and vendor support status
determine which tools, software, security fixes, and recovery paths are valid.

## 3. Watch / read

- Microsoft — Windows release health and lifecycle documentation. *(required)*

## 4. What you need to remember

- Identify OS/version before changing anything.
- NTFS supports Windows permissions and features; exFAT often improves
  removable-drive compatibility, but the destination device must still be checked.
- A vendor lifecycle end means security and support risk, not instant hardware failure.
- Back up before conversion, repartitioning, or reinstalling.

## 5. Real workplace example

An app requires a supported 64-bit Windows release. The technician records the
current version and lifecycle state before proposing an upgrade.

## 6. Commands / tools

Use `winver`, `systeminfo`, Settings > System > About, and Disk Management.

## 7. Interview / example

**Why identify the OS before troubleshooting?** Commands, paths, drivers,
permissions, and vendor support differ, so the same symptom can require a different safe action.

## 8. Quick Check

Four formative questions mapped to objective 1.1.
