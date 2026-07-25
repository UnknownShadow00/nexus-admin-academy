import { expect, test } from "@playwright/test";

// NB-5 controlled production Service Desk student walkthrough.
// Runs against the LIVE production backend using the single temporary
// student created for this validation session. Never touches real student
// accounts. Gated behind an explicit opt-in flag so it can never run by
// accident (e.g. in CI, which never targets production).
const enabled = process.env.NEXUS_E2E_NB5 === "true";
const studentUsername = process.env.NEXUS_E2E_NB5_STUDENT_USERNAME;
const studentPassword = process.env.NEXUS_E2E_NB5_STUDENT_PASSWORD;
const adminUsername = process.env.NEXUS_E2E_NB5_ADMIN_USERNAME;
const adminPassword = process.env.NEXUS_E2E_NB5_ADMIN_PASSWORD;
const apiBaseUrl = process.env.NEXUS_E2E_API_URL || process.env.NEXUS_E2E_BASE_URL || "http://127.0.0.1";
const screenshotDir = process.env.NEXUS_E2E_SCREENSHOT_DIR;
const allowCloudflareBeaconWarning = process.env.NEXUS_E2E_ALLOW_CLOUDFLARE_BEACON_WARNING === "true";

test.skip(!enabled, "NB-5 production walkthrough requires explicit opt-in and temporary credentials.");

function isCloudflareBeaconCspWarning(message) {
  return message.includes("static.cloudflareinsights.com/beacon.min.js")
    && message.includes("violates the following Content Security Policy directive")
    && message.includes("script-src 'self'");
}

function isCloudflareBeaconCspRequest(request, reason) {
  return request.url().startsWith("https://static.cloudflareinsights.com/beacon.min.js")
    && reason === "csp";
}

function monitorPage(page) {
  const consoleErrors = [];
  const failedRequests = [];
  const httpErrors = [];
  let active = true;
  page.on("console", (message) => {
    if (!active || message.type() !== "error") return;
    const text = message.text();
    if (allowCloudflareBeaconWarning && isCloudflareBeaconCspWarning(text)) return;
    consoleErrors.push(text);
  });
  page.on("pageerror", (error) => { if (active) consoleErrors.push(`pageerror: ${error.message}`); });
  page.on("requestfailed", (request) => {
    if (!active) return;
    const reason = request.failure()?.errorText || "unknown error";
    if (allowCloudflareBeaconWarning && isCloudflareBeaconCspRequest(request, reason)) return;
    if (!reason.includes("ERR_ABORTED")) failedRequests.push(`${request.method()} ${request.url()}: ${reason}`);
  });
  page.on("response", (response) => {
    if (!active) return;
    if (response.status() >= 400 && response.url().includes("/api/")) {
      httpErrors.push(`${response.status()} ${response.url()}`);
    }
  });
  return {
    consoleErrors, failedRequests, httpErrors,
    pause: () => { active = false; },
    resume: () => { active = true; },
  };
}

async function browserApi(page, url, options = {}) {
  return page.evaluate(async ({ requestUrl, requestOptions }) => {
    const response = await fetch(requestUrl, {
      credentials: "include",
      ...requestOptions,
      headers: { "Content-Type": "application/json", ...(requestOptions.headers || {}) },
    });
    let body = null;
    try { body = await response.json(); } catch { /* no body */ }
    return { status: response.status, body };
  }, { requestUrl: url, requestOptions: options });
}

async function studentLogin(page) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(studentUsername);
  await page.getByLabel("Password").fill(studentPassword);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
}

