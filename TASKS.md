# Nexus Current Roadmap

Last reviewed: 2026-07-24.

This file contains only active work. Completed implementation history is in
Git. The current manual-VM cohort release is deployed and the backend test
suite, frontend build, database migration head, and production smoke checks
were green at the last release checkpoint. `.github/workflows/ci.yml` now
runs the backend suite, a fresh-database migration/seed proof, frontend
validation, and real-browser Playwright coverage automatically on every PR
and push to main (see `docs/DEPLOYMENT.md`).

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
- [ ] Add a frontend lint/typecheck script (the navigation/auth browser suite
  now runs automatically in CI; frontend lint/typecheck is the remaining gap).
- [ ] Complete a keyboard, screen-reader, and automated accessibility pass.

## V2 Service Desk workspace redesign

Done on `feature/v2-service-desk-redesign` (not merged, not deployed, no
migration): unified student ticket workspace with embedded tools; authoritative
`workspace_view` driving the workflow rail, confirmed-evidence panel, one note
surface and one hint surface (no answer-key leakage before completion);
first-class escalation grading with normalized process scoring; post-completion
ticket debrief; semantic light/dark token system, system typography, and a
four-intent button hierarchy. See `service-desk-app/docs/WORKSPACE.md` and
`docs/PROGRESSION_CONTRACT.md` §E2.

Deferred realism follow-ups (full list in `service-desk-app/docs/WORKSPACE.md`
§9): `inc2501`-`inc2510` button-driven scenario rebuild; generalized
note-quality grading; deeper `inc2508` containment / session-revocation
fidelity; Directory <-> workstation state coupling; the remaining component and
admin theme-token conversion; scenario noise / wrong-requester assumptions;
richer escalation scenarios.

## Deferred product work

- Weekly mentor digest and stalled-student reporting.
- Additional Active Directory, PowerShell, subnetting, and escalation practice.
- Optional integrations such as GLPI, Gitea, n8n, and monitoring tools.
- The Service Desk Lab is intentionally not part of this cleanup and remains a
  separate future feature.
