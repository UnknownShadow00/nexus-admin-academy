# V2 pilot-readiness shelf integration

Integration source: `9aea8669826b181fcedc3207d74032b02a340f40` on top of the
completed Service Desk realism branch. The shelf was inspected but never
applied wholesale.

| Shelved file                                       | Decision                                  | Integration result                                                                                                                                                                                                |
| -------------------------------------------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/app/services/v2_curriculum_service.py`    | Manual integration                        | Kept the Service Desk published-version availability check and adapted it to current active-scenario behavior; added the same openability rule for practicals. Existing quiz visibility remains authoritative.    |
| `backend/tests/test_v2_assessment_availability.py` | Manual integration                        | Kept and tightened published Service Desk coverage; added unpublished-practical coverage.                                                                                                                         |
| `backend/tests/test_operator_scripts.py`           | Manual integration                        | Recovered the operator decision tests, then added read-only SQLite, native systemd validation, status parsing, cutover dry-run, and current ten-scenario realism coverage.                                        |
| `docs/DEPLOYMENT.md`                               | Manual integration                        | Recovered the operations runbook and updated stale realism, lab-gate, worker, Docker-degradation, and theme statements.                                                                                           |
| `scripts/check_grading_worker_install.py`          | Integrated and extended                   | Preserved path, entry-point, environment, cadence, and live-unit checks; added `systemd-analyze verify` when available.                                                                                           |
| `scripts/make_cutover_snapshot.sh`                 | Integrated                                | Preserved dry-run default, explicit confirmation, SQLite online backup, sanity floor, and the retention-safe `v2-cutover-*` name.                                                                                 |
| `scripts/pilot_status.sh`                          | Integrated and corrected                  | Preserved read-only health/queue/activity/backup reporting, added Docker degradation, and made configured pilot counts use the same positive, unique-ID semantics as backend access.                              |
| `scripts/predeploy_check.sh`                       | Integrated                                | Preserved the 2 GiB hard minimum and added 2–4 GiB warning, 4 GiB acceptable, and 8 GiB rebuild/cutover guidance.                                                                                                 |
| `scripts/v2_pilot_preflight.py`                    | Manual integration                        | Preserved the report structure, link opt-in, baseline comparison, integrity checks, and JSON mode; enforced SQLite read-only connections and replaced stale wizard debt with a 10/10 evidence-based realism gate. |
| `service-desk-app/apps/web/app/layout.tsx`         | Unrelated theme change, narrowly accepted | Kept the current saved preference contract and added only the safe missing OS-preference fallback. No account preference or theme redesign was introduced.                                                        |

The core pilot allowlist/status endpoint, atomic foundation transaction,
required-resource validation, V1 visibility isolation, and validated V2 lab
context were already committed in `da2de78`, `027593e`, and `2ed935f`. They
were reviewed and retained rather than reimplemented from the shelf.

The shelf remains available as a recovery reference until this integration
branch is reviewed. Once these commits are accepted, every legitimate shelved
line is either represented above or intentionally replaced by the safer
current-compatible implementation, so the shelf will no longer be required.

## Verification snapshot

- Backend: 1,070 full-suite tests passed; 417 focused V2, grading, visibility,
  loader, and lab-gate tests passed.
- Operator tools: 35 tests passed. A disposable database preflight completed
  with 44 PASS, 3 expected editorial WARN, 0 FAIL, and 2 SKIP; V1 baseline
  comparison completed with 46 PASS, 3 WARN, 0 FAIL, and 1 SKIP.
- Frontend: 52 unit tests and the production build passed. This package does
  not define standalone lint or typecheck scripts; its Vite build is the
  available compile gate.
- Service Desk: shared 37, simulation engine 266, web 152, and UI 36 tests
  passed. Local browser 25/25, dedicated realism browser 11/11, and disposable
  authenticated integration browser 14/14 passed.
- Static checks: Ruff, compileall, Service Desk lint/typecheck/build, shell and
  JavaScript syntax, Alembic single-head, and diff checks passed.
- Dependency checks: Service Desk audit is clean. The standalone frontend has
  existing Browserslist (high) and postcss-selector-parser (low) advisories;
  `pip-audit` reports the existing pip 26.1.2 advisory. No dependency was
  changed during this integration.

Remaining operational findings are intentionally not auto-fixed: host free
space is about 1.7 GiB (below the 2 GiB predeploy floor), the grading timer is
not installed, and the installed backend unit has an invalid environment
assignment warning. The IP Configuration assessment remains correctly blocked
by its editorial gate. A final authenticated smoke against the eventual pilot
deployment is still required at cutover.
