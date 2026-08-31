---
lesson_key: lesson.aplus.windows_admin.cli_diagnostics_policy
title: 'Windows CLI: Network, Disk, Repair & Policy Evidence'
certification_version: comptia_aplus_220-1202
domain: '1.0'
module: module.aplus.core2.windows_admin_cli_networking
lesson_order: 4
importance: job_critical
learning_relationship: deep_dive
objectives:
- '1.5'
estimated_minutes: 35
status: published
summary: 'Windows CLI: Network, Disk, Repair & Policy Evidence'
quick_check:
  title: "Quick Check \u2014 Windows CLI: Network, Disk, Repair & Policy Evidence"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M11Q010
  - M11Q011
  - M11Q012
  - M11Q032
---

# Windows CLI: Network, Disk, Repair & Policy Evidence

## 1. What is this?
Windows command-line tools can test network reachability/name resolution, inspect connections, check storage, verify system files, and show applied Group Policy. The goal is evidence-driven troubleshooting, not command spam.

## 2. Why does an IT worker care?
These commands help isolate where a failure lives. A successful IP test with failed name resolution points in a different direction than total connectivity loss. `gpresult` can show whether a policy actually applied before someone forces or edits policy.

## 3. Watch / Read
**Required:** Professor Messer — *The Windows Network Command Line (220-1202)*  
https://www.professormesser.com/free-a-plus-training/220-1202/220-1202-video/the-windows-network-command-line-220-1202/

**Optional:** Microsoft Learn — *gpresult*  
https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/gpresult

## 4. What you actually need to remember
- Network evidence: `ipconfig`, `ping`, `netstat`, `nslookup`, `tracert`, `pathping`, `net use`.
- Policy: `gpresult` shows resultant policy; `gpupdate` requests a policy refresh.
- Repair: `sfc` checks protected Windows system files.
- Disk: `chkdsk` checks filesystem/disk state; `diskpart` and `format` can be destructive.
- Use output to narrow the fault before making changes.
- Earlier Nexus networking remains the foundation; this lesson focuses on Windows command choice and evidence.

## 5. At work
A PC can ping a known server IP but `nslookup intranet.example` fails. That supports a DNS/name-resolution hypothesis. Reinstalling the NIC driver would not be the evidence-led first step.

## 6. Commands / Tools
Use `ipconfig /all`, `nslookup`, `tracert`, `gpresult /r`, and `sfc /scannow` only when appropriate and authorized. Capture relevant output, not entire dumps full of unrelated data.

## 7. Interview / Explain
Explain the difference between `gpresult` and `gpupdate`, and why one is evidence while the other requests a change/refresh.

## 8. Quick Check
Use bank questions **M11Q010, M11Q011, M11Q012, M11Q032**.

