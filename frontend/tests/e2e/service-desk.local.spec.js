import { expect, test } from "@playwright/test";

const enabled = process.env.NEXUS_E2E_SERVICE_DESK === "true";
const password = process.env.NEXUS_E2E_SERVICE_DESK_PASSWORD || "LocalBrowser!2026";
const screenshotDir = process.env.NEXUS_E2E_SCREENSHOT_DIR;

test.skip(!enabled, "Service Desk local browser validation requires disposable local accounts.");

const scenarios = [
  ["Locked User Account", [
    ["Ticket", "open ticket"], ["Ticket", "inspect requester"], ["Identity & Access", "verify identity", "employee_id_last4"],
    ["Employee Directory", "search account", "tnguyen"], ["Identity & Access", "inspect account"], ["Identity & Access", "unlock account", "tnguyen"],
    ["Resolution Notes", "add resolution note", "Verified identity and restored the correct account."], ["Ticket", "resolve ticket"],
  ]],
  ["Password Reset", [
    ["Ticket", "open ticket"], ["Ticket", "inspect requester"], ["Identity & Access", "verify identity", "employee_id_last4"],
    ["Employee Directory", "search account", "jpatel"], ["Identity & Access", "inspect account"], ["Identity & Access", "reset password", "jpatel"],
    ["Resolution Notes", "add resolution note", "Verified identity and completed the simulated reset."], ["Ticket", "resolve ticket"],
  ]],
  ["MFA Reset", [
    ["Ticket", "open ticket"], ["Ticket", "inspect requester"], ["Identity & Access", "verify identity", "employee_id_last4"],
    ["Employee Directory", "search account", "mlee"], ["Identity & Access", "inspect mfa"], ["Identity & Access", "reset mfa", "mlee"],
    ["Resolution Notes", "add resolution note", "Verified identity and completed the simulated MFA reset."], ["Ticket", "resolve ticket"],
  ]],
  ["BitLocker Recovery", [
    ["Ticket", "open ticket"], ["Ticket", "inspect requester"], ["Identity & Access", "verify identity", "employee_id_last4"],
    ["BitLocker Recovery", "verify device", "NEX-LT-204"], ["BitLocker Recovery", "lookup recovery key", "NEX-LT-204"],
    ["Resolution Notes", "add resolution note", "Verified requester and device; did not record key material."], ["Ticket", "resolve ticket"],
  ]],
  ["New Employee Onboarding", [
    ["Ticket", "open ticket"], ["Ticket", "inspect requester"], ["Onboarding", "verify onboarding request", "SDL-1005"],
    ["Onboarding", "create account", "crivera"], ["Onboarding", "assign group", "customer-success"], ["Onboarding", "assign device", "NEX-LT-305"],
    ["Resolution Notes", "add resolution note", "Validated approved request and completed onboarding."], ["Ticket", "resolve ticket"],
  ]],
];

async function login(page, username) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
}

async function complete(page, title, mode) {
  await page.goto("/service-desk?tab=Work+Queue");
  const row = page.locator("tr").filter({ hasText: title });
  await row.getByRole("button", { name: `Start ${mode}` }).click();
  await expect(page.getByText(`${mode[0].toUpperCase()}${mode.slice(1)} Mode`, { exact: true })).toBeVisible();
  if (mode === "learning") {
    await page.getByRole("button", { name: "Learning Help" }).click();
    await expect(page.getByRole("button", { name: "request hint" })).toBeVisible();
  } else {
    await expect(page.getByRole("button", { name: "Learning Help" })).toHaveCount(0);
  }
  const [, steps] = scenarios.find(([scenarioTitle]) => scenarioTitle === title);
  for (const [tool, action, value] of steps) {
    await page.getByRole("button", { name: tool, exact: true }).click();
    const form = page.locator("form").filter({ hasText: action });
    if (value) await form.locator("textarea").fill(value);
    await Promise.all([
      page.waitForResponse((response) => response.url().includes("/actions") && response.request().method() === "POST"),
      form.getByRole("button", { name: action, exact: true }).click(),
    ]);
  }
  await expect(page.getByText("Deterministic result", { exact: true })).toBeVisible();
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
}

test("Service Desk private beta renders safely on desktop and mobile", async ({ page }) => {
  const consoleErrors = [];
  const failures = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("requestfailed", (request) => { if (!request.failure()?.errorText?.includes("ERR_ABORTED")) failures.push(request.url()); });

  await page.setViewportSize({ width: 1440, height: 1000 });
  await login(page, "local-non-beta");
  await expect(page.getByText("Service Desk Lab", { exact: true })).toHaveCount(0);
  await page.goto("/service-desk");
  await expect(page.getByText("Service Desk Lab is unavailable.", { exact: true })).toBeVisible();

  await login(page, "local-beta");
  await page.getByRole("button", { name: "Practice Library" }).click();
  await page.getByRole("menuitem", { name: "Service Desk Lab" }).click();
  await expect(page.getByRole("heading", { name: "Service Desk Lab" })).toBeVisible();
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/student-overview-desktop.png`, fullPage: true });
  for (const tab of ["Work Queue", "Performance", "Knowledge Base"]) {
    await page.getByRole("button", { name: tab, exact: true }).click();
    await expect(page.getByRole("navigation", { name: "Service Desk sections" })).toBeVisible();
  }
  await page.goBack();
  await page.goForward();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Service Desk Lab" })).toBeVisible();

  for (const [title] of scenarios) await complete(page, title, "learning");
  for (const [title] of scenarios) await complete(page, title, "simulation");
  await page.goto("/service-desk?tab=Performance");
  await expect(page.getByText("Completed scenarios", { exact: true })).toBeVisible();
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/performance-desktop.png`, fullPage: true });

  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/service-desk?tab=Work+Queue");
  await expect(page.getByRole("heading", { name: "Work Queue" })).toBeVisible();
  const dimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width + 1);
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/work-queue-mobile.png`, fullPage: true });
  expect(consoleErrors).toEqual([]);
  expect(failures).toEqual([]);
});
