import { defineConfig } from '@playwright/test';

// Reuse existing browser tests with synthetic accounts, never real credentials.
process.env.NEXUS_E2E_BASE_URL = 'http://127.0.0.1:5819';
process.env.NEXUS_E2E_API_URL = 'http://127.0.0.1:5820';
process.env.NEXUS_E2E_SERVICE_DESK_URL = 'http://127.0.0.1:5820';
process.env.NEXUS_E2E_STUDENT_A_USERNAME = process.env.NEXUS_E2E_STUDENT_USERNAME = 'phase1-v2';
process.env.NEXUS_E2E_NONPILOT_USERNAME = 'phase1-legacy';
process.env.NEXUS_E2E_STUDENT_A_PASSWORD = process.env.NEXUS_E2E_STUDENT_PASSWORD = process.env.NEXUS_E2E_NONPILOT_PASSWORD = 'fixture-only-password';

export default defineConfig({
  testDir: './tests',
  testMatch: ['phase1/academy.spec.js', 'e2e/global-nav-reflow.spec.js', 'e2e/v2-copy-shell.spec.js'],
  // Admin mutation tests require an isolated backend and are outside this fixture.
  grepInvert: /admin header/,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: '../docs/visual-qa/academy-phase1/browser-results.json' }]],
  use: { baseURL: 'http://127.0.0.1:5819', headless: true, trace: 'retain-on-failure', viewport: { width: 1440, height: 900 } },
  webServer: [
    ...(process.env.NEXUS_PHASE1_BASELINE_DIR ? [{
      command: 'npm run dev -- --host 127.0.0.1 --port 5818 --strictPort',
      cwd: process.env.NEXUS_PHASE1_BASELINE_DIR + '/frontend', url: 'http://127.0.0.1:5818', reuseExistingServer: false,
      env: { VITE_API_URL: 'http://127.0.0.1:5820', VITE_V2_CURRICULUM_ENABLED: 'true', VITE_SENTRY_DSN: '', SENTRY_AUTH_TOKEN: '', SENTRY_ORG: '', SENTRY_PROJECT: '', E2E_API_PROXY_URL: '', E2E_SERVICE_DESK_URL: '' },
    }] : []),
    { command: 'node tests/phase1/api-server.mjs', url: 'http://127.0.0.1:5820/health', reuseExistingServer: false },
    { command: 'npm run dev -- --host 127.0.0.1 --port 5819 --strictPort', url: 'http://127.0.0.1:5819', reuseExistingServer: false,
      env: { VITE_API_URL: 'http://127.0.0.1:5820', VITE_V2_CURRICULUM_ENABLED: 'true', VITE_SENTRY_DSN: '', SENTRY_AUTH_TOKEN: '', SENTRY_ORG: '', SENTRY_PROJECT: '', E2E_API_PROXY_URL: '', E2E_SERVICE_DESK_URL: '' } },
  ],
});
