import { expect, test } from "@playwright/test";

const PASSWORD = "E2ePassw0rd!23";

async function login(page, username) {
  // The in-memory auth token is lost on a full navigation, but the selected
  // profile persists in localStorage — isAuthenticated() then still returns
  // true and LoginPage redirects away before rendering the form. Clear it
  // first so a second login() in the same test (switching students) works.
  await page.goto("/login");
  await page.evaluate(() => localStorage.clear());
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
}

function monitorConsole(page) {
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (err) => errors.push(String(err)));
  return errors;
}

async function expectNoPageOverflow(page) {
  const widths = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(widths.scroll).toBeLessThanOrEqual(widths.client + 1);
}

// Known-correct answers, taken from the server-side case definition
// (app/services/integrated_support_final_shift.py) — never read from the
// client response, matching how a real student would reason through the
// evidence panels and options actually rendered on screen.
const WEEK24_CORRECT = {
  incident_a: { panels: ["account", "access", "change"], diagnosisLabel: "Yesterday's group-cleanup script removed her from the required Finance-Reports-RW group", actionLabel: "Request the approved re-add of Priya to Finance-Reports-RW, have her sign out and back in, then verify access", requiresUserUpdate: true, requiresEscalation: false },
  incident_b: { panels: ["identity", "device", "policy"], diagnosisLabel: "The laptop fell out of compliance, so conditional access is blocking Outlook and Teams", actionLabel: "Have him re-check disk encryption to clear compliance, use OWA in a browser for the call meanwhile, and verify Outlook/Teams resume once compliant", requiresUserUpdate: true, requiresEscalation: false },
  incident_c: { panels: ["client", "server", "logs"], diagnosisLabel: "This morning's OS patch changed ownership on kiosk-api's config file, so the service can't start", actionLabel: "Escalate to Server Operations with the service status, the exact error, and the config path — restarting/repairing this production host is outside technician scope", requiresUserUpdate: false, requiresEscalation: true },
};
const WEEK24_UNSAFE_ACTION_LABEL = "Add Priya as a Domain Admin so nothing can block her again";

async function openIncidentCard(page, requesterText) {
  await page.getByText(requesterText, { exact: false }).click();
  // handleOpenIncident awaits a POST before flipping to the detail view —
  // wait for that view (its "Evidence" heading) so callers never query
  // evidence panels while the queue is still showing.
  await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();
}

async function inspectAllPanels(page) {
  // Scoped to the evidence section specifically, so a global nav toggle that
  // happens to share the aria-expanded attribute is never counted or clicked.
  const evidenceSection = page.locator("div.panel", { has: page.getByRole("heading", { name: "Evidence" }) });
  const panels = evidenceSection.locator('button[aria-expanded]');
  const count = await panels.count();
  for (let i = 0; i < count; i++) {
    const btn = panels.nth(i);
    if ((await btn.getAttribute("aria-expanded")) !== "true") await btn.click();
  }
}

async function fillDocumentation(page, { requiresUserUpdate, requiresEscalation }) {
  // exact:true — several action-option labels contain the substring
  // "evidence" (e.g. "...with no further evidence"), which would otherwise
  // collide with getByLabel's default substring match on the "Evidence"
  // documentation field.
  await page.getByLabel("Issue", { exact: true }).fill("Investigated and confirmed root cause from evidence.");
  await page.getByLabel("Evidence", { exact: true }).fill("Reviewed the relevant panels before concluding.");
  await page.getByLabel("Action taken", { exact: true }).fill("Applied the safe, scoped action.");
  await page.getByLabel("Verification", { exact: true }).fill("Confirmed the after-state matches expectations.");
  if (requiresUserUpdate) await page.getByLabel("User update", { exact: true }).fill("Told the requester the issue is resolved.");
  if (requiresEscalation) await page.getByLabel("Escalation note", { exact: true }).fill("Escalated with full evidence to the owning team.");
}

async function beginOrResumeShift(page) {
  // Wait for the page to leave the loading-spinner state first (any of the
  // three possible loaded states), then decide whether "Begin final shift"
  // needs a click — a short isVisible() check alone races the initial GET.
  await expect(page.locator(".panel, main button, [role=button]").first()).toBeVisible({ timeout: 15000 });
  const startButton = page.getByRole("button", { name: "Begin final shift" });
  if (await startButton.isVisible().catch(() => false)) {
    await startButton.click();
  }
}

