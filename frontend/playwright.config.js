import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: process.env.NEXUS_E2E_BASE_URL || "http://127.0.0.1:5173",
    headless: true,
    trace: "retain-on-failure",
  },
});
