import { expect, test } from "@playwright/test";

const enabled = process.env.NEXUS_E2E_SERVICE_DESK === "true";
const password = process.env.NEXUS_E2E_SERVICE_DESK_PASSWORD || "LocalBrowser!2026";
const screenshotDir = process.env.NEXUS_E2E_SCREENSHOT_DIR;
const adminUsername = process.env.NEXUS_E2E_ADMIN_USERNAME || "local-admin";
const adminPassword = process.env.NEXUS_E2E_ADMIN_PASSWORD || "LocalAdminBrowser!2026";
const apiBaseUrl = process.env.NEXUS_E2E_API_URL || "http://127.0.0.1:8012";

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

const recoverableMistakes = {
  "Locked User Account": ["search account", "wrong.user"],
  "Password Reset": ["search account", "wrong.user"],
  "MFA Reset": ["search account", "wrong.user"],
  "BitLocker Recovery": ["verify device", "WRONG-DEVICE"],
  "New Employee Onboarding": ["verify onboarding request", "WRONG-REQUEST"],
};

async function login(page, username) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
}

async function browserApi(page, url, options = {}) {
  return page.evaluate(async ({ requestUrl, requestOptions }) => {
    const response = await fetch(requestUrl, {
      credentials: "include",
      ...requestOptions,
      headers: {
        "Content-Type": "application/json",
        ...(requestOptions.headers || {}),
      },
    });
    return { status: response.status, body: await response.json() };
  }, { requestUrl: url, requestOptions: options });
}

async function complete(page, title, mode) {
  await page.goto("/service-desk?tab=Work+Queue");
  const row = page.locator("tr").filter({ hasText: title });
  const startName = mode === "learning" ? /^(Start|Retry) learning$/ : "Start simulation";
  await row.getByRole("button", { name: startName }).click();
  await expect(page.getByText(`${mode[0].toUpperCase()}${mode.slice(1)} Mode`, { exact: true })).toBeVisible();
  if (screenshotDir && title === "Locked User Account") {
    await page.screenshot({ path: `${screenshotDir}/${mode}-mode-ticket-desktop.png`, fullPage: true });
  }
  if (mode === "learning") {
    await page.getByRole("button", { name: "Learning Help" }).click();
    await expect(page.getByRole("button", { name: "request hint" })).toBeVisible();
  } else {
    await expect(page.getByRole("button", { name: "Learning Help" })).toHaveCount(0);
  }
  const [, steps] = scenarios.find(([scenarioTitle]) => scenarioTitle === title);
  for (const [tool, action, value] of steps) {
    await page.getByRole("button", { name: tool, exact: true }).click();
    if (screenshotDir && mode === "learning") {
      if (title === "Locked User Account" && tool === "Employee Directory" && action === "search account") {
        await page.screenshot({ path: `${screenshotDir}/employee-directory-desktop.png`, fullPage: true });
      }
      if (title === "Locked User Account" && tool === "Identity & Access" && action === "verify identity") {
        await page.screenshot({ path: `${screenshotDir}/identity-access-desktop.png`, fullPage: true });
      }
      if (title === "BitLocker Recovery" && tool === "BitLocker Recovery" && action === "verify device") {
        await page.screenshot({ path: `${screenshotDir}/bitlocker-recovery-desktop.png`, fullPage: true });
      }
    }
    const form = page.locator("form").filter({ hasText: action });
    if (value) {
      const mistake = recoverableMistakes[title];
      if (mode === "learning" && mistake?.[0] === action) {
        await form.locator("textarea").fill(mistake[1]);
        const wrongResponse = page.waitForResponse((response) => response.url().includes("/actions") && response.request().method() === "POST");
        await form.getByRole("button", { name: action, exact: true }).click();
        expect((await wrongResponse).status()).toBe(200);
        await expect(page.getByRole("status")).toBeVisible();
      }
      await form.locator("textarea").fill(value);
    }
    const actionResponsePromise = page.waitForResponse((response) => response.url().includes("/actions") && response.request().method() === "POST");
    await form.getByRole("button", { name: action, exact: true }).click();
    const actionResponse = await actionResponsePromise;
    if (action === "open ticket") {
      const duplicate = await browserApi(page, actionResponse.url(), {
        method: "POST",
        body: JSON.stringify(actionResponse.request().postDataJSON()),
      });
      expect(duplicate.status).toBe(200);
      expect(duplicate.body.data.idempotent).toBe(true);
      if (title === "Locked User Account" && mode === "learning") {
        await page.reload();
        await expect(page.getByText("Learning Mode", { exact: true })).toBeVisible();
      }
    }
  }
  await expect(page.getByText("Deterministic result", { exact: true })).toBeVisible();
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
}