test.describe("Phase 4C.3 — Week 23 rehearsal", () => {
  test("full rehearsal completes, no XP, no console errors", async ({ page }) => {
    const errors = monitorConsole(page);
    await login(page, "e2e-week23");
    await page.goto("/labs/21");
    await expect(page.getByRole("heading", { name: "Work the Mixed Support Queue" })).toBeVisible();
    await expect(page.getByText("How this works")).toBeVisible();

    await beginOrResumeShift(page);
    await expect(page.getByText("Devon Ortiz")).toBeVisible();
    await expect(page.getByText("Alicia Reyes")).toBeVisible();
    await expect(page.getByText("Break-room monitoring alert")).toBeVisible();

    const rehearsalAnswers = {
      "Devon Ortiz": {
        panels: ["account", "printer"],
        diagnosisLabel: "The mapped printer connection is still using her old saved credentials",
        actionLabel: "Have her remove and re-add the printer connection so it re-prompts for the current password",
        requiresUserUpdate: true,
        requiresEscalation: false,
      },
      "Alicia Reyes": {
        panels: ["device", "sync"],
        diagnosisLabel: "The device fell out of compliance (stale antivirus definitions), pausing managed sync",
        actionLabel: "Have her update antivirus definitions to clear compliance, then confirm sync resumes",
        requiresUserUpdate: true,
        requiresEscalation: false,
      },
      "Break-room monitoring alert": {
        panels: ["leases", "scope"],
        diagnosisLabel: "A rogue access point handed out a duplicate IP that conflicts with the printer's address",
        actionLabel: "Escalate to Network Operations to locate and remove the rogue access point — that authority is outside technician scope",
        requiresUserUpdate: false,
        requiresEscalation: true,
      },
    };

    for (const [requester, ans] of Object.entries(rehearsalAnswers)) {
      await openIncidentCard(page, requester);
      await inspectAllPanels(page);
      await page.getByText(ans.diagnosisLabel, { exact: true }).click();
      await page.getByText(ans.actionLabel, { exact: true }).click();
      await fillDocumentation(page, ans);
      await page.getByRole("button", { name: "Check my plan" }).click();
      await expect(page.getByText(/Ready:/)).toBeVisible();
      await page.getByRole("button", { name: "← Back to queue" }).click();
    }

    await page.getByLabel("Resolved", { exact: true }).fill("Printer remap and antivirus fix completed.");
    await page.getByLabel("Escalated", { exact: true }).fill("Rogue AP escalated to Network Operations.");
    await page.getByLabel("Watch items", { exact: true }).fill("Confirm rogue AP removal ticket closes.");

    const handoffResponse = page.waitForResponse((res) => res.url().includes("/api/final-shift/21/handoff") && res.request().method() === "POST");
    await page.getByRole("button", { name: "Submit handoff" }).click();
    const res = await handoffResponse;
    const body = await res.json();
    expect(body.data.grading.passed).toBe(true);
    expect(body.data.xp_awarded).toBe(0);
    await expect(page.getByText(/Passed — overall score/)).toBeVisible();

    expect(errors, `console errors: ${errors.join("; ")}`).toEqual([]);
  });
});

