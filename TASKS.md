# Nexus Current Roadmap

Last reviewed: 2026-07-22.

This file contains only active work. Completed implementation history is in
Git. The current manual-VM cohort release is deployed and the backend test
suite, frontend build, database migration head, and production smoke checks
were green at the last release checkpoint.

## Operations

- [ ] Enable Cloudflare **Always Use HTTPS** for the public domain. This is a
  dashboard-only change; the application already emits HSTS on HTTPS.
- [ ] Run a real Proxmox/Guacamole start, student-isolation, refresh, expiry,
  and cleanup test before enabling automated VM delivery for students.
- [ ] Schedule `DELETE /api/admin/vms/cleanup?idle_hours=2` only after that
  infrastructure acceptance passes.
- [ ] Continue testing both the SQLite database backup and uploads restore;
  see `docs/DEPLOYMENT.md`.

## Content quality

- [ ] Review the optional imported quiz editorial queue, add explanations,
  and validate answer keys before publishing any item.
- [ ] Review the proposed scenario-question gaps as a separate, approved
  content phase; do not mix them into maintenance work.
- [ ] Build the routing CLI lesson pack from
  `references/lesson-drafts/learn-routing.md` when product work resumes.

## Product maintenance

- [ ] Decide whether text-based labs should award XP and enter mentor review
  using the same policy as tickets and networking labs.
- [ ] Enforce or remove the currently descriptive
  `must_contain_text` evidence rule.
- [ ] Add consistent locked-state messaging to future-week ticket and lab
  detail pages; mutation endpoints already enforce the gate.
- [ ] Add explicit rate-limit messaging for HTTP 429 responses.
- [ ] Add a frontend lint/test harness and a focused navigation/auth browser
  suite when maintenance scope permits.
- [ ] Complete a keyboard, screen-reader, and automated accessibility pass.

## Deferred product work

- Weekly mentor digest and stalled-student reporting.
- Additional Active Directory, PowerShell, subnetting, and escalation practice.
- Optional integrations such as GLPI, Gitea, n8n, and monitoring tools.
- The Service Desk Lab is intentionally not part of this cleanup and remains a
  separate future feature.
