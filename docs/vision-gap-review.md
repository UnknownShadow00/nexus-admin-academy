# Vision Gap Review

This review reflects the current codebase after the Proxmox/Guacamole hardening pass on 2026-05-30.

## Strongly Implemented
- Student, mentor, and admin separation with JWT-compatible student auth and httpOnly browser session cookies.
- Core student workflows for learning path, quizzes, flashcards, tickets, labs, capstones, notes, command reference, and evidence upload.
- Admin workflows for students, quizzes, curriculum, labs, capstones, ticket review, bookmarklet import, AI cost visibility, and speed-flagged quiz attempts.
- Proxmox/Guacamole application layer for VM-backed labs: template VMID mapping, VM assignment tracking, lab start provisioning, iframe session launch, submit teardown, and idle cleanup endpoint.
- Backend regression coverage for auth, quizzes, tickets, labs, capstones, admin sessions, and VM assignment lifecycle behavior.

## Gaps Still Open
1. **Sidecar services are deployment work**
   - Guacamole, GLPI, Netdata, Uptime Kuma, Gitea, and n8n still need real Proxmox deployment/configuration outside this repository.

2. **Production VM smoke test**
   - The code path is mocked in tests, but still needs a real Proxmox template VMID, Guacamole credentials, and an end-to-end lab start/submit run.

3. **Scheduler wiring**
   - n8n or another scheduler should call `DELETE /api/admin/vms/cleanup?idle_hours=2` on a fixed cadence.

4. **Operational cleanup**
   - Inaccessible local pytest/temp cache directories still create noisy `git status --ignored` warnings on this workstation.

5. **Frontend bundle size**
   - `npm run build` passes, but Vite still warns that the main chunk is larger than 500 kB.

## Recommended Next High-Impact Steps
1. Deploy/configure the P4 sidecars on Proxmox and document exact URLs, credentials locations, and operator runbooks.
2. Run a real VM-backed lab smoke test and capture the result in `tasks/loop-log.md`.
3. Configure the idle VM cleanup scheduler.
4. Split large frontend routes with dynamic imports if startup performance becomes a practical issue.