const scenarios = [
  ["Locked User Account", [
    ["Ticket", "open ticket"], ["Ticket", "inspect requester"], ["Identity & Access", "verify identity", "employee_id_last4"],
    ["Employee Directory", "search account", "tnguyen"], ["Identity & Access", "inspect account"], ["Identity & Access", "unlock account", "tnguyen"],
    ["Resolution Notes", "add resolution note", "NB-5 validation: verified identity and restored the correct account."], ["Ticket", "resolve ticket"],
  ]],
  ["Password Reset", [
    ["Ticket", "open ticket"], ["Ticket", "inspect requester"], ["Identity & Access", "verify identity", "employee_id_last4"],
    ["Employee Directory", "search account", "jpatel"], ["Identity & Access", "inspect account"], ["Identity & Access", "reset password", "jpatel"],
    ["Resolution Notes", "add resolution note", "NB-5 validation: verified identity and completed the simulated reset."], ["Ticket", "resolve ticket"],
  ]],
  ["MFA Reset", [
    ["Ticket", "open ticket"], ["Ticket", "inspect requester"], ["Identity & Access", "verify identity", "employee_id_last4"],
    ["Employee Directory", "search account", "mlee"], ["Identity & Access", "inspect mfa"], ["Identity & Access", "reset mfa", "mlee"],
    ["Resolution Notes", "add resolution note", "NB-5 validation: verified identity and completed the simulated MFA reset."], ["Ticket", "resolve ticket"],
  ]],
  ["BitLocker Recovery", [
    ["Ticket", "open ticket"], ["Ticket", "inspect requester"], ["Identity & Access", "verify identity", "employee_id_last4"],
    ["BitLocker Recovery", "verify device", "NEX-LT-204"], ["BitLocker Recovery", "lookup recovery key", "NEX-LT-204"],
    ["Resolution Notes", "add resolution note", "NB-5 validation: verified requester and device; did not record key material."], ["Ticket", "resolve ticket"],
  ]],
  ["New Employee Onboarding", [
    ["Ticket", "open ticket"], ["Ticket", "inspect requester"], ["Onboarding", "verify onboarding request", "SDL-1005"],
    ["Onboarding", "create account", "crivera"], ["Onboarding", "assign group", "customer-success"], ["Onboarding", "assign device", "NEX-LT-305"],
    ["Resolution Notes", "add resolution note", "NB-5 validation: validated approved request and completed onboarding."], ["Ticket", "resolve ticket"],
  ]],
];

const recoverableMistakes = {
  "Locked User Account": ["search account", "wrong.user"],
  "Password Reset": ["search account", "wrong.user"],
  "MFA Reset": ["search account", "wrong.user"],
  "BitLocker Recovery": ["verify device", "WRONG-DEVICE"],
  "New Employee Onboarding": ["verify onboarding request", "WRONG-REQUEST"],
};

