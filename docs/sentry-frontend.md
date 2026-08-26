# Nexus frontend Sentry operations

Sentry is limited to the React/Vite frontend. The FastAPI backend and Next.js Service Desk are not instrumented.

## Runtime configuration

Set `VITE_SENTRY_DSN` to the public browser DSN to enable monitoring. An unset DSN leaves the SDK disabled. Set `VITE_SENTRY_ENVIRONMENT=production` and `VITE_SENTRY_RELEASE` to the immutable git SHA for a release build. Sampling defaults to 0.10 for traces, 0.05 for normal replays, and 1.0 for error replays; the corresponding optional variables are documented in `frontend/.env.example`.

## Source maps

The Vite plugin only creates and uploads hidden source maps when all three build-only variables are present:

- `SENTRY_AUTH_TOKEN`: configure as a GitHub Actions repository or environment secret named exactly `SENTRY_AUTH_TOKEN`.
- `SENTRY_ORG`: configure as a GitHub Actions repository or environment variable.
- `SENTRY_PROJECT`: configure as a GitHub Actions repository or environment variable.

The CI frontend build supplies the current `${{ github.sha }}` as `VITE_SENTRY_RELEASE`. The auth token is read only by the build process, has no `VITE_` prefix, and is never available to browser code. Use a narrowly scoped Sentry organization token with project release/source-map permissions. Uploaded `.map` files are deleted from `dist` after upload, and ordinary builds without upload credentials generate no maps.

For a manual release build outside GitHub Actions, export the same three build-only variables plus `VITE_SENTRY_RELEASE=$(git rev-parse HEAD)` for the `npm run build` process. Do not put `SENTRY_AUTH_TOKEN` in any committed `.env` file or Docker build argument.

## One-time connection check

No automated test sends Sentry events. In a disposable local shell, set the real `VITE_SENTRY_DSN`, run `npm run dev`, open Nexus, and use the browser developer console to run:

```js
import("/src/monitoring/sentry.js")
  .then(({ captureBoundaryError }) => captureBoundaryError(
    new Error("Nexus Sentry integration test"),
    "manual connection test",
  ));
```

Then open the Sentry project, select Issues, remove restrictive environment filters if needed, and confirm an event named `Nexus Sentry integration test` appears with the local/development environment. Send only this one intentional event and remove the DSN from the disposable local environment afterward.
