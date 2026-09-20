# Nexus V2 final pre-pilot integration evidence

This development branch is a candidate for a production-copy rehearsal. It is
not authorization to deploy, migrate production, enable V2, or enroll a real
student.

## Development-side guarantees

- Service Desk learning, simulation/assessment, and simulation/practice modes
  use assignment-owned retry ceilings. A mentor retry grant is idempotent.
- V2 Service Desk launches carry a trusted module/assessment marker on the
  attempt. Legacy attempts cannot satisfy V2 curriculum, V2 attempts cannot
  advance the legacy Service Desk ladder, and revoked learners cannot read or
  mutate marked attempts.
- A Service Desk retry clears every simulator overlay attributable to that
  ticket while preserving state owned by other tickets. Coaching remains
  limited while attempts remain and becomes full only when the attempt ceiling
  is exhausted.
- Assessment and Explain submissions persist their deterministic result or
  pending-grade job in the same transaction as the submitted response.
  Recoverable leases and mentor review cover worker interruption/provider
  failure.
- INC2501–INC2510 are reactivated from the curated source, have exactly one
  current published evidence-based version, and new attempts pin that version.
- Backend and Service Desk web writes require semantic contract `2.0`. The web
  client probes the contract and sends it with every authoritative mutation;
  the backend rejects a missing or incompatible contract.
- V2 practical launch context is an exact active module/assessment/lab
  relationship. Trusted run provenance protects later VM, evidence, verify,
  and submit calls after enrollment changes.
- Mentor progress reports expose pending assessment/Explain grading, available
  quiz retries, practical failure, Service Desk retry availability, and
  exhausted Service Desk attempts with recovery links where one exists.

## Authenticated full-module rehearsal coverage

`backend/tests/test_v2_full_module_rehearsal.py` runs one disposable authenticated
student through lesson and required resource completion, a failed/retried Quick
Check, a durable Module Quiz refresh, practical completion, a failed/retried
Service Desk attempt with a hint, pending Explain grading and mentor override,
Continue/module completion, and a fresh authenticated Progress request.

`frontend/tests/e2e/v2-student-experience.spec.js` covers the browser shell,
login persistence, Today/My Course navigation, module activity presentation,
Quick Check failure/retry, Module Quiz refresh behavior, and direct rendered
launches for the practical, Explain, and current Service Desk scenario, plus
logout/login, Progress, and a mobile viewport.
The deterministic Service Desk evidence action sequence and mentor override are
API-driven in the disposable full-module test rather than browser-clicked; the
separate Service Desk package tests cover workspace action routing, retries,
debrief tiers, and state restoration.

## Candidate preflight

The final rehearsal must capture the V1 baseline before loading V2 and compare
it afterward. Candidate mode deliberately fails without that artifact:

```bash
backend/.venv/bin/python scripts/v2_pilot_preflight.py \
  --database-url sqlite:////absolute/path/to/preload-copy.db \
  --baseline /absolute/path/to/v1-baseline.json

backend/.venv/bin/python scripts/v2_pilot_preflight.py \
  --production-candidate \
  --database-url sqlite:////absolute/path/to/loaded-copy.db \
  --compare-baseline /absolute/path/to/v1-baseline.json
```

Candidate mode also fails when the installed grading timer/unit, unit contract,
or a recorded successful worker execution cannot be proven. The check is
read-only.

`scripts/pilot_status.sh` warns on wildcard backend port 8000 and known direct
Service Desk/staging ports 3000, 13000, 18000, 18080, and 18081. Production is
expected to expose public application traffic through nginx only.

## Remaining operational work

Before a real learner is admitted: free production disk to the approved target,
correct the live backend unit environment assignment, install and exercise the
grading worker timer, rehearse 0064→0068 plus two V2 loads on a production copy,
compare V1 visibility, rehearse backup restore, verify production listeners,
run the candidate preflight and full smoke checklist, then enable/enroll only
the authorized pilot account.
