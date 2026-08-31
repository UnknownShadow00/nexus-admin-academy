---
lesson_key: lesson.aplus.windows_admin.client_networking
title: Windows Client Networking, Shares & Mapped Drives
certification_version: comptia_aplus_220-1202
domain: '1.0'
module: module.aplus.core2.windows_admin_cli_networking
lesson_order: 5
importance: job_critical
learning_relationship: deep_dive
objectives:
- '1.7'
estimated_minutes: 35
status: published
summary: Windows Client Networking, Shares & Mapped Drives
quick_check:
  title: "Quick Check \u2014 Windows Client Networking, Shares & Mapped Drives"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M11Q013
  - M11Q014
  - M11Q015
  - M11Q033
---

# Windows Client Networking, Shares & Mapped Drives

## 1. What is this?
Windows clients may participate in a workgroup or a managed domain and connect to shared folders, printers, file servers, and mapped drives. The same underlying network can work while one path, credential, mapping, or name fails.

## 2. Why does an IT worker care?
Mapped drives and shared resources are everyday help-desk work. Technicians need to separate “the network is down” from “this saved mapping points to the wrong place” or “the user lacks access.”

## 3. Watch / Read
**Required:** Professor Messer — *Windows Network Connections (220-1202)*  
https://www.professormesser.com/free-a-plus-training/220-1202/220-1202-video/windows-network-connections-220-1202/

**Optional:** Microsoft Learn — *Windows commands* (`net use` reference)  
https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands

## 4. What you actually need to remember
- Domain and workgroup are different management/trust models.
- UNC paths such as `\\server\share` identify network shares directly.
- A mapped drive assigns a drive letter to a network path; the mapping can become stale even if the server is healthy.
- `net use` can show and manage mapped resources.
- Verify the actual server/share path and permissions before remapping.
- A direct UNC test is useful evidence: if it works while the mapped drive fails, the mapping itself deserves attention.

## 5. At work
After VPN reconnect, `\\files01\Projects` opens but `P:` fails. `net use` reveals `P:` still targets a retired server. That is a saved-mapping issue, not proof of a firewall outage.

## 6. Commands / Tools
Use File Explorer network paths, `net use`, `ping`/`nslookup` only when needed, and the organization's approved share documentation. Never “fix” access by granting broader permissions without authorization.

## 7. Interview / Explain
Explain how you would distinguish a bad mapped drive from a file-server outage.

## 8. Quick Check
Use bank questions **M11Q013, M11Q014, M11Q015, M11Q033**.

