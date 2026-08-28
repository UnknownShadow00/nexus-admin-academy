# Service Desk launch-readiness evidence

## Staging database backup

Created before migration testing with:

```sh
docker exec nexus-staging-postgres-1 sh -c 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > /tmp/nexus-staging-audit-backup-fUuqBz/nexus-staging-pre-migration.dump
```

Backup path: `/tmp/nexus-staging-audit-backup-fUuqBz/nexus-staging-pre-migration.dump`.
Integrity was verified with `docker run --rm -v /tmp/nexus-staging-audit-backup-fUuqBz:/backup:ro postgres:16-alpine pg_restore --list /backup/nexus-staging-pre-migration.dump`.

At backup time: `students=9`, `service_desk_attempts=7`, `service_desk_attempt_events=15`, and `service_desk_attempt_grades=6`. Migration head was `0036_service_desk_mentor_feedback`.

Restore to an isolated database (never the live database) is:

```sh
pg_restore --clean --if-exists --no-owner --dbname="$ISOLATED_DATABASE_URL" /tmp/nexus-staging-audit-backup-fUuqBz/nexus-staging-pre-migration.dump
```

Verify by comparing the four row counts above and `alembic current`. SQLAlchemy migrations may not have a safe downgrade for every historical schema/data transform; database restore is the rollback path. The supplied backup folder was not found at its literal, correctly quoted path, so the space in `Nexus dupe` was not the cause.

## React Router audit (2026-08-02)

Installed `react-router-dom` and transitive `react-router` are both `6.30.4`.

`npm audit` reports GHSA-jjmj-jmhj-qwj2 (open redirect/XSS), GHSA-wrjc-x8rr-h8h6 (backslash open redirect), and GHSA-337j-9hxr-rhxg (SSR `deserializeErrors` constructor injection). The application is a client-only `BrowserRouter`; it does not use React Router SSR hydration, so the third advisory is not reachable. Login redirect handling should still reject external/backslash paths before `navigate`, so the redirect advisories remain a defense-in-depth risk. The audit's offered fixed release is `react-router-dom@7.18.2`, a major upgrade; defer it until a dedicated Router v7 migration passes every routing/browser flow.
