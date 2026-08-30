---
lesson_key: lesson.aplus.service_desk.change_management
title: Change Management Without Breaking Production
certification_version: comptia_aplus_220-1202
domain: '4.0'
module: module.aplus.core2.service_desk_workflow
importance: job_critical
learning_relationship: new
objectives:
- '4.2'
lesson_order: 5
quick_check:
  title: "Quick Check \u2014 Change Management Without Breaking Production"
  displayed_count: 5
  pass_percent: 60
  tags_any:
  - Q012
  - Q019
  - Q020
  - Q021
  - Q022
---

# Lesson 5 — Change Management Without Breaking Production

**Importance:** Job Critical  
**Relationship:** New  
**Objectives:** 220-1202 4.2

## 1. What is this?
Change management is a controlled way to modify systems without turning a planned improvement into an outage.

A change should answer: **why are we changing it, what is affected, what could go wrong, who approves/owns it, when will it happen, how will we test it, what will we back up, how will we undo it, and how will we prove it worked?**

## 2. Why does an IT worker care?
Even a simple software update can affect many users. In production, “I think it will be fine” is not a plan.

## 3. Watch / Read
**Required:** Professor Messer — *Change Management (220-1202)*  
https://www.professormesser.com/free-a-plus-training/220-1202/220-1202-video/change-management-220-1202/

## 4. What you actually need to remember
Core elements:
- purpose and scope
- affected systems / impact
- change type: standard, normal, or emergency
- date/time and maintenance-window or change-freeze rules
- risk analysis
- sandbox/test plan when possible
- **backup plan**
- **rollback/backout plan**
- responsible staff / approvals
- implementation steps
- peer review when required
- verification / end-user acceptance

**Backup plan:** what data, configuration, or state you will preserve before the change so it can be recovered if needed.

**Rollback/backout plan:** the concrete steps used to return the service to the previous known-good state if the change fails.

A backup can support rollback, but **“take a backup” is not by itself a rollback plan**.

## 5. At work
IT plans to update the approved PDF editor on 60 workstations. Test it with representative files before broad deployment. Define what will be backed up, who owns the deployment, when it runs, how the old version can be restored, and how users will confirm that critical exports still work.

## 6. Commands / Tools
Depends on the change. The skill here is the **plan and evidence**, not memorizing a deployment command.

## 7. Interview / Explain example
**Question:** “Why does a change need a rollback plan?”  
A strong answer: because testing cannot predict every production failure; the team needs a known, approved way to restore service quickly without improvising under pressure.

## 8. Quick Check
Use bank questions: **Q012, Q019, Q020, Q021, Q022**.
