---
lesson_key: lesson.aplus.security.encryption
title: 'Protecting Data at Rest: BitLocker, BitLocker To Go & EFS'
certification_version: comptia_aplus_220-1202
domain: '2.0'
module: module.aplus.core2.identity_endpoint_hardening
lesson_order: 4
importance: job_critical
learning_relationship: review
objectives:
- '2.2'
- '2.7'
estimated_minutes: 25
status: published
summary: Choose the right Windows encryption scope and protect recovery material.
quick_check:
  title: "Quick Check \u2014 Protecting Data at Rest: BitLocker, BitLocker To Go &\
    \ EFS"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M13Q013
  - M13Q014
  - M13Q015
  - M13Q016
---
# Protecting Data at Rest: BitLocker, BitLocker To Go & EFS

## 1. What is this?
Choose the right Windows encryption scope and protect recovery material.

## 2. Why does an IT worker care?
Security tickets often look like ordinary access or application problems. The technician must restore approved work without weakening controls, granting unnecessary privilege, or destroying useful evidence.

## 3. Watch / Read
Complete the required resource **resource.aplus.m13.bitlocker_overview** before the Quick Check. Use optional references only when you need another explanation or a vendor procedure.

## 4. What you actually need to remember
- BitLocker protects an entire supported volume and is used for full-volume data-at-rest protection.
- BitLocker To Go protects supported removable drives.
- EFS encrypts selected files/folders on supported NTFS volumes; it is not a substitute for full-volume encryption.
- Encryption protects data when storage is lost, stolen, or accessed offline; it does not automatically stop an already-authorized user.
- Recovery keys/certificates are sensitive. Store them only in the organization's approved recovery location.
- Never enable, disable, decrypt, or reset encryption casually during troubleshooting.

## 5. At work
- Before firmware, TPM, drive, or OS recovery work, confirm encryption state and recovery-key availability.
- For lost removable media, whether it was encrypted materially changes the incident response decision.

## 6. Commands / Tools
- manage-bde (recognition/approved use)
- Windows Settings / Control Panel BitLocker surfaces
- File/folder Advanced Attributes for EFS
- Approved recovery-key directory

## 7. Interview / Explain
Compare BitLocker, BitLocker To Go, and EFS in one minute.

## 8. Quick Check
- `M13Q013`
- `M13Q014`
- `M13Q015`
- `M13Q016`
