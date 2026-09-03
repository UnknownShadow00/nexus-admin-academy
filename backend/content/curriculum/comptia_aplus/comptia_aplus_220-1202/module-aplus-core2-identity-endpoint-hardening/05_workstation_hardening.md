---
lesson_key: lesson.aplus.security.workstation_hardening
title: Workstation Hardening & Account Hygiene
certification_version: comptia_aplus_220-1202
domain: '2.0'
module: module.aplus.core2.identity_endpoint_hardening
lesson_order: 5
importance: job_critical
learning_relationship: new
objectives:
- '2.7'
estimated_minutes: 30
status: published
summary: Apply practical hardening controls that reduce avoidable endpoint risk.
quick_check:
  title: "Quick Check \u2014 Workstation Hardening & Account Hygiene"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M13Q017
  - M13Q018
  - M13Q019
  - M13Q020
---
# Workstation Hardening & Account Hygiene

## 1. What is this?
Apply practical hardening controls that reduce avoidable endpoint risk.

## 2. Why does an IT worker care?
Security tickets often look like ordinary access or application problems. The technician must restore approved work without weakening controls, granting unnecessary privilege, or destroying useful evidence.

## 3. Watch / Read
Complete the required resource **resource.aplus.m13.security_best_practices** before the Quick Check. Use optional references only when you need another explanation or a vendor procedure.

## 4. What you actually need to remember
- Use strong organizational password/passphrase policy and a password manager instead of password reuse.
- Lock the screen and enforce appropriate idle/session controls on managed devices.
- Change or disable default administrative accounts according to policy; do not leave known defaults active.
- Disable unnecessary services/features and AutoRun/AutoPlay behavior where policy requires it.
- Use BIOS/UEFI passwords only within the organization's recovery/asset-management process.
- Account lockout, expiration, failed-attempt limits, and least privilege reduce abuse but must align with policy and supportability.
- Hardening is not 'turn everything off'; it is risk reduction while preserving the approved business function.

## 5. At work
- Audit settings before changing them so you can distinguish policy drift from an intentional configuration.
- If the required change conflicts with policy, document and escalate instead of silently weakening the baseline.

## 6. Commands / Tools
- Windows Security
- Local/managed policy views
- Services console
- Startup/AutoRun settings
- Firmware security settings where authorized

## 7. Interview / Explain
Name four workstation-hardening controls and explain why each reduces risk.

## 8. Quick Check
- `M13Q017`
- `M13Q018`
- `M13Q019`
- `M13Q020`