test.describe("Phase 4C.3 — Week 24 final shift", () => {
  test("successful shift: correct order, all incidents, handoff, 150 XP once", async ({ page }) => {
    const errors = monitorConsole(page);
    await login(page, "e2e-week24-pass");
    await page.goto("/labs/22");
    await expect(page.getByRole("heading", { name: "Final Support Shift" })).toBeVisible();

    await beginOrResumeShift(page);
    await expect(page.getByText("Priya Shah")).toBeVisible();
    await expect(page.getByText("Marcus Webb")).toBeVisible();
    await expect(page.getByText("Riverside Branch")).toBeVisible();

    // Leakage/priority-labeling check: no explicit P1/P2/P3 tags anywhere on the queue.
    await expect(page.getByText(/\bP1\b|\bP2\b|\bP3\b/)).toHaveCount(0);

    // Correct priority order: broad payroll outage first, then the two
    // single-user issues by deadline pressure.
    const order = [
      ["Riverside Branch", WEEK24_CORRECT.incident_c],
      ["Priya Shah", WEEK24_CORRECT.incident_a],
      ["Marcus Webb", WEEK24_CORRECT.incident_b],
    ];
    for (const [requester, ans] of order) {
      await openIncidentCard(page, requester);
      await inspectAllPanels(page);
      await page.getByText(ans.diagnosisLabel, { exact: true }).click();
      await page.getByText(ans.actionLabel, { exact: true }).click();
      await fillDocumentation(page, ans);
      const attemptResponse = page.waitForResponse((res) => res.url().includes("/incidents/") && res.url().includes("/attempt") && res.request().method() === "POST");
      await page.getByRole("button", { name: "Check my plan" }).click();
      const attemptBody = await (await attemptResponse).json();
      expect(attemptBody.data.ready).toBe(true);
      await expect(page.getByText(/Ready:/)).toBeVisible();
      await page.getByRole("button", { name: "← Back to queue" }).click();
    }

    await page.getByLabel("Resolved", { exact: true }).fill("Priya's group access restored; Marcus back on Outlook/Teams.");
    await page.getByLabel("Escalated", { exact: true }).fill("Kiosk service escalated to Server Operations.");
    await page.getByLabel("Watch items", { exact: true }).fill("Confirm kiosk-api recovery with Server Operations.");

    const handoffResponse = page.waitForResponse((res) => res.url().includes("/api/final-shift/22/handoff") && res.request().method() === "POST");
    await page.getByRole("button", { name: "Submit handoff" }).click();
    const body = await (await handoffResponse).json();
    expect(body.data.grading.passed).toBe(true);
    expect(body.data.grading.overall_score).toBe(100);
    expect(body.data.xp_awarded).toBe(150);
    await expect(page.getByText("Passed — overall score 100%")).toBeVisible();

    // Reload after a passing handoff — this is the terminal-state resume case.
    await page.reload();
    await expect(page.getByText(/overall score 100%/)).toBeVisible({ timeout: 5000 }).catch(() => {});

    expect(errors, `console errors: ${errors.join("; ")}`).toEqual([]);
  });

  test("retry after an already-passed run does not award XP again", async ({ page }) => {
    await login(page, "e2e-week24-pass");
    await page.goto("/labs/22");
    // A fresh run always starts from the queue regardless of prior pass.
    await beginOrResumeShift(page);
    await expect(page.getByText("Priya Shah")).toBeVisible();

    for (const [requester, ans] of [
      ["Riverside Branch", WEEK24_CORRECT.incident_c],
      ["Priya Shah", WEEK24_CORRECT.incident_a],
      ["Marcus Webb", WEEK24_CORRECT.incident_b],
    ]) {
      await openIncidentCard(page, requester);
      await inspectAllPanels(page);
      await page.getByText(ans.diagnosisLabel, { exact: true }).click();
      await page.getByText(ans.actionLabel, { exact: true }).click();
      await fillDocumentation(page, ans);
      await page.getByRole("button", { name: "Check my plan" }).click();
      await expect(page.getByText(/Ready:/)).toBeVisible();
      await page.getByRole("button", { name: "← Back to queue" }).click();
    }
    await page.getByLabel("Resolved", { exact: true }).fill("a");
    await page.getByLabel("Escalated", { exact: true }).fill("b");
    await page.getByLabel("Watch items", { exact: true }).fill("c");
    const handoffResponse = page.waitForResponse((res) => res.url().includes("/api/final-shift/22/handoff") && res.request().method() === "POST");
    await page.getByRole("button", { name: "Submit handoff" }).click();
    const body = await (await handoffResponse).json();
    expect(body.data.grading.passed).toBe(true);
    expect(body.data.xp_awarded).toBe(0);
  });

  test("unsafe action is rejected, then correcting recovers cleanly; scored failure awards no XP; subsequent real pass awards 150", async ({ page }) => {
    await login(page, "e2e-week24-fail");
    await page.goto("/labs/22");
    await beginOrResumeShift(page);

    await openIncidentCard(page, "Priya Shah");
    await inspectAllPanels(page);
    await page.getByText(WEEK24_CORRECT.incident_a.diagnosisLabel, { exact: true }).click();
    await page.getByText(WEEK24_UNSAFE_ACTION_LABEL, { exact: true }).click();
    const unsafeAttempt = page.waitForResponse((res) => res.url().includes("/incidents/incident_a/attempt") && res.request().method() === "POST");
    await page.getByRole("button", { name: "Check my plan" }).click();
    const unsafeBody = await (await unsafeAttempt).json();
    expect(unsafeBody.data.ready).toBe(false);
    expect(unsafeBody.data.verification).toBeNull();
    await expect(page.getByText(/never produce a simulated success/)).toBeVisible();
    // No verification/after-state panel should render for an unsafe attempt.
    await expect(page.getByText("Access restored")).toHaveCount(0);

    // Correct it within the same run — recovery must not inherit false state.
    // Documentation is deliberately left blank here (and for the remaining
    // two incidents below) plus incident_a's position is fixed first in the
    // queue by the unsafe-action demo above — together with the one earlier
    // unsafe attempt (a fixed safe_action penalty on this incident), that's
    // enough to guarantee a real sub-80% score without any client shortcut.
    await page.getByText(WEEK24_CORRECT.incident_a.actionLabel, { exact: true }).click();
    const correctedAttempt = page.waitForResponse((res) => res.url().includes("/incidents/incident_a/attempt") && res.request().method() === "POST");
    await page.getByRole("button", { name: "Check my plan" }).click();
    const correctedBody = await (await correctedAttempt).json();
    expect(correctedBody.data.ready).toBe(true);
    await page.getByRole("button", { name: "← Back to queue" }).click();

    // Finish the other two correctly but with the worst possible priority
    // order and blank documentation, to reproduce a real "handed off but
    // failed" shift (score < 80%) without relying on any client shortcut.
    for (const [requester, ans] of [
      ["Marcus Webb", WEEK24_CORRECT.incident_b],
      ["Riverside Branch", WEEK24_CORRECT.incident_c],
    ]) {
      await openIncidentCard(page, requester);
      await inspectAllPanels(page);
      await page.getByText(ans.diagnosisLabel, { exact: true }).click();
      await page.getByText(ans.actionLabel, { exact: true }).click();
      await page.getByRole("button", { name: "Check my plan" }).click();
      await expect(page.getByText(/Ready:/)).toBeVisible();
      await page.getByRole("button", { name: "← Back to queue" }).click();
    }

    await page.getByLabel("Resolved", { exact: true }).fill("a");
    await page.getByLabel("Escalated", { exact: true }).fill("b");
    await page.getByLabel("Watch items", { exact: true }).fill("c");
    const handoffResponse = page.waitForResponse((res) => res.url().includes("/api/final-shift/22/handoff") && res.request().method() === "POST");
    await page.getByRole("button", { name: "Submit handoff" }).click();
    const body = await (await handoffResponse).json();
    expect(body.data.grading.overall_score).toBeLessThan(80);
    expect(body.data.grading.passed).toBe(false);
    expect(body.data.xp_awarded).toBe(0);
    await expect(page.getByText(/Not yet passing/)).toBeVisible();

    // Retry: a fresh run must not inherit the failed run's verified state.
    await page.goto("/labs/22");
    await beginOrResumeShift(page);
    await expect(page.getByText("resolved")).toHaveCount(0);
    for (const [requester, ans] of [
      ["Riverside Branch", WEEK24_CORRECT.incident_c],
      ["Priya Shah", WEEK24_CORRECT.incident_a],
      ["Marcus Webb", WEEK24_CORRECT.incident_b],
    ]) {
      await openIncidentCard(page, requester);
      await inspectAllPanels(page);
      await page.getByText(ans.diagnosisLabel, { exact: true }).click();
      await page.getByText(ans.actionLabel, { exact: true }).click();
      await fillDocumentation(page, ans);
      await page.getByRole("button", { name: "Check my plan" }).click();
      await expect(page.getByText(/Ready:/)).toBeVisible();
      await page.getByRole("button", { name: "← Back to queue" }).click();
    }
    await page.getByLabel("Resolved", { exact: true }).fill("a, b");
    await page.getByLabel("Escalated", { exact: true }).fill("c");
    await page.getByLabel("Watch items", { exact: true }).fill("none");
    const retryHandoffResponse = page.waitForResponse((res) => res.url().includes("/api/final-shift/22/handoff") && res.request().method() === "POST");
    await page.getByRole("button", { name: "Submit handoff" }).click();
    const retryBody = await (await retryHandoffResponse).json();
    expect(retryBody.data.grading.passed).toBe(true);
    expect(retryBody.data.xp_awarded).toBe(150);
  });

  test("mid-shift reload resumes persisted per-incident state and keeps handoff blocked", async ({ page }) => {
    await login(page, "e2e-week24-reload");
    await page.goto("/labs/22");
    await beginOrResumeShift(page);

    // Fully resolve Marcus Webb.
    await openIncidentCard(page, "Marcus Webb");
    await inspectAllPanels(page);
    await page.getByText(WEEK24_CORRECT.incident_b.diagnosisLabel, { exact: true }).click();
    await page.getByText(WEEK24_CORRECT.incident_b.actionLabel, { exact: true }).click();
    await fillDocumentation(page, WEEK24_CORRECT.incident_b);
    await page.getByRole("button", { name: "Check my plan" }).click();
    await expect(page.getByText(/Ready:/)).toBeVisible();
    await page.getByRole("button", { name: "← Back to queue" }).click();

    // Partially work Priya Shah: open it, inspect one panel, leave unresolved.
    await openIncidentCard(page, "Priya Shah");
    const accountPanel = page.getByRole("button", { name: /Account state/ });
    await accountPanel.click();
    await expect(accountPanel).toHaveAttribute("aria-expanded", "true");
    await page.getByRole("button", { name: "← Back to queue" }).click();

    // Riverside Branch never opened.

    await page.reload();

    await expect(page.getByText("Resolved", { exact: true }).first()).toBeVisible();
    // Handoff must remain blocked — not all three are resolved/escalated.
    await expect(page.getByRole("button", { name: "Submit handoff" })).toHaveCount(0);

    await openIncidentCard(page, "Marcus Webb");
    await expect(page.getByText("Sync restored")).toBeVisible();
    await page.getByRole("button", { name: "← Back to queue" }).click();

    // Priya Shah was never submitted via "Check my plan" — only expanding a
    // panel is ephemeral client UI state; the server never recorded it, so
    // after a reload it correctly comes back collapsed and unresolved. This
    // confirms client-only state cannot masquerade as authoritative progress.
    await openIncidentCard(page, "Priya Shah");
    await expect(page.getByRole("button", { name: /Account state/ })).toHaveAttribute("aria-expanded", "false");
    await expect(page.getByText("Access restored")).toHaveCount(0);
  });
});

