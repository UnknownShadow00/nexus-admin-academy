import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

// This app is nested two levels below the pnpm workspace root
// (service-desk-app/apps/web). Next.js infers a "workspace root" by walking
// up from this directory looking for a lockfile, and — now that
// service-desk-app lives inside the larger nexus-admin-academy repo — it can
// walk past service-desk-app/pnpm-lock.yaml and find an unrelated lockfile
// higher up, which produces a "workspace root inferred incorrectly" warning
// and could misdirect file tracing for standalone output. Pinning it
// explicitly to service-desk-app/ (the real workspace root) is the fix
// Next.js's own docs recommend for this exact nested-app situation.
const workspaceRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

const nextConfig = {
  basePath: process.env.SERVICE_DESK_BASE_PATH || '',
  env: {
    NEXT_PUBLIC_BASE_PATH: process.env.SERVICE_DESK_BASE_PATH || '',
  },
  outputFileTracingRoot: workspaceRoot,
  serverExternalPackages: ['jsonwebtoken'],
  transpilePackages: [
    '@service-desk/ui',
    '@service-desk/shared',
    '@service-desk/simulation-engine',
  ],
};

export default nextConfig;
