---
lesson_key: lesson.aplus.mobile.mdm_sync
title: MDM, BYOD, Corporate Devices & Business Sync
certification_version: comptia_aplus_220-1201
domain: '1.0'
module: module.aplus.core1.mobile_device_support
lesson_order: 4
importance: working_knowledge
learning_relationship: new
objectives:
- '1.3'
estimated_minutes: 35
status: ready
summary: Understand A+-level mobile device management, corporate vs BYOD ownership,
  policy enforcement, corporate apps, and business synchronization.
quick_check:
  title: "Quick Check \u2014 MDM, BYOD, Corporate Devices & Business Sync"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - Q021
  - Q022
  - Q023
  - Q024
---

# Lesson 4 — MDM, BYOD, Corporate Devices & Business Sync

## 1. What is this?
**Mobile device management (MDM)** lets an organization centrally manage device configuration, policy, and corporate applications. A+ expects the concept—not deep Intune administration.

Two common ownership situations:
- **Corporate device:** organization owns and manages the device.
- **BYOD:** the employee owns the device but uses it for work under the organization's allowed management model.

Business data may synchronize across **mail, calendar, contacts, and cloud storage**.

## 2. Why does an IT worker care?
When a business app does not install, email does not sync, or a setting “keeps changing back,” the cause may be **management policy** rather than a broken phone.

A support technician should know where personal troubleshooting ends and managed-device policy begins.

## 3. Watch / Read
**Required:** Professor Messer — *Mobile Device Management (220-1201)* — 8:31  
https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/mobile-device-management-220-1201/

**Optional vendor reference:** Microsoft Learn — *Microsoft Intune core concepts*  
https://learn.microsoft.com/en-us/intune/intune-service/fundamentals/manage-apps

## 4. What you actually need to remember
At A+ depth, MDM can:
- apply device configurations
- enforce organizational policy
- deploy/manage corporate applications
- distinguish management expectations for corporate vs personal/BYOD devices
- influence access and synchronization behavior

For sync problems, separate:
1. **network access** — can the device reach the internet/service?
2. **account/session** — is the correct work account signed in?
3. **sync categories** — mail, calendar, contacts, cloud storage
4. **data limits** — data cap/data saver/restrictions where relevant
5. **management policy** — is MDM or another organizational control blocking/requiring something?
6. **application health** — version, permissions, storage, compatibility

Do not remove MDM enrollment or factory-reset a managed device just to “see if it works” without authorization.

Microsoft distinguishes full-device MDM from app-level management (MAM). That is useful workplace context, but **MAM is not an assessed term in this module**.

## 5. At work
A company phone has normal web access, but calendar and contacts stopped syncing while mail still updates. The technician does not replace hardware. They inspect the affected sync categories, work account, policy state, data restrictions, and application status.

## 6. Commands / Tools
- MDM/device-management status
- work account settings
- mail/calendar/contact sync settings
- app store/company portal or approved app catalog
- device compliance/configuration status where the technician has access
- ticket/asset record

## 7. Interview / Explain
**Prompt:** “What is MDM and why would a company use it?”

A strong answer mentions centralized device configuration, policy enforcement, corporate applications/data, and different expectations for corporate vs BYOD devices.

## 8. Quick Check
Use bank questions: **Q021, Q022, Q023, Q024**.