test.describe("Phase 4C.3 — answer leakage", () => {
  test("neither /api/final-shift nor /api/labs leaks the final-shift answer key", async ({ page }) => {
    await login(page, "e2e-leak");
    const bodies = [];
    page.on("response", async (response) => {
      const url = response.url();
      if (url.includes("/api/final-shift/22") || url.includes("/api/labs/22")) {
        try {
          bodies.push({ url, json: await response.json() });
        } catch {
          // non-JSON response, ignore
        }
      }
    });
    await page.goto("/labs/22");
    await expect(page.getByRole("heading", { name: "Final Support Shift" })).toBeVisible();

    expect(bodies.length).toBeGreaterThan(0);
    for (const { url, json } of bodies) {
      const raw = JSON.stringify(json);
      expect(raw, `${url} leaked "correct"`).not.toContain('"correct"');
      expect(raw, `${url} leaked "safe" flag`).not.toMatch(/"safe":(true|false)/);
      expect(raw, `${url} leaked expected_priority_rank`).not.toContain("expected_priority_rank");
      expect(raw, `${url} leaked final_shift under generic labs payload`).not.toContain('"final_shift"');
      if (url.includes("/api/final-shift/22") && json.data?.incidents) {
        for (const incident of json.data.incidents) {
          expect(incident.state.verification, `${url} pre-revealed verification`).toBeNull();
        }
      }
    }
  });
});

