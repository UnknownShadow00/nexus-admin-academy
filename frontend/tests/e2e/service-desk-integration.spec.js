// Real end-to-end coverage for the Nexus <-> Service Desk simulator
// integration: requires BOTH apps running together behind one origin
// (e.g. the nexus-staging Compose stack), not the isolated single-service
// local harness used by the other specs in this directory.
//
// Required env vars (no defaults — this must never silently run against
// production or a half-configured stack):
//   NEXUS_E2E_BASE_URL          e.g. http://192.168.0.101:18081
//   NEXUS_E2E_STUDENT_A_USERNAME / _PASSWORD
//   NEXUS_E2E_STUDENT_B_USERNAME / _PASSWORD
//   NEXUS_E2E_ADMIN_USERNAME / _PASSWORD
//
// The two student accounts and the admin account are expected to be
// disposable/staging-only fixtures, not real student data.

import { expect, test } from "@playwright/test";

function requireEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} must be set to run the Service Desk integration E2E spec.`);
  }
  return value;
}

const baseUrl = requireEnv("NEXUS_E2E_BASE_URL");
const studentAUsername = requireEnv("NEXUS_E2E_STUDENT_A_USERNAME");
const studentAPassword = requireEnv("NEXUS_E2E_STUDENT_A_PASSWORD");
const studentBUsername = requireEnv("NEXUS_E2E_STUDENT_B_USERNAME");
const studentBPassword = requireEnv("NEXUS_E2E_STUDENT_B_PASSWORD");
const adminUsername = requireEnv("NEXUS_E2E_ADMIN_USERNAME");
const adminPassword = requireEnv("NEXUS_E2E_ADMIN_PASSWORD");

const TICKET_ID = "INC2401";
const SCENARIO_STABLE_KEY = "inc2401";

async function studentLogin(page, username, password) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
}

async function adminLogin(page) {
  await page.goto("/admin-login");
  await page.getByLabel("Username").fill(adminUsername);
  await page.getByLabel("Password").fill(adminPassword);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/admin$/);
}

// The backend's CSRF-origin-validation middleware rejects state-changing
// requests (POST/PUT/PATCH/DELETE) made with a session cookie unless the
// Origin header matches a trusted origin. Real browser fetch() calls made
// from in-page JS set this automatically; Playwright's page.request client
// does not, since it is not executed by the page's own JS engine. Any direct
// POST made via page.request in this spec must set it explicitly.
function withOrigin(extra) {
  return { ...extra, headers: { ...extra?.headers, origin: baseUrl } };
}

async function getMyAssignment(page, stableKey) {
  const response = await page.request.get("/api/service-desk/assignments");
  expect(response.ok()).toBeTruthy();
  const assignments = await response.json();
  const assignment = assignments.find((a) => a.scenario.stable_key === stableKey);
  expect(assignment, `assignment for ${stableKey} should exist`).toBeTruthy();
  return assignment;
}

test.describe("Service Desk integration (requires an integrated stack)", () => {
  test("offline outbox retries grading evidence in original order", async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await studentLogin(page, studentAUsername, studentAPassword);
    const assignment = await getMyAssignment(page, SCENARIO_STABLE_KEY);
    const started = await page.request.post(
      `/api/service-desk/assignments/${assignment.id}/attempts`,
      withOrigin({}),
    );
    expect(started.ok()).toBeTruthy();
    const attemptId = (await started.json()).id;

    await page.goto(`/service-desk/tickets/${TICKET_ID}`);
    await expect(page.getByText(TICKET_ID).first()).toBeVisible();
    await page.route(/\/api\/service-desk\/attempts\/\d+\/(events|hints)$/, (route) => route.abort());

    await page.getByLabel("Add a note").fill("Offline evidence note.");
    await page.getByRole("button", { name: "Add internal note" }).click();
    await page.getByRole("link", { name: /Directory/ }).click();
    await expect(page.getByRole("heading", { name: "Directory", exact: true })).toBeVisible();
    await page.getByText("Avery Brooks", { exact: true }).click();
    await page.getByRole("button", { name: "Unlock account" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Unlock account" }).click();
    await page.goto(`/service-desk/tickets/${TICKET_ID}`);
    await page.getByRole("button", { name: /I don't know how to fix this/i }).click();

    await expect(page.getByText(/Saving…|Sync problem — retrying/)).toBeVisible();
    const readOutbox = () => page.evaluate(() => {
      const key = Object.keys(localStorage).find((candidate) => candidate.startsWith("nexus-sd-outbox-v1:"));
      return key ? JSON.parse(localStorage.getItem(key) || "{}") : null;
    });
    const pendingBeforeRefresh = await readOutbox();
    expect(pendingBeforeRefresh.items).toHaveLength(3);
    const queuedTypes = pendingBeforeRefresh.items.map((item) => item.event.event_type);
    const queuedKeys = pendingBeforeRefresh.items.map((item) => item.event.idempotency_key);
    expect(queuedTypes).toEqual(["ticket.add_note", "directory.unlock_account", "ticket.reveal_hint"]);
    const storedTypes = ["ticket.add_note", "directory.unlock_account", "hint_requested"];

    await page.reload();
    await expect(page.getByText("Offline evidence note.")).toBeVisible();
    expect((await readOutbox()).items.map((item) => item.event.idempotency_key)).toEqual(queuedKeys);
    const retriedRequests = [];
    const retriedResponses = [];
    page.on("request", (request) => {
      if (request.method() === "POST" && /\/api\/service-desk\/attempts\/\d+\/(events|hints)$/.test(request.url())) {
        retriedRequests.push({ url: request.url(), body: request.postDataJSON() });
      }
    });
    page.on("response", async (response) => {
      if (response.request().method() === "POST" && /\/api\/service-desk\/attempts\/\d+\/(events|hints)$/.test(response.url())) {
        retriedResponses.push({ url: response.url(), status: response.status() });
      }
    });
    await page.unroute(/\/api\/service-desk\/attempts\/\d+\/(events|hints)$/);
    await page.evaluate(() => window.dispatchEvent(new Event("online")));
    await expect.poll(() => retriedResponses.length).toBeGreaterThan(0);
    expect(retriedRequests.map((request) => request.body.idempotency_key)).toEqual(queuedKeys);
    expect(retriedRequests.map((request) => request.url)).toEqual([
      `${baseUrl}/api/service-desk/attempts/${attemptId}/events`,
      `${baseUrl}/api/service-desk/attempts/${attemptId}/events`,
      `${baseUrl}/api/service-desk/attempts/${attemptId}/hints`,
    ]);
    expect(retriedResponses.map((response) => response.status)).toEqual([201, 201, 201]);
    await expect.poll(async () => (await readOutbox()).items.length).toBe(0);
    await expect(page.getByText("Saving…")).toBeHidden();

    const adminContext = await browser.newContext();
    const adminPage = await adminContext.newPage();
    await adminLogin(adminPage);
    await expect.poll(async () => {
      const response = await adminPage.request.get(`/api/admin/service-desk/attempts/${attemptId}`);
      return (await response.json()).events.map((event) => event.event_type);
    }).toEqual(storedTypes);
    const timeline = await (await adminPage.request.get(`/api/admin/service-desk/attempts/${attemptId}`)).json();
    const retried = timeline.events.filter((event) => storedTypes.includes(event.event_type));
    expect(retried.map((event) => event.event_type)).toEqual(storedTypes);
    expect(new Set(retried.map((event) => event.idempotency_key))).toEqual(new Set(queuedKeys));
    expect(retried).toHaveLength(3);
    await adminPage.goto("/admin/service-desk-review");
    await expect(adminPage.getByText(/#\d+ directory\.unlock_account/)).toBeVisible();
    await adminContext.close();
    await context.close();
  });

  test("student resolves a ticket through the real UI; grade, XP, and evidence are Nexus-authoritative", async ({ browser }) => {
    // --- Student A: work the ticket through the real Service Desk UI ---
    const contextA1 = await browser.newContext();
    const pageA1 = await contextA1.newPage();
    await studentLogin(pageA1, studentAUsername, studentAPassword);

    const assignmentBefore = await getMyAssignment(pageA1, SCENARIO_STABLE_KEY);
    const hadPriorAttempt = assignmentBefore.most_recent_attempt !== null;

    await pageA1.goto(`/service-desk/tickets/${TICKET_ID}`);
    await pageA1.waitForTimeout(1000);
    await expect(pageA1.getByText(TICKET_ID).first()).toBeVisible();

    // Satisfy the INC2401 directory objective: unlock Avery Brooks.
    // "Unlock account" is a trigger that opens a DirectoryActionDialog confirm
    // modal; the modal's confirm button has the SAME accessible name as the
    // trigger, so it must be clicked twice (open, then confirm-scoped-to-dialog).
    await pageA1.getByRole("link", { name: /Directory/ }).click();
    await expect(pageA1.getByRole("heading", { name: "Directory", exact: true })).toBeVisible();
    await pageA1.getByText("Avery Brooks", { exact: true }).click();
    const unlockTrigger = pageA1.getByRole("button", { name: "Unlock account" });
    await expect(unlockTrigger.first()).toBeVisible();
    await unlockTrigger.first().click();
    const directoryEventResponse = pageA1.waitForResponse(async (response) => {
      if (!response.url().includes("/api/service-desk/attempts/") || !response.url().endsWith("/events") || response.request().method() !== "POST") {
        return false;
      }
      return (await response.request().postDataJSON()).event_type === "directory.unlock_account";
    });
    await pageA1
      .getByRole("dialog")
      .getByRole("button", { name: "Unlock account" })
      .click();
    await expect(pageA1.getByText(/Account unlocked\. New sign-in attempts/)).toBeVisible();
    expect((await directoryEventResponse).status()).toBe(201);
    await expect(pageA1.getByText("Saving…")).toBeHidden();

    // Add an internal note, then resolve and close the ticket.
    await pageA1.goto(`/service-desk/tickets/${TICKET_ID}`);
    await pageA1.waitForTimeout(1000);
    const noteBox = pageA1.getByPlaceholder(/note/i).or(pageA1.locator("textarea").first());
    if (await noteBox.count()) {
      await noteBox.first().fill("Unlocked the account after confirming identity with the requester.");
      const addNoteButton = pageA1.getByRole("button", { name: /add.*note/i });
      if (await addNoteButton.count()) {
        await addNoteButton.first().click();
        await pageA1.waitForTimeout(500);
      }
    }

    // ResolveDialog is a two-step modal: fill note + verified checkbox,
    // "Continue to review" shows the grade preview, then "Resolve ticket"
    // (or "Close anyway" if unverified) actually calls onConfirm.
    await pageA1.getByRole("button", { name: "Resolve / close" }).click();
    await pageA1.waitForTimeout(500);
    await pageA1.getByLabel("Resolution note").fill(
      "Unlocked the account; verified the requester could sign in.",
    );
    await pageA1.getByRole("checkbox", { name: /verified the requester/i }).check();
    await pageA1.getByRole("button", { name: "Continue to review" }).click();
    await pageA1.waitForTimeout(500);
    await pageA1.getByRole("button", { name: "Resolve ticket" }).click();
    await pageA1.waitForTimeout(1500);

    // --- Verify Nexus is now authoritative for this attempt ---
    const assignmentAfter = await getMyAssignment(pageA1, SCENARIO_STABLE_KEY);
    expect(assignmentAfter.most_recent_attempt, "an attempt should now exist").toBeTruthy();
    const attemptId = assignmentAfter.most_recent_attempt.id;

    const attemptResponse = await pageA1.request.get(`/api/service-desk/attempts/${attemptId}`);
    expect(attemptResponse.ok()).toBeTruthy();
    const attempt = await attemptResponse.json();
    expect(attempt.grade, "attempt should have a server-computed grade").toBeTruthy();
    expect(attempt.grade.passed).toBe(true);
    expect(attempt.grade.overall_score).toBeGreaterThan(0);
    expect(attempt.status).toBe("completed");
    await contextA1.close();

    // --- Idempotent completion: replaying the same complete call must not double-award XP ---
    const contextIdem = await browser.newContext();
    const pageIdem = await contextIdem.newPage();
    await studentLogin(pageIdem, studentAUsername, studentAPassword);
    const beforeXp = await pageIdem.request.get("/api/service-desk/assignments");
    const repeatResponse = await pageIdem.request.post(
      `/api/service-desk/attempts/${attemptId}/complete`,
      withOrigin({ data: { idempotency_key: "e2e-repeat-should-be-a-no-op" } }),
    );
    expect(repeatResponse.status()).toBe(200);
    const repeatGrade = await repeatResponse.json();
    expect(repeatGrade.overall_score).toBe(attempt.grade.overall_score);
    // A second, independent replay with the SAME key must also be a no-op.
    const repeatResponse2 = await pageIdem.request.post(
      `/api/service-desk/attempts/${attemptId}/complete`,
      withOrigin({ data: { idempotency_key: "e2e-repeat-should-be-a-no-op" } }),
    );
    expect(repeatResponse2.status()).toBe(200);
    expect((await repeatResponse2.json()).overall_score).toBe(attempt.grade.overall_score);
    await contextIdem.close();

    // --- Resume/cross-device: a completely clean second browser context, same student ---
    const contextA2 = await browser.newContext();
    const pageA2 = await contextA2.newPage();
    await studentLogin(pageA2, studentAUsername, studentAPassword);
    const resumedAttempt = await (
      await pageA2.request.get(`/api/service-desk/attempts/${attemptId}`)
    ).json();
    expect(resumedAttempt.status).toBe("completed");
    expect(resumedAttempt.grade.passed).toBe(true);
    await contextA2.close();

    // --- Cross-student isolation: student B must not be able to read A's attempt ---
    const contextB = await browser.newContext();
    const pageB = await contextB.newPage();
    await studentLogin(pageB, studentBUsername, studentBPassword);
    const forbidden = await pageB.request.get(`/api/service-desk/attempts/${attemptId}`);
    expect(forbidden.status()).toBe(403);
    await contextB.close();

    // --- Mentor/admin: full event timeline is visible, feedback can be added ---
    const contextAdmin = await browser.newContext();
    const pageAdmin = await contextAdmin.newPage();
    await adminLogin(pageAdmin);
    const timelineResponse = await pageAdmin.request.get(
      `/api/admin/service-desk/attempts/${attemptId}`,
    );
    expect(timelineResponse.ok()).toBeTruthy();
    const timeline = await timelineResponse.json();
    const eventTypes = timeline.events.map((event) => event.event_type);
    expect(eventTypes).toContain("ticket.close");
    expect(eventTypes.some((type) => type.startsWith("directory."))).toBe(true);

    await pageAdmin.goto("/admin/service-desk-review");
    await expect(pageAdmin.getByRole("heading", { name: "Event timeline" })).toBeVisible();
    await expect(pageAdmin.getByText(/#\d+ directory\.unlock_account/)).toBeVisible();

    const feedbackResponse = await pageAdmin.request.post(
      `/api/admin/service-desk/attempts/${attemptId}/feedback`,
      withOrigin({ data: { mentor_feedback: "Nice work verifying identity before unlocking the account." } }),
    );
    expect(feedbackResponse.ok()).toBeTruthy();
    await contextAdmin.close();

    // --- Student sees the mentor feedback ---
    const contextA3 = await browser.newContext();
    const pageA3 = await contextA3.newPage();
    await studentLogin(pageA3, studentAUsername, studentAPassword);
    const withFeedback = await (
      await pageA3.request.get(`/api/service-desk/attempts/${attemptId}`)
    ).json();
    expect(withFeedback.grade.mentor_feedback).toBe(
      "Nice work verifying identity before unlocking the account.",
    );
    await contextA3.close();
  });
});
