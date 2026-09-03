---
lesson_key: lesson.aplus.security.permissions_ad
title: Permissions, Groups & Active Directory Security
certification_version: comptia_aplus_220-1202
domain: '2.0'
module: module.aplus.core2.identity_endpoint_hardening
lesson_order: 3
importance: job_critical
learning_relationship: deep_dive
objectives:
- '2.2'
estimated_minutes: 30
status: published
summary: Reason about Windows file access, inheritance, groups, and directory-based
  security without guessing.
quick_check:
  title: "Quick Check \u2014 Permissions, Groups & Active Directory Security"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M13Q009
  - M13Q010
  - M13Q011
  - M13Q012
---
# Permissions, Groups & Active Directory Security

## 1. What is this?
Reason about Windows file access, inheritance, groups, and directory-based security without guessing.

## 2. Why does an IT worker care?
Security tickets often look like ordinary access or application problems. The technician must restore approved work without weakening controls, granting unnecessary privilege, or destroying useful evidence.

## 3. Watch / Read
Complete the required resource **resource.aplus.m13.active_directory** before the Quick Check. Use optional references only when you need another explanation or a vendor procedure.

## 4. What you actually need to remember
- NTFS permissions apply to files/folders on NTFS volumes; share permissions apply when the resource is accessed through a network share.
- When both NTFS and share permissions apply, the effective access can be constrained by either layer.
- Permissions commonly inherit from parent folders unless inheritance is intentionally changed.
- Group-based access is easier to audit and maintain than one-off permissions for individual users.
- Active Directory centralizes identities, computers, groups, policies, and access relationships in many business environments.
- Support technicians should verify the intended group/role and approval before changing directory membership.

## 5. At work
- Compare the affected user with a known-good peer in the same approved role.
- Inspect share path, group membership, inheritance, and effective permissions before adding new access.
- Do not grant Full Control simply because Read/Modify troubleshooting is taking too long.

## 6. Commands / Tools
- File/folder Properties > Security
- Share permissions
- Active Directory Users and Computers or approved directory tool
- whoami /groups
- gpresult when policy context matters

## 7. Interview / Explain
Explain why a user can be allowed by the share but still denied by NTFS permissions.

## 8. Quick Check
- `M13Q009`
- `M13Q010`
- `M13Q011`
- `M13Q012`