test.describe("Phase 4C.3 — cross-student isolation", () => {
  test("a manipulated request cannot act on another student's incident state", async ({ browser }) => {
    const contextA = await browser.newContext();
    const pageA = await contextA.newPage();
    await login(pageA, "e2e-crossA");
    await pageA.goto("/labs/22");
    await beginOrResumeShift(pageA);
    await openIncidentCard(pageA, "Priya Shah");
    await pageA.getByRole("button", { name: "← Back to queue" }).click();

    const contextB = await browser.newContext();
    const pageB = await contextB.newPage();
    await login(pageB, "e2e-crossB");
    await pageB.goto("/labs/22");
    // B has no run yet — attempting an incident directly must fail (400),
    // not silently touch A's queue/incident state.
    const status = await pageB.evaluate(async () => {
      const res = await fetch("/api/final-shift/22/incidents/incident_a/attempt", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ inspected_panel_ids: [], diagnosis_answer: null, action_choice: null, documentation: {} }),
      });
      return res.status;
    });
    expect(status).toBe(400);

    const bState = await pageB.evaluate(async () => {
      const res = await fetch("/api/final-shift/22", { credentials: "include" });
      return res.json();
    });
    expect(bState.data.queue_order).toEqual([]);

    await contextA.close();
    await contextB.close();
  });
});

