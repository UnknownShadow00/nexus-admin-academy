---
lesson_key: lesson.aplus.security.windows_defender_firewall
title: Windows Defender, Firewall, Accounts & UAC
certification_version: comptia_aplus_220-1202
domain: '2.0'
module: module.aplus.core2.identity_endpoint_hardening
lesson_order: 2
importance: job_critical
learning_relationship: deep_dive
objectives:
- '2.2'
estimated_minutes: 30
status: published
summary: Use Windows built-in security controls without turning protection off as
  a troubleshooting shortcut.
quick_check:
  title: "Quick Check \u2014 Windows Defender, Firewall, Accounts & UAC"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M13Q005
  - M13Q006
  - M13Q007
  - M13Q008
---
# Windows Defender, Firewall, Accounts & UAC

## 1. What is this?
Use Windows built-in security controls without turning protection off as a troubleshooting shortcut.

## 2. Why does an IT worker care?
Security tickets often look like ordinary access or application problems. The technician must restore approved work without weakening controls, granting unnecessary privilege, or destroying useful evidence.

## 3. Watch / Read
Complete the required resource **resource.aplus.m13.defender_antivirus** before the Quick Check. Use optional references only when you need another explanation or a vendor procedure.

## 4. What you actually need to remember
- Microsoft Defender Antivirus provides built-in antimalware protection; signatures/security intelligence must stay current.
- Windows Firewall controls network traffic by profile and rule. A blocked application does not justify disabling the firewall globally.
- Standard users should remain standard users. Use approved elevation for administrative tasks.
- UAC is a security boundary prompt/consent mechanism; treat unexpected elevation prompts as evidence, not an annoyance to disable.
- Local accounts, Microsoft accounts, and domain identities have different management boundaries.
- Account lockout, sign-in options, and group membership should be inspected before reset or privilege changes.

## 5. At work
- Collect the exact Defender/firewall alert, app name, path, publisher, network profile, and user context before changing rules.
- Prefer the narrowest authorized firewall rule or managed deployment instead of disabling a whole protection layer.
- If a user needs admin rights only for one approved action, use the approved temporary/elevation process.

## 6. Commands / Tools
- Windows Security
- Virus & threat protection
- Windows Defender Firewall with Advanced Security
- Computer Management / Local Users and Groups (where available)
- UAC prompts

## 7. Interview / Explain
A trusted app is blocked. Explain why disabling Defender or the firewall is usually the wrong first fix.

## 8. Quick Check
- `M13Q005`
- `M13Q006`
- `M13Q007`
- `M13Q008`
