// Real end-to-end coverage for the Nexus <-> Service Desk simulator
// integration: requires BOTH apps running together behind one browser
// origin. Since service-desk-app moved into this repo, that's satisfied
// either by scripts/e2e/start_local_stack.sh (Vite dev-server proxies
// /service-desk and /api to locally-started Service Desk + backend
// processes — see frontend/vite.config.js) or by a real Compose stack
// (e.g. nexus-staging). Both set NEXUS_E2E_BASE_URL to a single origin
// that serves both apps, so this spec doesn't need to know which.
//
// Required env vars (no defaults — this must never silently run against
// production or a half-configured stack):
//   NEXUS_E2E_BASE_URL          e.g. http://192.168.0.101:18081
//   NEXUS_E2E_STUDENT_A_USERNAME / _PASSWORD
//   NEXUS_E2E_STUDENT_B_USERNAME / _PASSWORD
//   NEXUS_E2E_STUDENT_D_USERNAME / _PASSWORD
//   NEXUS_E2E_ADMIN_USERNAME / _PASSWORD
//
// The student and admin accounts are expected to be disposable
// local/staging-only fixtures, not real student data.

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
const studentCUsername = requireEnv("NEXUS_E2E_STUDENT_C_USERNAME");
const studentCPassword = requireEnv("NEXUS_E2E_STUDENT_C_PASSWORD");
const studentDUsername = requireEnv("NEXUS_E2E_STUDENT_D_USERNAME");
const studentDPassword = requireEnv("NEXUS_E2E_STUDENT_D_PASSWORD");
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
  test("snapshot-only sync persists every formerly local simulator domain", async ({ browser }) => {
    test.setTimeout(90_000);
    const sourceContext = await browser.newContext();
    const page = await sourceContext.newPage();
    await studentLogin(page, studentAUsername, studentAPassword);
    const assignment = await getMyAssignment(page, SCENARIO_STABLE_KEY);
    const attemptId = (await (await page.request.post(
      `/api/service-desk/assignments/${assignment.id}/attempts`, withOrigin({}),
    )).json()).id;
    const snapshot = async () => (await (await page.request.get(`/api/service-desk/attempts/${attemptId}`)).json()).current_state;

    await page.goto('/service-desk/tools/company-chat?contact=directory-user-avery-brooks');
    await page.getByLabel(/Message Avery Brooks/).fill('Snapshot-only chat message.');
    await page.getByRole('button', { name: 'Send' }).click();
    await expect.poll(snapshot).toMatchObject({ nexus_service_desk_attempt: { chatThreads: { 'directory-user-avery-brooks': { messages: expect.arrayContaining([expect.objectContaining({ body: 'Snapshot-only chat message.' })]) } } } });

    await page.goto('/service-desk/tools/asset-management');
    await page.getByText('NX-4831', { exact: true }).first().click();
    await page.locator('#status-NX-4831').selectOption({ index: 1 });
    await page.getByRole('button', { name: 'Update status' }).click();
    await page.getByRole('dialog').getByRole('button', { name: /Mark / }).click();
    await expect.poll(snapshot).toMatchObject({ nexus_service_desk_attempt: { assetOverlays: { 'NX-4831': expect.any(Object) } } });

    await page.goto('/service-desk/tools/pc-shelf');
    await page.getByRole('button', { name: 'Add computer' }).first().click();
    await page.locator('#pc-shelf-add-computer').selectOption('SD6893');
    await page.getByRole('dialog').getByRole('button', { name: 'Add to shelf' }).click();
    await expect.poll(snapshot).toMatchObject({ nexus_service_desk_attempt: { pcShelfOverlays: { SD6893: { present: true } } } });

    await page.goto('/service-desk/tools/server-room');
    await page.getByRole('tab', { name: 'Devices' }).click();
    await page.getByRole('button', { name: 'Restart device' }).first().click();
    await page.getByRole('dialog').getByRole('button', { name: 'Restart device' }).click();
    await expect.poll(snapshot).toMatchObject({ nexus_service_desk_attempt: { serverRoomOverlays: { 'metro-isp': expect.any(Object) } } });

    await page.goto('/service-desk/tools/computer-deployment');
    await page.getByRole('button', { name: 'Start' }).click();
    await expect.poll(snapshot).toMatchObject({ nexus_service_desk_attempt: { activeDeploymentRunId: expect.any(String), deploymentRuns: expect.any(Object) } });

    await page.goto('/service-desk/tools/shipping-manager');
    await page.getByLabel('Recipient name').fill('Avery Brooks');
    await page.getByRole('checkbox', { name: 'Computer', exact: true }).check();
    await page.getByLabel('Provisioned PC').selectOption('SD9099');
    await page.getByRole('button', { name: 'Ship' }).click();
    await expect.poll(snapshot).toMatchObject({ nexus_service_desk_attempt: { shipments: expect.any(Object), lastShippingAddress: { recipientName: 'Avery Brooks' } } });
    await sourceContext.close();

    const cleanContext = await browser.newContext();
    const cleanPage = await cleanContext.newPage();
    await studentLogin(cleanPage, studentAUsername, studentAPassword);
    await cleanPage.goto('/service-desk/tools/company-chat?contact=directory-user-avery-brooks');
    await expect(cleanPage.getByText('Snapshot-only chat message.')).toBeVisible();
    await cleanPage.goto('/service-desk/tools/pc-shelf');
    await expect(cleanPage.getByText('SD6893', { exact: true })).toBeVisible();
    await cleanContext.close();
  });

  test("offline snapshot-only outbox replays formerly local changes in order", async ({ browser }) => {
    test.setTimeout(60_000);
    const context = await browser.newContext();
    const page = await context.newPage();
    await studentLogin(page, studentBUsername, studentBPassword);
    const assignment = await getMyAssignment(page, SCENARIO_STABLE_KEY);
    const attemptId = (await (await page.request.post(
      `/api/service-desk/assignments/${assignment.id}/attempts`, withOrigin({}),
    )).json()).id;
    await page.route(/\/api\/service-desk\/attempts\/\d+\/snapshot$/, route => route.abort());
    await page.goto('/service-desk/tools/company-chat?contact=directory-user-avery-brooks');
    await page.getByLabel(/Message Avery Brooks/).fill('Offline snapshot chat.');
    await page.getByRole('button', { name: 'Send' }).click();
    await page.goto('/service-desk/tools/pc-shelf');
    await page.getByRole('button', { name: 'Add computer' }).first().click();
    await page.locator('#pc-shelf-add-computer').selectOption('SD6893');
    await page.getByRole('dialog').getByRole('button', { name: 'Add to shelf' }).click();
    const outbox = await page.evaluate(() => {
      const key = Object.keys(localStorage).find(key => key.startsWith('nexus-sd-outbox-v1:'));
      return JSON.parse(localStorage.getItem(key) || '{}').items;
    });
    expect(outbox.length).toBeGreaterThanOrEqual(2);
    expect(outbox.every(item => item.event.event_type === 'snapshot.persisted')).toBeTruthy();
    const keys = outbox.map(item => item.event.idempotency_key);
    await page.reload();
    await page.unroute(/\/api\/service-desk\/attempts\/\d+\/snapshot$/);
    await page.evaluate(() => window.dispatchEvent(new Event('online')));
    await expect.poll(async () => (await (await page.request.get(`/api/service-desk/attempts/${attemptId}`)).json()).current_state).toMatchObject({
      nexus_service_desk_attempt: {
        chatThreads: { 'directory-user-avery-brooks': { messages: expect.arrayContaining([expect.objectContaining({ body: 'Offline snapshot chat.' })]) } },
        pcShelfOverlays: { SD6893: { present: true } },
      },
    });
    await expect.poll(() => page.evaluate(() => {
      const key = Object.keys(localStorage).find(key => key.startsWith('nexus-sd-outbox-v1:'));
      return JSON.parse(localStorage.getItem(key) || '{}').items.length;
    })).toBe(0);
    await context.close();
    expect(keys).toHaveLength(2);
  });

  test("offline outbox retries grading evidence in original order", async ({ browser }) => {
    // This is the longest test in the file: route interception, offline
    // queueing across three event types, a reload, an online-triggered
    // retry, and an admin-side timeline check. The default 30s test budget
    // is tight for that on a shared CI runner (observed failing mid-flow at
    // ~30s in CI while passing locally); double it rather than trim steps.
    test.setTimeout(60_000);
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
    await page.route(/\/api\/service-desk\/attempts\/\d+\/(actions|events|hints)$/, (route) => route.abort());

    await page.getByLabel("Add a note").fill("Offline evidence note.");
    await page.getByRole("button", { name: "Add internal note" }).click();
    await page.getByRole("link", { name: /Directory/ }).click();
    // The note click above just queued an offline-outbox write (its POST is
    // being aborted by the route handler above) and triggered the sync-retry
    // UI's own state update; that extra async work can briefly delay this
    // client-side navigation's render under CI's slower CPU, past the
    // default 5s timeout. Give it more room rather than racing it.
    await expect(page.getByRole("heading", { name: "Directory", exact: true })).toBeVisible({
      timeout: 15000,
    });
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
      if (request.method() === "POST" && /\/api\/service-desk\/attempts\/\d+\/(actions|events|hints)$/.test(request.url())) {
        retriedRequests.push({ url: request.url(), body: request.postDataJSON() });
      }
    });
    page.on("response", async (response) => {
      if (response.request().method() === "POST" && /\/api\/service-desk\/attempts\/\d+\/(actions|events|hints)$/.test(response.url())) {
        retriedResponses.push({ url: response.url(), status: response.status() });
      }
    });
    await page.unroute(/\/api\/service-desk\/attempts\/\d+\/(actions|events|hints)$/);
    await page.evaluate(() => window.dispatchEvent(new Event("online")));
    await expect.poll(() => retriedResponses.length).toBeGreaterThan(0);
    expect(retriedRequests.map((request) => request.body.idempotency_key)).toEqual(queuedKeys);
    expect(retriedRequests.map((request) => request.url)).toEqual([
      `${baseUrl}/api/service-desk/attempts/${attemptId}/actions`,
      `${baseUrl}/api/service-desk/attempts/${attemptId}/actions`,
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

  test("completion waits for pending Service Desk evidence", async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await studentLogin(page, studentBUsername, studentBPassword);
    const assignment = await getMyAssignment(page, SCENARIO_STABLE_KEY);
    const started = await page.request.post(`/api/service-desk/assignments/${assignment.id}/attempts`, withOrigin({}));
    const attemptId = (await started.json()).id;
    await page.goto(`/service-desk/tickets/${TICKET_ID}`);
    await page.route(/\/api\/service-desk\/attempts\/\d+\/(actions|events|hints|complete)$/, (route) => route.abort());

    await page.getByRole("link", { name: /Directory/ }).click();
    await expect(page.getByRole("heading", { name: "Directory", exact: true })).toBeVisible();
    await page.getByRole("button", { name: /Avery Brooks abrooks/ }).click();
    await expect(page.getByRole("heading", { name: "Avery Brooks", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Unlock account" })).toBeVisible();
    await page.getByRole("button", { name: "Unlock account" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Unlock account" }).click();
    await page.goto(`/service-desk/tickets/${TICKET_ID}`);
    await page.getByLabel("Add a note").fill("Completion must wait for sync.");
    await page.getByRole("button", { name: "Add internal note" }).click();
    await page.getByRole("button", { name: "Resolve / close" }).click();
    await page.getByLabel("Resolution note").fill("Unlocked the account and verified sign-in.");
    await page.getByRole("checkbox", { name: /verified the requester/i }).check();
    await page.getByRole("button", { name: "Continue to review" }).click();
    await page.getByRole("button", { name: "Resolve ticket" }).click();
    await expect(page.getByText(/Saving…|Sync problem — retrying/)).toBeVisible();

    const beforeReconnect = await page.request.get(`/api/service-desk/attempts/${attemptId}`);
    const pendingAttempt = await beforeReconnect.json();
    expect(pendingAttempt.status).toBe("in_progress");
    expect(pendingAttempt.grade).toBeNull();

    await page.unroute(/\/api\/service-desk\/attempts\/\d+\/(actions|events|hints|complete)$/);
    await page.evaluate(() => window.dispatchEvent(new Event("online")));
    await expect.poll(async () => (await (await page.request.get(`/api/service-desk/attempts/${attemptId}`)).json()).status).toBe("completed");
    const completed = await (await page.request.get(`/api/service-desk/attempts/${attemptId}`)).json();
    expect(completed.grade).toBeTruthy();
    const replay = await page.request.post(`/api/service-desk/attempts/${attemptId}/complete`, withOrigin({ data: { idempotency_key: "pending-completion-replay" } }));
    expect(replay.status()).toBe(200);
    const adminContext = await browser.newContext();
    const adminPage = await adminContext.newPage();
    await adminLogin(adminPage);
    const timeline = await (await adminPage.request.get(`/api/admin/service-desk/attempts/${attemptId}`)).json();
    expect(timeline.events.map((event) => event.event_type)).toEqual(["directory.unlock_account", "ticket.add_note", "ticket.close"]);
    expect(new Set(timeline.events.map((event) => event.idempotency_key)).size).toBe(3);
    expect(timeline.grade.id).toBe(completed.grade.id);
    await adminContext.close();
    await context.close();
  });

  test("Student D restores the full ticket and directory snapshot in a clean browser", async ({ browser }) => {
    const sourceContext = await browser.newContext();
    const sourcePage = await sourceContext.newPage();
    await studentLogin(sourcePage, studentDUsername, studentDPassword);
    const assignment = await getMyAssignment(sourcePage, SCENARIO_STABLE_KEY);
    const started = await sourcePage.request.post(
      `/api/service-desk/assignments/${assignment.id}/attempts`,
      withOrigin({}),
    );
    expect(started.ok()).toBeTruthy();
    const attemptId = (await started.json()).id;

    await sourcePage.goto(`/service-desk/tickets/${TICKET_ID}`);
    await sourcePage.getByLabel("Add a note").fill("Student D clean-browser restoration note.");
    await sourcePage.getByRole("button", { name: "Add internal note" }).click();
    await sourcePage.getByRole("link", { name: /Directory/ }).click();
    await expect(sourcePage.getByRole("heading", { name: "Directory", exact: true })).toBeVisible();
    await sourcePage.getByText("Avery Brooks", { exact: true }).click();
    await sourcePage.getByRole("button", { name: "Unlock account" }).click();
    await sourcePage.getByRole("dialog").getByRole("button", { name: "Unlock account" }).click();
    await expect(sourcePage.getByText(/Account unlocked\. New sign-in attempts/)).toBeVisible();

    await expect.poll(async () => {
      const response = await sourcePage.request.get(`/api/service-desk/attempts/${attemptId}`);
      return (await response.json()).current_state;
    }).toMatchObject({
      schema_version: 1,
      nexus_service_desk_attempt: {
        assetOverlays: expect.any(Object),
        chatThreads: expect.any(Object),
        deploymentRuns: expect.any(Object),
        directoryOverlays: { "directory-user-avery-brooks": { locked: false } },
        remoteDesktopOverlays: expect.any(Object),
        ticketOverlays: { [TICKET_ID]: { notes: [expect.objectContaining({ body: "Student D clean-browser restoration note." })] } },
      },
    });
    await sourceContext.close();

    // A new browser context has neither the Service Desk attempt cache nor its
    // outbox. The only possible restoration source is the Nexus snapshot.
    const cleanContext = await browser.newContext();
    const cleanPage = await cleanContext.newPage();
    await studentLogin(cleanPage, studentDUsername, studentDPassword);
    await cleanPage.goto(`/service-desk/tickets/${TICKET_ID}`);
    await expect(cleanPage.getByText("Student D clean-browser restoration note.")).toBeVisible();
    await cleanPage.getByRole("link", { name: /Directory/ }).click();
    await cleanPage.getByRole("button", { name: /Avery Brooks abrooks/ }).click();
    await expect(cleanPage.getByRole("heading", { name: "Avery Brooks", exact: true })).toBeVisible();
    await expect(cleanPage.getByText("Account unlocked", { exact: true })).toBeVisible();
    await expect(cleanPage.getByRole("button", { name: "Already unlocked" })).toBeDisabled();
    await cleanContext.close();
  });

  test("student resolves a ticket through the real UI; grade, XP, and evidence are Nexus-authoritative", async ({ browser }) => {
    // --- Student A: work the ticket through the real Service Desk UI ---
    const contextA1 = await browser.newContext();
    const pageA1 = await contextA1.newPage();
    await studentLogin(pageA1, studentCUsername, studentCPassword);

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
      if (!response.url().includes("/api/service-desk/attempts/") || !response.url().endsWith("/actions") || response.request().method() !== "POST") {
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
    await studentLogin(pageIdem, studentCUsername, studentCPassword);
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
    await studentLogin(pageA2, studentCUsername, studentCPassword);
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
    expect(timeline.events.find((event) => event.event_type === "directory.unlock_account").trusted).toBe(true);

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
    await studentLogin(pageA3, studentCUsername, studentCPassword);
    const withFeedback = await (
      await pageA3.request.get(`/api/service-desk/attempts/${attemptId}`)
    ).json();
    expect(withFeedback.grade.mentor_feedback).toBe(
      "Nice work verifying identity before unlocking the account.",
    );
    await contextA3.close();
  });
});