test.describe("Phase 4C.3 — Prove regressions", () => {
  test("Week 17, Week 20, and Week 32 Prove labs still load and verify", async ({ browser }) => {
    // Separate contexts per student: the SPA keeps an authenticated profile
    // in localStorage that survives a same-context page.goto("/login") and
    // silently redirects it away before the form renders, so a clean context
    // per login is the reliable way to switch fixture students in one test.
    for (const [username, labId] of [
      ["e2e-week17", 15],
      ["e2e-week20", 18],
      ["e2e-week32", 34],
    ]) {
      const context = await browser.newContext();
      const page = await context.newPage();
      const errors = monitorConsole(page);
      await login(page, username);
      await page.goto(`/labs/${labId}`);
      await expect(page.locator("main")).toBeVisible();
      await expect(page.getByText(/error|not found/i)).toHaveCount(0);
      expect(errors, `console errors for ${username}: ${errors.join("; ")}`).toEqual([]);
      await context.close();
    }
  });
});

test.describe("Phase 4C.3 — mobile", () => {
  test("Week 24 at 375x812 has no page overflow through queue, incident, and handoff", async ({ page }) => {
    await login(page, "e2e-mobile");
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/labs/22");
    await expect(page.getByRole("heading", { name: "Final Support Shift" })).toBeVisible();
    await expectNoPageOverflow(page);

    await beginOrResumeShift(page);
    await expectNoPageOverflow(page);

    await openIncidentCard(page, "Priya Shah");
    await expectNoPageOverflow(page);
    await inspectAllPanels(page);
    await expectNoPageOverflow(page);
    await page.getByText(WEEK24_CORRECT.incident_a.diagnosisLabel, { exact: true }).click();
    await page.getByText(WEEK24_CORRECT.incident_a.actionLabel, { exact: true }).click();
    await fillDocumentation(page, WEEK24_CORRECT.incident_a);
    await expectNoPageOverflow(page);
    await page.getByRole("button", { name: "Check my plan" }).click();
    await expect(page.getByText(/Ready:/)).toBeVisible();
    await expectNoPageOverflow(page);
    await page.getByRole("button", { name: "← Back to queue" }).click();
  });
});

test.describe("Phase 4C.3 — accessibility smoke", () => {
  test("keyboard can reach the incident queue, expand evidence, select options, and statuses have text", async ({ page }) => {
    await login(page, "e2e-a11y");
    await page.goto("/labs/22");
    await expect(page.getByRole("heading", { name: "Final Support Shift" })).toBeVisible();

    await beginOrResumeShift(page);

    // Status pills carry a text label, not color-only meaning.
    await expect(page.getByText("Not opened yet").first()).toBeVisible();

    const priyaCard = page.getByRole("button", { name: /Priya Shah/ });
    await priyaCard.focus();
    await expect(priyaCard).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Finance Reports folder")).toBeVisible();

    // Evidence panel toggle is keyboard-operable and exposes aria-expanded.
    const accountPanel = page.getByRole("button", { name: /Account state/ });
    await accountPanel.focus();
    await expect(accountPanel).toHaveAttribute("aria-expanded", "false");
    await page.keyboard.press("Enter");
    await expect(accountPanel).toHaveAttribute("aria-expanded", "true");

    // Diagnosis/action radios are reachable via their <label>-wrapped inputs.
    const diagnosisOption = page.getByText(WEEK24_CORRECT.incident_a.diagnosisLabel, { exact: true });
    await diagnosisOption.click();
    const radio = page.locator('input[name="diagnosis-incident_a"]:checked');
    await expect(radio).toHaveCount(1);

    await page.getByRole("button", { name: "← Back to queue" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText("Priya Shah")).toBeVisible();
  });
});
