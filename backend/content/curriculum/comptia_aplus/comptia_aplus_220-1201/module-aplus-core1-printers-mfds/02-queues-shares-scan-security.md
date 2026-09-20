---
lesson_key: lesson.aplus.printers.queues_shares_scan_security
title: Queues, Shares, Secure Print & Scanning
certification_version: comptia_aplus_220-1201
domain: '3.0'
module: module.aplus.core1.printers_mfds
lesson_order: 2
importance: job_critical
learning_relationship: deep_dive
objectives:
- '3.7'
- '5.6'
estimated_minutes: 40
status: published
summary: Support print queues/shares, secure release, audit features, and scan destinations
  without exposing confidential output.
quick_check:
  title: "Quick Check \u2014 Queues, Shares, Secure Print & Scanning"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M9Q005
  - M9Q006
  - M9Q007
  - M9Q008
---

# 1. What is this?
A print job travels through software, driver/spooler/queue, connectivity, and the printer. Organizations may share printers through a print server, require PIN/badge secure release, log/audit printing, and configure scanning to email, SMB/file shares, or cloud destinations.

# 2. Why does an IT worker care?
A printer that can print a hardware configuration page may still fail from one workstation because the problem is upstream. Secure printing also matters: sensitive documents should not sit unattended in an output tray.

# 3. Watch / Read
**Required:** review the secure print, printer sharing, and scanning sections of Messer's *Multifunction Devices*.  
**Optional vendor/OS reference:** Microsoft printer connection/queue troubleshooting guidance.

# 4. What you actually need to remember
- **Queue/spooler:** holds/manages jobs before they reach the printer.
- **Printer share/print server:** centralizes access/queues/drivers in many environments.
- **Secure print:** may hold jobs until PIN/badge/user release.
- **Audit logs:** help track print activity where enabled.
- **Scan to email:** depends on mail/service configuration; **scan to SMB** depends on network path/auth/permissions; cloud scan depends on the configured cloud service/account.
- **ADF** handles multi-page feeding; **flatbed** is useful for single/fragile/bound originals.

# 5. At work
A user says scanning "is broken." Copying works, printing works, but scan-to-SMB returns access denied. The scanner engine is probably not your first fault domain; investigate network path/auth/permissions and approved destination configuration.

# 6. Commands / Tools
Windows queue/service tools, test page, print server/share settings, MFD status/configuration pages, and Module 7 network tests. Follow least privilege for scan-share credentials.

# 7. Interview / Explain
Explain why printing a printer-internal configuration page and an OS test page are useful different tests.

# 8. Quick Check
Use Module 9 Quick Check 2: M9Q005, M9Q006, M9Q007, M9Q008.
