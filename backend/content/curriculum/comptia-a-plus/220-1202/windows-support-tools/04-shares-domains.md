---
lesson_key: lesson.aplus.core2.windows_support_tools.shares_domains
title: Workgroups, Domains and Network Shares
certification_version: comptia_aplus_220-1202
domain: "1.0"
module: module.aplus.core2.windows_support_tools
importance: working_knowledge
learning_relationship: new
objectives: ["1.6"]
estimated_minutes: 13
status: published
source_name: "CompTIA A+ 220-1202 objective 1.6"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

A workgroup is peer-to-peer administration; a domain centrally manages
identities and policy. A network share exposes an approved folder using a UNC
path such as `\\fileserver\team` with both share and filesystem permissions.

## 2. Why does an IT worker care?

Access problems may be identity, permission, name-resolution, network, or
server issues. Changing permissions without evidence can create a breach.

## 3. Watch / read

- Microsoft — File sharing over a network in Windows. *(required)*

## 4. What you need to remember

- Confirm user, device, path, scope, and whether others are affected.
- A mapped drive is a shortcut; test its UNC path directly.
- Effective access is constrained by both share and NTFS permissions.
- Do not grant broad access merely to make a ticket disappear.

## 5. Real workplace example

One user loses a mapped drive while teammates work. The UNC path and identity
check distinguish a stale mapping from a server outage.

## 6. Commands / tools

Use File Explorer, `whoami`, `net use`, and approved directory/access tools.

## 7. Interview / example

**What do you check before changing share permissions?** Identity, business
approval, group membership, path, effective access, and whether the issue is broader.

## 8. Quick Check

Four formative questions mapped to objective 1.6.