test("Service Desk private beta renders safely on desktop and mobile", async ({ page }) => {
  test.setTimeout(180_000);
  const consoleErrors = [];
  const failures = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("requestfailed", (request) => { if (!request.failure()?.errorText?.includes("ERR_ABORTED")) failures.push(request.url()); });

  await page.setViewportSize({ width: 1440, height: 1000 });
  await login(page, "local-non-beta");
  await expect(page.getByRole("heading", { name: "Local Non Beta" })).toBeVisible();
  await expect(page.getByText("Service Desk Lab", { exact: true })).toHaveCount(0);
  const practice = page.getByRole("button", { name: "Practice Library" });
  await practice.focus();
  await page.keyboard.press("Enter");
  await expect(practice).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("menuitem", { name: "Support Tickets" })).toBeVisible();
  await expect(page.getByRole("menuitem", { name: "Service Desk Lab" })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(practice).toHaveAttribute("aria-expanded", "false");
  await expect(practice).toBeFocused();
  const focusStyle = await practice.evaluate((element) => getComputedStyle(element).boxShadow);
  expect(focusStyle).not.toBe("none");
  await page.goto("/training");
  await expect(page.getByRole("heading", { name: "My Training" })).toBeVisible();
  await page.goto("/labs");
  await expect(page.getByRole("heading", { name: "Lab Exercises" })).toBeVisible();
  await page.goto("/progress");
  await expect(page.getByRole("heading", { name: "Progress", exact: true })).toBeVisible();
  await page.goto("/tickets");
  await expect(page.locator("main")).toContainText(/Available Tickets|Complete methodology training first/);
  const access = await browserApi(page, `${apiBaseUrl}/api/service-desk/access`);
  expect(access.status).toBe(200);
  expect(access.body.data.available).toBe(false);
  for (const path of ["overview", "queue", "performance", "knowledge"]) {
    const denied = await browserApi(page, `${apiBaseUrl}/api/service-desk/${path}`);
    expect(denied.status).toBe(404);
    expect(denied.body.code).toBe("SERVICE_DESK_UNAVAILABLE");
  }
  await page.goto("/service-desk");
  await expect(page.getByText("Service Desk Lab is unavailable.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Local Non Beta" }).click();
  await expect(page).toHaveURL(/\/login$/);
  consoleErrors.length = 0;
  failures.length = 0;

  await login(page, "local-beta");
  await page.getByRole("button", { name: "Practice Library" }).click();
  await page.getByRole("menuitem", { name: "Service Desk Lab" }).click();
  await expect(page.getByRole("heading", { name: "Service Desk Lab" })).toBeVisible();
  const desktopDimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(desktopDimensions.scroll).toBeLessThanOrEqual(desktopDimensions.width + 1);
  if (screenshotDir) {
    await page.screenshot({ path: `${screenshotDir}/student-overview-desktop.png`, fullPage: true });
    await page.screenshot({ path: `${screenshotDir}/desktop-layout.png`, fullPage: true });
  }
  for (const [tab, key] of [["Work Queue", "Enter"], ["Performance", "Space"], ["Knowledge Base", "Enter"]]) {
    const tabButton = page.getByRole("button", { name: tab, exact: true });
    await tabButton.focus();
    await page.keyboard.press(key);
    await expect(page.getByRole("navigation", { name: "Service Desk sections" })).toBeVisible();
    if (screenshotDir && tab === "Work Queue") await page.screenshot({ path: `${screenshotDir}/work-queue-desktop.png`, fullPage: true });
    if (screenshotDir && tab === "Knowledge Base") await page.screenshot({ path: `${screenshotDir}/knowledge-base-desktop.png`, fullPage: true });
  }
  await page.goBack();
  await page.goForward();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Service Desk Lab" })).toBeVisible();

  for (const [index, [title]] of scenarios.entries()) {
    await complete(page, title, "learning");
    if (index === 0) {
      const attemptId = new URL(page.url()).searchParams.get("attempt");
      const projection = await browserApi(page, `${apiBaseUrl}/api/service-desk/attempts/${attemptId}`);
      const projectionText = JSON.stringify(projection.body);
      for (const hidden of ["hidden_facts", "correct_account_id", "critical_failure_definitions", "expected_action_sequence"]) {
        expect(projectionText).not.toContain(hidden);
      }
      expect(await page.locator("body").innerText()).not.toContain("hidden_facts");
    }
  }
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
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/mobile-layout.png`, fullPage: true });
  expect(consoleErrors).toEqual([]);
  expect(failures).toEqual([]);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("button", { name: "Local Beta" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => localStorage.getItem("nexus_explicit_logout"))).toBe("true");
  const logoutDenied = await browserApi(page, `${apiBaseUrl}/api/service-desk/overview`);
  expect(logoutDenied.status).toBe(401);
  const browserContext = page.context();
  await page.close();
  const loggedOutPage = await browserContext.newPage();
  await loggedOutPage.goto("/service-desk");
  await expect(loggedOutPage.getByRole("button", { name: "Login" })).toBeVisible();
  await expect(loggedOutPage.getByRole("heading", { name: "Work Queue" })).toHaveCount(0);
  await loggedOutPage.close();
});

test("Service Desk administrator controls and replay render safely", async ({ page }) => {
  test.setTimeout(120_000);
  const consoleErrors = [];
  const pageErrors = [];
  const failures = [];
  const httpErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => { if (!request.failure()?.errorText?.includes("ERR_ABORTED")) failures.push(request.url()); });
  page.on("response", (response) => {
    if (response.status() >= 400 && response.url().includes("/api/")) {
      httpErrors.push(`${response.status()} ${response.url()}`);
    }
  });

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/admin/service-desk");
  await expect(page).toHaveURL(/\/admin-login\?redirect=/);
  await page.getByLabel("Username").fill(adminUsername);
  await page.getByLabel("Password").fill(adminPassword);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/admin\/service-desk$/);
  await expect(page.getByRole("heading", { name: "Service Desk Lab" })).toBeVisible();
  await expect(page.getByText("Passing", { exact: true })).toBeVisible();
  for (const [title] of scenarios) {
    const scenario = page.locator("li").filter({ has: page.getByText(title, { exact: true }) }).first();
    await expect(scenario.getByText("Version 1 · published · Health passing", { exact: true })).toBeVisible();
    await expect(scenario.getByRole("button", { name: "View details" })).toBeVisible();
  }

  const lockedScenario = page.locator("li").filter({ has: page.getByText("Locked User Account", { exact: true }) }).first();
  const viewScenario = lockedScenario.getByRole("button", { name: "View details" });
  await viewScenario.focus();
  await viewScenario.press("Space");
  await expect(page).toHaveURL(/scenario=locked-user-account/);
  await expect(page.getByRole("heading", { name: "Locked User Account" })).toBeVisible();
  await expect(page.getByText("Stable ID")).toBeVisible();
  await expect(page.getByText("Learning Mode availability")).toBeVisible();
  await expect(page.getByText("Simulation Mode availability")).toBeVisible();
  await expect(page.getByText("Administrator-safe metadata")).toBeVisible();
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/admin-scenario-details-desktop.png`, fullPage: true });

  const scenarioResponse = await browserApi(page, `${apiBaseUrl}/api/admin/service-desk/scenarios/1`);
  expect(scenarioResponse.status).toBe(200);
  const serializedScenario = JSON.stringify(scenarioResponse.body).toLowerCase();
  for (const hiddenValue of ["hidden_facts", "root_cause", "critical_failure_definitions", "correct_account_id", "tnguyen"]) {
    expect(serializedScenario).not.toContain(hiddenValue);
  }
  await page.reload();
  await expect(page.getByRole("heading", { name: "Locked User Account" })).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(/\/admin\/service-desk$/);
  await expect(page.getByRole("heading", { name: "Scenarios and validation" })).toBeVisible();

  await page.getByLabel("Student ID").first().fill("1");
  await page.getByRole("button", { name: "Add beta student" }).click();
  const enrollment = page.locator("li").filter({ hasText: "Student 1 · Active" });
  await expect(enrollment).toBeVisible();
  await enrollment.getByRole("button", { name: "Remove enrollment" }).click();
  await expect(page.getByText("Student 1 · Removed", { exact: true })).toBeVisible();

  await page.getByLabel("Student ID").nth(1).fill("2");
  await page.getByLabel("Scenario ID").selectOption({ index: 1 });
  await page.getByRole("button", { name: "Assign learning mode" }).click();
  const assignmentPanel = page.getByRole("heading", { name: "Assign scenario" }).locator("..");
  const assignment = assignmentPanel.locator("li").filter({ hasText: "Student 2" });
  await expect(assignment).toBeVisible();
  await assignment.getByRole("button", { name: "Remove assignment" }).click();
  await expect(assignment).toHaveCount(0);

  await page.getByLabel("Knowledge article stable ID").fill("browser-release-review");
  await page.getByLabel("Knowledge article title").fill("Browser release review");
  await page.getByLabel("Knowledge article category").fill("Validation");
  await page.getByLabel("Knowledge article content").fill("Temporary administrator browser validation article.");
  await page.getByRole("button", { name: "Create article" }).click();
  await expect(page).toHaveURL(/article=browser-release-review/);
  await expect(page.getByRole("heading", { name: "Browser release review" })).toBeVisible();
  await expect(page.getByText("Temporary administrator browser validation article.", { exact: true })).toBeVisible();
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/admin-knowledge-article-desktop.png`, fullPage: true });
  await page.goBack();
  await expect(page).toHaveURL(/\/admin\/service-desk$/);

  const articleCard = page.locator("li").filter({ has: page.getByText("Browser release review", { exact: true }) });
  const viewArticle = articleCard.getByRole("button", { name: "View article" });
  await viewArticle.focus();
  await viewArticle.press("Enter");
  await expect(page.getByRole("heading", { name: "Browser release review" })).toBeVisible();
  await page.getByRole("button", { name: "Edit article" }).click();
  await page.getByLabel("Title").fill("Unsaved article title");
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByRole("heading", { name: "Browser release review" })).toBeVisible();
  await expect(page.getByText("Unsaved article title", { exact: true })).toHaveCount(0);

  await page.getByRole("button", { name: "Edit article" }).click();
  await page.getByLabel("Title").fill("Browser release review updated");
  await page.getByLabel("Category").fill("Operations");
  await page.getByLabel("Content").fill("Updated temporary administrator browser validation article.");
  await page.getByLabel("Article state").selectOption("published");
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/admin-knowledge-edit-desktop.png`, fullPage: true });
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("heading", { name: "Browser release review updated" })).toBeVisible();
  await expect(page.getByText("Operations", { exact: true })).toBeVisible();
  await expect(page.getByText("Status: published", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Browser release review updated" })).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(/\/admin\/service-desk$/);

  const simulationRow = page.locator("tbody tr").filter({ hasText: "simulation" }).first();
  await expect(simulationRow.getByRole("button", { name: "View replay" })).toBeVisible();
  await expect(simulationRow.getByRole("button", { name: "Grade details" })).toBeVisible();
  await expect(simulationRow.getByRole("button", { name: "Reset attempt" })).toBeVisible();
  await simulationRow.getByRole("button", { name: "View replay" }).click();
  await expect(page).toHaveURL(/panel=replay/);
  await expect(page.getByRole("heading", { name: /Attempt \d+ event replay/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Grade breakdown" })).toBeVisible();
  await expect(page.getByText("Technical completion")).toBeVisible();
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/admin-attempt-replay-desktop.png`, fullPage: true });
  const replay = await browserApi(page, `${apiBaseUrl}/api/admin/service-desk/attempts/${await simulationRow.locator("td").first().textContent()}/events`);
  expect(replay.status).toBe(200);
  const replayBody = replay.body;
  const sequence = replayBody.data.events.map((event) => event.sequence_number);
  expect(sequence).toEqual([...sequence].sort((a, b) => a - b));
  expect(replayBody.data.grade.details.earned_score_keys.length).toBeGreaterThan(0);

  await simulationRow.getByRole("button", { name: "Reset attempt" }).click();
  await expect(page.getByText("admin · admin_reset · accepted", { exact: true })).toBeVisible();

  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByRole("button", { name: "Close attempt details" }).click();
  const mobileScenario = page.locator("li").filter({ has: page.getByText("Locked User Account", { exact: true }) }).first();
  await mobileScenario.getByRole("button", { name: "View details" }).click();
  await expect(page.getByRole("heading", { name: "Locked User Account" })).toBeVisible();
  const dimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width + 1);
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/admin-scenario-details-mobile.png`, fullPage: true });
  expect(consoleErrors).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(failures).toEqual([]);
  expect(httpErrors).toEqual([]);
});
