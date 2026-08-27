import { expect, test } from "@playwright/test";

const SENTRY_INGEST_ORIGIN = "https://o4511978744840192.ingest.us.sentry.io";
const MOCK_ERROR = "Nexus CSP mock transport test";

test("production CSP allows Sentry and Replay without broadening Nexus navigation", async ({ page }) => {
  test.skip(process.env.NEXUS_E2E_CSP !== "true", "requires the disposable nginx CSP stack");
  const username = process.env.NEXUS_E2E_STUDENT_USERNAME;
  const password = process.env.NEXUS_E2E_STUDENT_PASSWORD;
  expect(username).toBeTruthy();
  expect(password).toBeTruthy();

  const cspViolations = [];
  const failedRequests = [];
  const sentryEnvelopes = [];
  const expectedPageErrors = [];

  page.on("console", (message) => {
    const text = message.text();
    if (text.includes("Content Security Policy")) cspViolations.push(text);
  });
  page.on("requestfailed", (request) => {
    failedRequests.push(`${request.failure()?.errorText || "unknown"} ${request.url()}`);
  });
  page.on("pageerror", (error) => {
    if (error.message.includes(MOCK_ERROR)) expectedPageErrors.push(error.message);
  });

  await page.addInitScript(() => {
    const NativeWorker = window.Worker;
    window.__nexusWorkerStarts = [];
    window.Worker = class NexusObservedWorker extends NativeWorker {
      constructor(url, options) {
        window.__nexusWorkerStarts.push(String(url));
        super(url, options);
      }
    };
  });

  await page.route(`${SENTRY_INGEST_ORIGIN}/**`, async (route) => {
    sentryEnvelopes.push({ method: route.request().method(), url: route.request().url() });
    await route.fulfill({
      status: 200,
      headers: {
        "access-control-allow-origin": process.env.NEXUS_E2E_BASE_URL,
        "content-type": "application/json",
      },
      body: "{}",
    });
  });

  const loginResponse = await page.goto("/login");
  const csp = loginResponse.headers()["content-security-policy"];
  expect(csp).toContain(`connect-src 'self' ${SENTRY_INGEST_ORIGIN}`);
  expect(csp).toContain("worker-src 'self' blob:");
  expect(csp).not.toContain("child-src");
  expect(csp).not.toContain("*.sentry.io");
  expect(csp).not.toContain("*.ingest.sentry.io");
  expect(csp).not.toMatch(/(?:^|;\s*)script-src[^;]*blob:/);
  expect(csp).not.toContain("'unsafe-eval'");

  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("button", { name: "Report Issue" })).toBeVisible();

  await page.getByRole("button", { name: "Report Issue" }).click();
  await expect(page.getByRole("dialog").getByRole("heading", { name: "Report an issue" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "What went wrong? (required)" })).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();

  await page.getByRole("link", { name: "Learning Path", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Learning Path", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Labs", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Labs", exact: true })).toBeVisible();

  await page.evaluate((message) => {
    setTimeout(() => { throw new Error(message); }, 0);
  }, MOCK_ERROR);

  await expect.poll(() => sentryEnvelopes.length, { timeout: 15_000 }).toBeGreaterThan(0);
  await expect.poll(
    async () => (await page.evaluate(() => window.__nexusWorkerStarts)).length,
    { timeout: 15_000 },
  ).toBeGreaterThan(0);
  const workerUrls = await page.evaluate(() => window.__nexusWorkerStarts);
  expect(workerUrls.every((url) => url.startsWith("blob:"))).toBe(true);

  await expect(page.getByRole("link", { name: "Tickets", exact: true })).toHaveAttribute("href", "/service-desk");

  expect(sentryEnvelopes.every(({ method, url }) => method === "POST" && url.startsWith(SENTRY_INGEST_ORIGIN))).toBe(true);
  expect(expectedPageErrors).toHaveLength(1);
  expect(cspViolations).toEqual([]);
  expect(failedRequests).toEqual([]);
});

test("disposable stack preserves authenticated Service Desk navigation", async ({ page }) => {
  test.skip(
    process.env.NEXUS_E2E_SERVICE_DESK_SMOKE !== "true",
    "requires the disposable backend and Service Desk stack",
  );

  await page.goto("/login");
  await page.getByLabel("Username").fill(process.env.NEXUS_E2E_STUDENT_USERNAME);
  await page.getByLabel("Password").fill(process.env.NEXUS_E2E_STUDENT_PASSWORD);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);

  await page.getByRole("link", { name: "Tickets", exact: true }).click();
  await expect(page).toHaveURL(/\/service-desk$/);
  await expect(page.getByRole("heading", { name: "My Service Desk" })).toBeVisible({ timeout: 20_000 });
});