async function shot(page, name) {
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/${name}.png`, fullPage: true });
}

async function complete(page, title, mode, { screenshotPrefix } = {}) {
  // "Continue" covers the case where a prior attempt in this loop actually
  // started server-side but the UI failed to navigate in time (see below) —
  // the row falls back to a resume button instead of Start/Retry.
  const startName = mode === "learning" ? /^(Start|Retry) learning$/ : /^(Start simulation|Continue)$/;
  const modeHeading = page.getByText(`${mode[0].toUpperCase()}${mode.slice(1)} Mode`, { exact: true });
  // Real production over the internet is occasionally slow enough that a
  // click right after navigation doesn't land before the row re-renders.
  // Retry the whole navigate-and-click cycle a few times rather than assume
  // a fixed delay is always enough.
  let landed = false;
  for (let attempt = 1; attempt <= 4 && !landed; attempt += 1) {
    await page.goto("/service-desk?tab=Work+Queue");
    await expect(page.getByRole("heading", { name: "Work Queue" })).toBeVisible();
    const row = page.locator("tr").filter({ hasText: title });
    const startButton = row.getByRole("button", { name: startName });
    await expect(startButton).toBeEnabled();
    await page.waitForTimeout(500);
    await startButton.click();
    try {
      await expect(modeHeading).toBeVisible({ timeout: 8_000 });
      landed = true;
    } catch {
      if (attempt === 4) throw new Error(`Could not enter ${mode} mode for "${title}" after ${attempt} attempts`);
    }
  }
  if (screenshotPrefix) await shot(page, `${screenshotPrefix}-ticket`);
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
    }
  }
  await expect(page.getByText("Deterministic result", { exact: true })).toBeVisible();
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
  const attemptId = new URL(page.url()).searchParams.get("attempt");
  return attemptId;
}

test("NB-5: temporary student completes all five scenarios (Learning + Simulation)", async ({ page }) => {
  test.setTimeout(600_000);
  const monitor = monitorPage(page);

  await page.setViewportSize({ width: 1440, height: 1000 });
  await studentLogin(page);
  await expect(page.getByRole("heading", { name: "NB5 Temp QA Walkthrough" })).toBeVisible();

  // Nav / keyboard access sanity before touching the feature.
  const practice = page.getByRole("button", { name: "Practice Library" });
  await practice.focus();
  await page.keyboard.press("Enter");
  await expect(practice).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("menuitem", { name: "Service Desk Lab" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(practice).toHaveAttribute("aria-expanded", "false");
  await expect(practice).toBeFocused();
  const focusStyle = await practice.evaluate((el) => getComputedStyle(el).boxShadow);
  expect(focusStyle).not.toBe("none");

  await page.getByRole("button", { name: "Practice Library" }).click();
  await page.getByRole("menuitem", { name: "Service Desk Lab" }).click();
  await expect(page.getByRole("heading", { name: "Service Desk Lab" })).toBeVisible();
  const desktopDims = await page.evaluate(() => ({ w: document.documentElement.clientWidth, s: document.documentElement.scrollWidth }));
  expect(desktopDims.s).toBeLessThanOrEqual(desktopDims.w + 1);
  await shot(page, "nb5-desktop-overview");

  for (const [tab, key] of [["Work Queue", "Enter"], ["Performance", "Space"], ["Knowledge Base", "Enter"]]) {
    const tabButton = page.getByRole("button", { name: tab, exact: true });
    await tabButton.focus();
    await page.keyboard.press(key);
    await expect(page.getByRole("navigation", { name: "Service Desk sections" })).toBeVisible();
  }
  await shot(page, "nb5-desktop-knowledge-base");
  await page.goBack();
  await page.goForward();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Service Desk Lab" })).toBeVisible();

  // --- Learning Mode: all five scenarios ---
  for (const [index, [title]] of scenarios.entries()) {
    const attemptId = await complete(page, title, "learning", {
      screenshotPrefix: index === 0 ? "nb5-desktop-learning-locked-account" : undefined,
    });
    if (index === 0) {
      const projection = await browserApi(page, `${apiBaseUrl}/api/service-desk/attempts/${attemptId}`);
      const projectionText = JSON.stringify(projection.body);
      for (const hidden of ["hidden_facts", "correct_account_id", "critical_failure_definitions", "expected_action_sequence"]) {
        expect(projectionText).not.toContain(hidden);
      }
      expect(await page.locator("body").innerText()).not.toContain("hidden_facts");
      // Refresh mid-review preserves state.
      await page.reload();
      await expect(page.getByText("Learning Mode", { exact: true })).toBeVisible();
    }
  }

  // --- Simulation Mode: all five scenarios (attempt #1 of the 3-attempt cap for each) ---
  for (const [index, [title]] of scenarios.entries()) {
    await complete(page, title, "simulation", {
      screenshotPrefix: index === 0 ? "nb5-desktop-simulation-locked-account" : undefined,
    });
  }

  // Two more scored simulation attempts for Locked User Account, driven directly
  // through the same attempt-action API the UI calls (attempts #2 and #3 of the
  // 3-attempt cap; attempt #1 was the main loop above). Exercises the identical
  // engine/scoring path the UI walkthrough above already proved end-to-end;
  // this just needs two more terminal attempts to reach the cap deterministically.
  async function apiCompleteLockedAccount(seedPrefix) {
    const start = await browserApi(page, `${apiBaseUrl}/api/service-desk/scenarios/1/attempts`, {
      method: "POST",
      body: JSON.stringify({ mode: "simulation" }),
    });
    expect(start.status).toBe(201);
    const attemptId = start.body.data.id;
    const steps = [
      ["open_ticket", {}],
      ["inspect_requester", {}],
      ["verify_identity", { verification_method: "employee_id_last4" }],
      ["search_account", { query: "tnguyen" }],
      ["inspect_account", {}],
      ["unlock_account", { account_id: "tnguyen" }],
      ["add_resolution_note", { note: `NB-5 validation: ${seedPrefix} attempt-limit coverage.` }],
      ["resolve_ticket", {}],
    ];
    let version = 0;
    for (const [action, payload] of steps) {
      const result = await browserApi(page, `${apiBaseUrl}/api/service-desk/attempts/${attemptId}/actions`, {
        method: "POST",
        body: JSON.stringify({ action, idempotency_key: `${seedPrefix}-${action}`, expected_state_version: version, payload }),
      });
      expect(result.status).toBe(200);
      version += 1;
    }
    return attemptId;
  }
  const attempt2Id = await apiCompleteLockedAccount("nb5-cap2");
  await apiCompleteLockedAccount("nb5-cap3");

  // 4th attempt should be blocked by the simulation attempt cap (default 3).
  monitor.pause(); // this call is EXPECTED to fail with 403 — don't flag it as a defect.
  const limitResponse = await browserApi(page, `${apiBaseUrl}/api/service-desk/scenarios/1/attempts`, {
    method: "POST",
    body: JSON.stringify({ mode: "simulation" }),
  });
  monitor.resume();
  expect(limitResponse.status).toBe(403);
  expect(limitResponse.body?.code).toBe("SIMULATION_ATTEMPT_LIMIT");

  // Latest/best results and Knowledge Base.
  await page.goto("/service-desk?tab=Performance");
  await expect(page.getByText("Completed scenarios", { exact: true })).toBeVisible();
  await expect(page.getByText(/Latest \d+% · Best \d+% · \d+ attempts/)).toHaveCount(5, { timeout: 10_000 });
  await shot(page, "nb5-desktop-performance");
  const performance = await browserApi(page, `${apiBaseUrl}/api/service-desk/performance`);
  expect(performance.status).toBe(200);

  await page.goto("/service-desk?tab=Knowledge+Base");
  // The Knowledge Base panel has no page heading of its own — it renders
  // straight into a search box and article cards — so assert on the search
  // input instead of a heading that doesn't exist.
  await expect(page.getByLabel("Search knowledge articles")).toBeVisible({ timeout: 15_000 });
  const kb = await browserApi(page, `${apiBaseUrl}/api/service-desk/knowledge`);
  expect(kb.status).toBe(200);
  expect(kb.body.data.length).toBeGreaterThan(0);

  // --- Mobile viewport ---
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/service-desk?tab=Work+Queue");
  await expect(page.getByRole("heading", { name: "Work Queue" })).toBeVisible();
  const mobileDims = await page.evaluate(() => ({ w: document.documentElement.clientWidth, s: document.documentElement.scrollWidth }));
  expect(mobileDims.s).toBeLessThanOrEqual(mobileDims.w + 1);
  await shot(page, "nb5-mobile-work-queue");
  await page.goto("/service-desk?tab=Performance");
  await shot(page, "nb5-mobile-performance");

  expect(monitor.consoleErrors).toEqual([]);
  expect(monitor.failedRequests).toEqual([]);
  expect(monitor.httpErrors).toEqual([]);

  // --- Logout ---
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("button", { name: "NB5 Temp QA Walkthrough" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => localStorage.getItem("nexus_explicit_logout"))).toBe("true");
  const afterLogout = await browserApi(page, `${apiBaseUrl}/api/service-desk/overview`);
  expect(afterLogout.status).toBe(401);

  process.env.NB5_ATTEMPT_2_ID = attempt2Id || "";
});

test("NB-5: administrator verification of the temporary student's beta activity", async ({ page }) => {
  test.setTimeout(180_000);
  const monitor = monitorPage(page);

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
  }

  // Scenario detail view — confirm no hidden fields leak.
  const lockedScenario = page.locator("li").filter({ has: page.getByText("Locked User Account", { exact: true }) }).first();
  await lockedScenario.getByRole("button", { name: "View details" }).click();
  await expect(page).toHaveURL(/scenario=locked-user-account/);
  await shot(page, "nb5-admin-scenario-details-desktop");
  const scenarioResponse = await browserApi(page, `${apiBaseUrl}/api/admin/service-desk/scenarios/1`);
  const serialized = JSON.stringify(scenarioResponse.body).toLowerCase();
  for (const hidden of ["hidden_facts", "root_cause", "critical_failure_definitions", "correct_account_id", "tnguyen"]) {
    expect(serialized).not.toContain(hidden);
  }
  await page.goBack();

  // Beta enrollment — confirm ONLY the temporary student (id 8) is enrolled.
  const enrollments = await browserApi(page, `${apiBaseUrl}/api/admin/service-desk/beta-enrollments`);
  expect(enrollments.status).toBe(200);
  const activeEnrollments = enrollments.body.data.filter((e) => e.enabled && !e.removed_at);
  expect(activeEnrollments.map((e) => e.student_id)).toEqual([8]);
  await expect(page.getByText(/Student 8 · Active/)).toBeVisible();

  // Attempts — confirm student 8 has attempts, view replay + grade for one simulation attempt.
  const attempts = await browserApi(page, `${apiBaseUrl}/api/admin/service-desk/attempts`);
  expect(attempts.status).toBe(200);
  const studentAttempts = attempts.body.data.filter((a) => a.student_id === 8);
  expect(studentAttempts.length).toBeGreaterThanOrEqual(8); // 5 learning + 3 scored simulation
  const simulationAttempt = studentAttempts.find((a) => a.mode === "simulation" && a.status === "completed");
  expect(simulationAttempt).toBeTruthy();

  const simulationRow = page.locator("tbody tr").filter({ hasText: String(simulationAttempt.id) }).first();
  if (await simulationRow.count() === 0) {
    // Table may be scenario-scoped; fall back to direct API verification if the row isn't on the current view.
    const replay = await browserApi(page, `${apiBaseUrl}/api/admin/service-desk/attempts/${simulationAttempt.id}/events`);
    expect(replay.status).toBe(200);
    const sequence = replay.body.data.events.map((e) => e.sequence_number);
    expect(sequence).toEqual([...sequence].sort((a, b) => a - b));
    expect(replay.body.data.grade.details.earned_score_keys.length).toBeGreaterThan(0);
  } else {
    await simulationRow.getByRole("button", { name: "View replay" }).click();
    await expect(page).toHaveURL(/panel=replay/);
    await expect(page.getByRole("heading", { name: /Attempt \d+ event replay/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Grade breakdown" })).toBeVisible();
    await shot(page, "nb5-admin-attempt-replay-desktop");
  }

  // Reset control — exercised only on the deliberately-created 2nd (prerequisite-gating) attempt,
  // never on the primary walkthrough attempts, per the documented cleanup/reset policy.
  const attempt2Id = process.env.NB5_ATTEMPT_2_ID;
  if (attempt2Id) {
    const resetRow = page.locator("tbody tr").filter({ hasText: attempt2Id }).first();
    if (await resetRow.count() > 0) {
      await resetRow.getByRole("button", { name: "Reset attempt" }).click();
      await expect(page.getByText("admin · admin_reset · accepted", { exact: true })).toBeVisible();
    } else {
      const resetApi = await browserApi(page, `${apiBaseUrl}/api/admin/service-desk/attempts/${attempt2Id}/reset`, { method: "POST" });
      expect(resetApi.status).toBe(200);
    }
  }

  // Mobile viewport.
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(`/admin/service-desk?scenario=locked-user-account`);
  await expect(page.getByRole("heading", { name: "Locked User Account" })).toBeVisible();
  const dims = await page.evaluate(() => ({ w: document.documentElement.clientWidth, s: document.documentElement.scrollWidth }));
  expect(dims.s).toBeLessThanOrEqual(dims.w + 1);
  await shot(page, "nb5-admin-scenario-details-mobile");

  expect(monitor.consoleErrors).toEqual([]);
  expect(monitor.failedRequests).toEqual([]);
  expect(monitor.httpErrors).toEqual([]);
});
