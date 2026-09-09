# Core Wave 3 validation

All browser data lived in temporary SQLite databases, services bound only to loopback, V2 was explicitly false, and the three Wave 3 fixture learners were disposable. The temporary database, credentials, logs, processes, and dependency symlinks were removed after testing.

## Passing gates

- Backend focused: 58 passed.
- Frontend unit: 74 passed.
- Wave 3 browser: 3 passed.
- Wave 1 browser truth: 4 passed.
- Wave 2 beginner path: 4 passed.
- Service Desk integrity subset: 31 passed.
- Core Vite production build: passed.
- Ruff check, compileall, selected Ruff format and Prettier checks, and `git diff --check`: passed.
- Python audit: no known vulnerabilities.

## Diagnostic exceptions

The unscoped full backend run passed 1,181 tests and reported 9 failures unrelated to this branch’s lesson changes: absent production database assumptions (2), stale historical practical-migration aggregate expectations (6), and missing V2 admin-auth environment (1). The relevant test groups pass independently. The unchanged Core frontend dependency tree reports one low, one moderate, and one high advisory; no dependencies changed in Wave 3.

## Safety

No production URL, service, database, learner, content loader, migration, V2 feature flag, or Service Desk implementation was used or changed.
