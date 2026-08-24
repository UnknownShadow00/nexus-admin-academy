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
const freshAUsername = requireEnv("NEXUS_E2E_FRESH_A_USERNAME");
const freshAPassword = requireEnv("NEXUS_E2E_FRESH_A_PASSWORD");
const freshBUsername = requireEnv("NEXUS_E2E_FRESH_B_USERNAME");
const freshBPassword = requireEnv("NEXUS_E2E_FRESH_B_PASSWORD");
const adminUsername = requireEnv("NEXUS_E2E_ADMIN_USERNAME");
const adminPassword = requireEnv("NEXUS_E2E_ADMIN_PASSWORD");
const endpointUsername = requireEnv("NEXUS_E2E_ENDPOINT_USERNAME");
const endpointPassword = requireEnv("NEXUS_E2E_ENDPOINT_PASSWORD");

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


async function completeWeekZero(page) {
  await page.goto("/");
  await page.getByRole("link", { name: "Start Training" }).first().click();
  await expect(page).toHaveURL(/\/lessons\/\d+$/);
  await page.getByRole("button", { name: "Mark lesson complete", exact: true }).click();
  await expect(page.getByRole("button", { name: "Orientation complete", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Take quiz", exact: true }).click();
  await expect(page).toHaveURL(/\/quizzes\/\d+$/);

  for (let index = 1; index <= 4; index += 1) {
    await expect(page.getByText("Question " + index + " of 4", { exact: true })).toBeVisible();
    const questionPanel = page.locator("section .panel").first();
    const questionText = await questionPanel.textContent();
    const correctOptions = questionText.includes("initial data collection")
      ? ["User information", "Device information", "Problem description"]
      : questionText.includes("future reporting")
        ? ["Category"]
        : questionText.includes("Level 2 hardware specialist")
          ? ["Escalation level"]
          : ["Progress notes"];
    for (const option of correctOptions) {
      await questionPanel.getByText(option, { exact: true }).click();
    }
    await page.getByRole("button", { name: index === 4 ? "Submit Quiz" : "Next", exact: true }).click();
  }

  await expect(page.getByText("Passed", { exact: true })).toBeVisible();
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

async function clickAndWaitForTrustedAction(page, buttonName) {
  const responsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      /\/api\/service-desk\/attempts\/\d+\/actions$/.test(response.url()),
  );
  await page.getByRole("button", { name: buttonName, exact: true }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(201);
}

async function resolveEndpointCase(page, scenario) {
  const assignment = await getMyAssignment(page, scenario.stableKey);
  const started = await page.request.post(
    `/api/service-desk/assignments/${assignment.id}/attempts`,
    withOrigin({}),
  );
  expect([200, 201]).toContain(started.status());
  const attemptId = (await started.json()).id;

  await page.goto(`/service-desk/tools/device-management?ticket=${scenario.ticketId}`);
  await expect(page.getByRole("heading", { name: "Device Management" })).toBeVisible();
  await page.getByRole("button", { name: `4. ${scenario.remediationLabel}` }).click();
  await expect(
    page.getByRole("alert").filter({
      hasText: "Inspect the device record and verify the requester or authorization before diagnosis or remediation.",
    }),
  ).toBeVisible();
  await clickAndWaitForTrustedAction(page, "1. Inspect device record");

  await page.goto(
    `/service-desk/tools/company-chat?contact=${scenario.contactId}&ticket=${scenario.ticketId}`,
  );
  await clickAndWaitForTrustedAction(page, "Run approved identity check");

  await page.goto(`/service-desk/tools/device-management?ticket=${scenario.ticketId}`);
  await clickAndWaitForTrustedAction(page, "3. Record evidence-based diagnosis");
  await clickAndWaitForTrustedAction(page, `4. ${scenario.remediationLabel}`);
  await clickAndWaitForTrustedAction(page, "5. Verify resulting device state");

  await page.goto(
    `/service-desk/tools/company-chat?contact=${scenario.contactId}&ticket=${scenario.ticketId}`,
  );
  await clickAndWaitForTrustedAction(page, "Ask user to retest original symptom");

  await page.goto(`/service-desk/tickets/${scenario.ticketId}`);
  await page.getByLabel("Add a note").fill(scenario.note);
  await clickAndWaitForTrustedAction(page, "Add internal note");
  await page.getByRole("button", { name: "Resolve / close" }).click();
  await page.getByLabel("I verified the requester has a working outcome").check();
  await page.getByRole("button", { name: "Continue to review" }).click();
  await page.getByRole("button", { name: "Resolve ticket", exact: true }).click();

  await expect.poll(async () => {
    const attempts = await (await page.request.get("/api/service-desk/attempts")).json();
    return attempts.find((attempt) => attempt.id === attemptId);
  }).toMatchObject({ status: "completed", score: 100, passed: true });
}


async function resolveFoundationalAccountCase(page, scenario) {
  const assignment = await getMyAssignment(page, scenario.stableKey);
  const completedQueueType = assignment.experience_mode === "guided" ? "earlier" : "practice";
  const started = await page.request.post(
    "/api/service-desk/assignments/" + assignment.id + "/attempts",
    withOrigin({}),
  );
  expect([200, 201]).toContain(started.status());

  await page.goto("/service-desk/tickets/" + scenario.ticketId);
  await expect(page.getByRole("heading", { name: scenario.title })).toBeVisible();
  await expect(page.getByText("Read").first()).toBeVisible();
  await expect(page.getByText("Investigate").first()).toBeVisible();
  await page.getByRole("link", { name: "Directory", exact: true }).click();
  await page.getByPlaceholder("Search name, username, or department").fill(scenario.requester);
  await page.getByRole("button", { name: new RegExp(scenario.requester) }).click();

  await expect(page.getByText("Account status has not been reviewed yet.")).toBeVisible();
  await page.getByRole("button", { name: "Review account state" }).click();
  await expect(page.getByText("Account state reviewed.", { exact: false })).toBeVisible();
  await page.goto(
    `/service-desk/tools/company-chat?contact=${scenario.contactId}&ticket=${scenario.ticketId}`,
  );
  await page.getByRole("button", { name: "Run approved identity check" }).click();
  await page.goto("/service-desk/tools/directory");
  await page.getByPlaceholder("Search name, username, or department").fill(scenario.requester);
  await page.getByRole("button", { name: new RegExp(scenario.requester) }).click();
  await page.getByRole("button", { name: "Record verified chat evidence" }).click();
  if (scenario.testPrimaryAuth) {
    await page.getByRole("button", { name: "Test primary password sign-in" }).click();
    await expect(page.getByText("Primary password authentication succeeds", { exact: false })).toBeVisible();
  }
  await page.getByLabel("Account diagnosis").selectOption(scenario.diagnosis);
  await page.getByRole("button", { name: "Record diagnosis" }).click();
  await expect(page.getByText("Diagnosis recorded from the reviewed account evidence.")).toBeVisible();

  await page.getByRole("button", { name: scenario.remediationTrigger, exact: true }).first().click();
  const remediationDialog = page.getByRole("dialog");
  if (scenario.remediationTrigger === "Reset password") {
    await expect(remediationDialog.getByRole("checkbox")).toBeChecked();
  }
  await remediationDialog.getByRole(
    "button",
    { name: scenario.remediationConfirm, exact: true },
  ).click();
  await page.getByRole("button", { name: "Test original sign-in" }).click();
  const signInDialog = page.getByRole("dialog", { name: "Simulated sign-in test" });
  await signInDialog.getByRole("button", { name: scenario.signInAction }).click();
  await expect(signInDialog.getByText("Checkpoint reached")).toBeVisible();
  await signInDialog.getByRole("button", { name: "Record successful sign-in test" }).click();
  await expect(page.getByText("The original sign-in path has been verified after remediation.")).toBeVisible();

  await page.goto(
    `/service-desk/tools/company-chat?contact=${scenario.contactId}&ticket=${scenario.ticketId}`,
  );
  await page.getByRole("button", { name: "Ask user to retest original symptom" }).click();
  await expect(
    page.getByText("It now works and I can continue.", { exact: false }).last(),
  ).toBeVisible();

  await page.getByRole("link", { name: "Dashboard", exact: true }).click();
  await page.getByRole("link", { name: new RegExp(scenario.title) }).click();
  await expect(page).toHaveURL(new RegExp("/service-desk/tickets/" + scenario.ticketId + "$"));
  await page.getByLabel("Add a note").fill(scenario.note);
  await page.getByRole("button", { name: "Add internal note" }).click();
  await expect(page.getByText(scenario.note, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Resolve / close" }).click();
  await page.getByLabel("I verified the requester has a working outcome").check();
  await page.getByRole("button", { name: "Continue to review" }).click();
  await expect(page.getByText("Ready to resolve", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Resolve ticket", exact: true }).click();

  await expect.poll(async () => {
    const current = await getMyAssignment(page, scenario.stableKey);
    return {
      queueType: current.queue_type,
      status: current.most_recent_attempt?.status,
    };
  }).toEqual({ queueType: completedQueueType, status: "completed" });
  return completedQueueType;
}

async function connectRemoteDesktop(page, ticketId, assetTag) {
  await page.goto(`/service-desk/tools/remote-desktop?ticket=${ticketId}`);
  await page.getByPlaceholder("Search by asset tag, hostname, or owner").fill(assetTag);
  await page.getByRole("button", { name: "Connect" }).click();
  const startButton = page.getByRole("button", { name: "Open Start menu" });
  const username = page.getByPlaceholder("e.g. jdoe");
  await expect(username.or(startButton)).toBeVisible();
  if (await username.isVisible()) {
    await username.fill("support.admin");
    await page.getByPlaceholder("Domain password").fill("simulation-only");
    await page.getByRole("button", { name: "OK" }).click();
  }
  await expect(startButton).toBeVisible();
}

async function openDesktopApp(page, appName) {
  await page.getByRole("button", { name: "Open Start menu" }).click();
  await page.getByRole("button", { name: appName, exact: true }).last().click();
  await expect(page.getByLabel(`${appName} window`)).toBeVisible();
}

async function prepareInc2401Workflow(page) {
  await connectRemoteDesktop(page, TICKET_ID, "NX-4831");
  await openDesktopApp(page, "Mail");
  await page.getByRole("button", { name: "Mark support alert reviewed" }).click();
  await openDesktopApp(page, "Web Browser");
  await page.getByRole("button", { name: "Retry portal sign-in" }).click();
  await openDesktopApp(page, "Settings");
  await page.getByRole("button", { name: "Applications", exact: true }).click();
  await page.getByRole("button", { name: "Clear support browser profile storage" }).click();
  await openDesktopApp(page, "Web Browser");
  await page.getByRole("button", { name: "Retry portal sign-in" }).click();
  await page.getByLabel("Student-authored internal note").fill(
    "I confirmed stale browser profile storage, applied the repair by clearing the profile, and verified the portal opened.",
  );
  await page.getByRole("button", { name: "Save internal note" }).click();
  await expect(page.getByRole("button", { name: "Close ticket" })).toBeEnabled();
}

test.describe("Service Desk integration (requires an integrated stack)", () => {

  test("BitLocker and offboarding are fully playable live endpoint workflows", async ({ browser }) => {
    test.setTimeout(300_000);
    const context = await browser.newContext({ viewport: { width: 375, height: 812 } });
    const page = await context.newPage();
    await studentLogin(page, endpointUsername, endpointPassword);

    const cases = [
      {
        contactId: "directory-user-morgan-ellis",
        note: "Verified Morgan and NEX-LT-2214, recorded the firmware-triggered recovery diagnosis, released the key through the approved channel, and confirmed the device booted.",
        remediationLabel: "Reveal recovery key through approved channel",
        stableKey: "bitlocker-recovery",
        ticketId: "INC3001",
      },
      {
        contactId: "directory-user-hr-adebayo-coker",
        note: "Verified HR authorization and NEX-LT-3390, confirmed access revocation and corporate-data reset handling, completed the reset and reassignment, and verified readiness for the new assignee.",
        remediationLabel: "Reset and reassign device",
        stableKey: "offboarding-device-reassignment",
        ticketId: "INC3002",
      },
    ];

    for (const scenario of cases) {
      await resolveEndpointCase(page, scenario);
    }

    const attempts = await (await page.request.get("/api/service-desk/attempts")).json();
    expect(attempts.filter((attempt) => attempt.passed && attempt.score === 100)).toHaveLength(2);
    const dimensions = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
    await context.close();
  });

  test("Week 0 unlocks an isolated four-ticket starter queue with a compact next-pack preview", async ({ browser }) => {
    test.setTimeout(180_000);
    const contextA = await browser.newContext({ viewport: { width: 375, height: 812 } });
    const pageA = await contextA.newPage();
    await studentLogin(pageA, freshAUsername, freshAPassword);

    let assignmentsResponse = await pageA.request.get("/api/service-desk/assignments");
    expect(assignmentsResponse.ok()).toBeTruthy();
    expect(await assignmentsResponse.json()).toEqual([]);

    await pageA.goto("/service-desk");
    await expect(pageA.getByRole("heading", { name: "My Service Desk" })).toBeVisible();
    await expect(pageA.getByText("Complete Nexus Orientation to begin your first Service Desk shift.")).toBeVisible();
    await expect(pageA.getByRole("region", { name: "Assigned" })).toHaveCount(0);
    await expect(pageA.locator('a[href^="/service-desk/tickets/"]')).toHaveCount(0);
    await pageA.goto("/service-desk/tickets/INC2511");
    await expect(pageA.getByRole("heading", { name: "Case unavailable" })).toBeVisible();

    await completeWeekZero(pageA);
    await pageA.goto("/service-desk");
    assignmentsResponse = await pageA.request.get("/api/service-desk/assignments");
    expect(assignmentsResponse.ok()).toBeTruthy();
    const assignments = await assignmentsResponse.json();
    expect(new Set(assignments.map((row) => row.scenario.stable_key))).toEqual(
      new Set(["locked-user-account", "password-reset", "mfa-reset", "inc2404"]),
    );
    expect(assignments.every((row) => row.queue_type === "assigned")).toBeTruthy();

    const progressA = pageA.getByRole("region", { name: "Training progress" });
    await expect(progressA.getByText("4", { exact: true })).toBeVisible();
    await expect(progressA.getByText("Available", { exact: true })).toBeVisible();
    await expect(pageA.getByRole("region", { name: "Assigned" })).toBeVisible();
    await expect(pageA.getByRole("heading", { name: "Practice" })).toBeVisible();
    await expect(pageA.getByText("No mastered cases yet", { exact: false })).toBeVisible();
    await expect(pageA.getByText("Next case pack", { exact: true })).toBeVisible();
    await expect(pageA.getByRole("heading", { name: "Desktop Support" })).toBeVisible();
    await expect(pageA.getByText("○ Reach Windows Fundamentals & Diagnostics")).toBeVisible();
    await expect(pageA.getByText(/○ Successfully resolve 2 Starter Support cases \(0\/2\)/)).toBeVisible();
    await expect(pageA.locator('a[href^="/service-desk/tickets/"]')).toHaveCount(4);
    await expect(pageA.getByText("Desktop opens with a temporary Windows profile")).toHaveCount(0);
    const dimensions = await pageA.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);

    const started = await pageA.request.post(
      "/api/service-desk/assignments/" + assignments[0].id + "/attempts",
      withOrigin({}),
    );
    expect(started.status()).toBe(201);
    await pageA.reload();
    await expect(progressA.getByText("3", { exact: true })).toBeVisible();
    await expect(progressA.getByText("1", { exact: true })).toBeVisible();
    await expect(progressA.getByText("In progress", { exact: true })).toBeVisible();

    await pageA.goto("/service-desk/tickets/INC2408");
    await expect(pageA.getByRole("heading", { name: "Case unavailable" })).toBeVisible();
    await contextA.close();

    const contextB = await browser.newContext();
    const pageB = await contextB.newPage();
    await studentLogin(pageB, freshBUsername, freshBPassword);
    const studentBAssignments = await (await pageB.request.get("/api/service-desk/assignments")).json();
    expect(studentBAssignments).toHaveLength(0);
    await pageB.goto("/service-desk");
    await expect(pageB.getByText("Complete Nexus Orientation to begin your first Service Desk shift.")).toBeVisible();
    await expect(pageB.locator('a[href^="/service-desk/tickets/"]')).toHaveCount(0);
    await contextB.close();
  });

  test("foundational account cases require investigation, remediation, verification, and documentation", async ({ browser }) => {
    test.setTimeout(180_000);
    const context = await browser.newContext({ viewport: { width: 375, height: 812 } });
    const page = await context.newPage();
    await studentLogin(page, freshAUsername, freshAPassword);
    if ((await (await page.request.get("/api/service-desk/assignments")).json()).length === 0) {
      await completeWeekZero(page);
    }

    const cases = [
      {
        contactId: "directory-user-taylor-morgan",
        diagnosis: "account-locked",
        note: "Reviewed Taylor's account and approved identity check, confirmed the lock, unlocked it, and verified the original sign-in path works.",
        remediationConfirm: "Unlock account",
        remediationTrigger: "Unlock account",
        requester: "Taylor Morgan",
        signInAction: "Attempt clean account sign-in",
        stableKey: "locked-user-account",
        testPrimaryAuth: false,
        ticketId: "INC2511",
        title: "Can't sign in after lunch",
      },
      {
        contactId: "directory-user-jordan-lee",
        diagnosis: "password-expired",
        note: "Reviewed Jordan's account and approved identity check, confirmed the expired password, issued a temporary password, and verified the required-change sign-in handoff.",
        remediationConfirm: "Issue temporary credential",
        remediationTrigger: "Reset password",
        requester: "Jordan Lee",
        signInAction: "Begin temporary-credential handoff",
        stableKey: "password-reset",
        testPrimaryAuth: false,
        ticketId: "INC2512",
        title: "Sign-in stops before the desktop loads",
      },
      {
        contactId: "directory-user-camille-reyes",
        diagnosis: "mfa-factor-unavailable",
        note: "Reviewed Camille's account, confirmed primary password authentication succeeds, reset the unavailable MFA factor, and verified re-registration is ready.",
        remediationConfirm: "Reset MFA",
        remediationTrigger: "Reset MFA",
        requester: "Camille Reyes",
        signInAction: "Test sign-in through second factor",
        stableKey: "mfa-reset",
        testPrimaryAuth: true,
        ticketId: "INC2513",
        title: "Approval prompts go to an old phone",
      },
    ];

    const completedQueueTypes = new Map();
    for (const scenario of cases) {
      completedQueueTypes.set(
        scenario.stableKey,
        await resolveFoundationalAccountCase(page, scenario),
      );
    }

    await page.goto("/service-desk");
    await expect(page.getByRole("region", { name: "Assigned" }).locator('a[href^="/service-desk/tickets/"]')).toHaveCount(1);
    const starterAssignments = await (
      await page.request.get("/api/service-desk/assignments")
    ).json();
    for (const scenario of cases) {
      const completed = starterAssignments.find(
        (assignment) => assignment.scenario.stable_key === scenario.stableKey,
      );
      expect(completed).toMatchObject({
        queue_type: completedQueueTypes.get(scenario.stableKey),
        most_recent_attempt: { status: "completed" },
      });
    }
    const dimensions = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
    await context.close();
  });

  test("admin scenario draft survives refresh and publishes an immutable version", async ({ page }) => {
    const suffix = Date.now();
    const stableKey = `e2e-printer-${suffix}`;
    const title = `E2E printer draft ${suffix}`;
    const definition = {
      title,
      slug: stableKey,
      category: "software",
      priority: "medium",
      difficulty: "easy",
      pointValue: 100,
      explanation: "Restarting the failed Print Spooler restores the local print queue.",
      description: {
        issue: "Print jobs disappear from one workstation while a nearby workstation prints normally.",
        reportedByLine: "Reported through the employee portal.",
        businessImpact: "The requester cannot print an onboarding pack.",
        troubleshooting: ["A nearby workstation can print to the same device."],
      },
      requester: {
        name: "Avery Brooks", department: "Finance", email: "avery@example.test",
        contact: "Ext. 10", location: "North office",
      },
      device: {
        assetTag: "NX-1000", deviceName: "FIN-LT-10", kind: "laptop",
        operatingSystem: "Windows 11", state: "active",
      },
      sla: { dueAt: "2026-08-08T12:00:00Z", target: "4 hours" },
      initialWorldState: { directoryOverlaySeeds: {}, assetOverlaySeeds: {}, chatMessageSeeds: [] },
      objectives: [{
        id: "document-resolution", order: 1, description: "Document the diagnosis and verification.",
        pointValue: 100, predicateType: "action_event_occurred",
        predicateParams: { actionType: "ticket.add_note", payloadMatch: { ticketId: stableKey.toUpperCase() } }, required: true,
      }],
      requiredActions: [], forbiddenActions: [],
      hints: [
        { id: "h1", order: 1, pointPenalty: 0, text: "Determine whether the failure follows the user, workstation, or printer." },
        { id: "h2", order: 2, pointPenalty: 5, text: "Inspect the affected workstation's Windows services." },
        { id: "h3", order: 3, pointPenalty: 5, text: "Check and restart the Print Spooler, then print a test page." },
      ],
    };

    await adminLogin(page);
    const created = await page.request.post("/api/admin/service-desk/scenarios", withOrigin({ data: {
      stable_key: stableKey, title, description: definition.description.issue,
      category: definition.category, difficulty: 1, definition_json: definition,
    } }));
    expect(created.status()).toBe(201);
    const scenario = await created.json();

    await page.goto(`/service-desk/admin/scenarios/${scenario.id}`);
    const titleInput = page.getByLabel("Title");
    await expect(titleInput).toHaveValue(title);
    const editedTitle = `${title} saved`;
    await titleInput.fill(editedTitle);
    await page.getByRole("button", { name: "Save Draft" }).click();
    await expect(page.getByText(/Draft v1 saved to Nexus/)).toBeVisible();

    await page.reload();
    await expect(page.getByLabel("Title")).toHaveValue(editedTitle);
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Publish Version" }).click();
    await expect(page.getByText(/Version 1 published/)).toBeVisible();

    await page.getByLabel("Title").fill(`${editedTitle} v2`);
    await page.getByRole("button", { name: "Save Draft" }).click();
    await expect(page.getByText(/Draft v2 saved to Nexus/)).toBeVisible();
    const reloaded = await (await page.request.get(`/api/admin/service-desk/scenarios/${scenario.id}`)).json();
    expect(reloaded.versions).toHaveLength(2);
    expect(reloaded.versions[0].status).toBe("published");
    expect(reloaded.versions[0].definition_json.title).toBe(editedTitle);
    expect(reloaded.versions[1].status).toBe("draft");
    await page.reload();
    await expect(page.getByLabel("Title")).toHaveValue(`${editedTitle} v2`);
  });

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

    await page.goto('/service-desk/tools/company-chat?contact=directory-user-avery-brooks&ticket=INC2401');
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
    await page.getByRole('button', { name: 'Ship', exact: true }).click();
    await expect.poll(snapshot).toMatchObject({ nexus_service_desk_attempt: { shipments: expect.any(Object), lastShippingAddress: { recipientName: 'Avery Brooks' } } });
    await sourceContext.close();

    const cleanContext = await browser.newContext();
    const cleanPage = await cleanContext.newPage();
    await studentLogin(cleanPage, studentAUsername, studentAPassword);
    await cleanPage.goto('/service-desk/tools/company-chat?contact=directory-user-avery-brooks&ticket=INC2401');
    await expect(cleanPage.getByText('Snapshot-only chat message.')).toBeVisible();
    await cleanPage.goto('/service-desk/tools/pc-shelf');
    await expect(
      cleanPage.locator('.sd-card-header__title').filter({ hasText: 'SD6893' }),
    ).toBeVisible();
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
    await page.goto('/service-desk/tools/company-chat?contact=directory-user-avery-brooks&ticket=INC2401');
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
    expect((await page.evaluate(() => {
      const key = Object.keys(localStorage).find(key => key.startsWith('nexus-sd-outbox-v1:'));
      return JSON.parse(localStorage.getItem(key) || '{}').items.map(item => item.event.idempotency_key);
    }))).toEqual(keys);
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
    expect(keys).toHaveLength(4);
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
    await page.getByRole("button", { name: "Unassign", exact: true }).click();
    await page.getByRole("button", { name: "Assign to me", exact: true }).click();

    await expect(page.getByText(/Saving…|Sync problem — retrying/)).toBeVisible();
    const readOutbox = () => page.evaluate(() => {
      const key = Object.keys(localStorage).find((candidate) => candidate.startsWith("nexus-sd-outbox-v1:"));
      return key ? JSON.parse(localStorage.getItem(key) || "{}") : null;
    });
    const pendingBeforeRefresh = await readOutbox();
    expect(pendingBeforeRefresh.items).toHaveLength(3);
    const queuedTypes = pendingBeforeRefresh.items.map((item) => item.event.event_type);
    const queuedKeys = pendingBeforeRefresh.items.map((item) => item.event.idempotency_key);
    expect(queuedTypes).toEqual(["ticket.add_note", "ticket.unassign", "ticket.assign"]);
    const storedTypes = ["ticket.add_note", "ticket.unassign", "ticket.assign"];

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
    await expect.poll(() => retriedResponses.length).toBe(3);
    expect(retriedRequests.map((request) => request.body.idempotency_key)).toEqual(queuedKeys);
    expect(retriedRequests.map((request) => request.url)).toEqual([
      `${baseUrl}/api/service-desk/attempts/${attemptId}/actions`,
      `${baseUrl}/api/service-desk/attempts/${attemptId}/actions`,
      `${baseUrl}/api/service-desk/attempts/${attemptId}/actions`,
    ]);
    expect(retriedResponses.map((response) => response.status)).toEqual([201, 201, 201]);
    await expect.poll(async () => (await readOutbox()).items.length).toBe(0);
    await expect(page.getByText("Saving…")).toBeHidden();

    const adminContext = await browser.newContext();
    const adminPage = await adminContext.newPage();
    await adminLogin(adminPage);
    await expect.poll(async () => {
      const response = await adminPage.request.get(`/api/admin/service-desk/attempts/${attemptId}`);
      return (await response.json()).events
        .filter((event) => event.event_type !== "snapshot.persisted")
        .map((event) => event.event_type);
    }).toEqual(storedTypes);
    const timeline = await (await adminPage.request.get(`/api/admin/service-desk/attempts/${attemptId}`)).json();
    const retried = timeline.events.filter((event) => storedTypes.includes(event.event_type));
    expect(retried.map((event) => event.event_type)).toEqual(storedTypes);
    expect(new Set(retried.map((event) => event.idempotency_key))).toEqual(new Set(queuedKeys));
    expect(retried).toHaveLength(3);
    await adminContext.close();
    await context.close();
  });

  test("completion waits for pending Service Desk evidence", async ({ browser }) => {
    test.setTimeout(90_000);
    const context = await browser.newContext();
    const page = await context.newPage();
    await studentLogin(page, studentBUsername, studentBPassword);
    await prepareInc2401Workflow(page);
    const assignment = await getMyAssignment(page, SCENARIO_STABLE_KEY);
    const attemptId = assignment.most_recent_attempt.id;
    await page.route(/\/api\/service-desk\/attempts\/\d+\/(actions|events|hints|complete)$/, (route) => route.abort());
    await page.getByRole("button", { name: "Close ticket" }).click();
    await expect(page.getByText(/Saving…|Sync problem — retrying/)).toBeVisible();

    const beforeReconnect = await page.request.get(`/api/service-desk/attempts/${attemptId}`);
    const pendingAttempt = await beforeReconnect.json();
    expect(pendingAttempt.status).toBe("in_progress");
    expect(pendingAttempt.grade).toBeNull();

    await page.unroute(/\/api\/service-desk\/attempts\/\d+\/(actions|events|hints|complete)$/);
    await page.evaluate(() => window.dispatchEvent(new Event("online")));
    await expect.poll(
      async () => (await (await page.request.get(`/api/service-desk/attempts/${attemptId}`)).json()).status,
      { timeout: 15_000 },
    ).toBe("completed");
    const completed = await (await page.request.get(`/api/service-desk/attempts/${attemptId}`)).json();
    expect(completed.grade).toBeTruthy();
    const replay = await page.request.post(`/api/service-desk/attempts/${attemptId}/complete`, withOrigin({ data: { idempotency_key: "pending-completion-replay" } }));
    expect(replay.status()).toBe(200);
    const adminContext = await browser.newContext();
    const adminPage = await adminContext.newPage();
    await adminLogin(adminPage);
    const timeline = await (await adminPage.request.get(`/api/admin/service-desk/attempts/${attemptId}`)).json();
    const evidenceEvents = timeline.events.filter((event) => event.event_type !== "snapshot.persisted");
    expect(evidenceEvents.map((event) => event.event_type)).toContain("ticket.close");
    expect(evidenceEvents.filter((event) => event.trusted)).toHaveLength(5);
    expect(new Set(evidenceEvents.map((event) => event.idempotency_key)).size).toBe(evidenceEvents.length);
    expect(timeline.grade.id).toBe(completed.grade.id);
    await adminContext.close();
    await context.close();
  });

  test("Student D restores ticket and asset state in a clean browser", async ({ browser }) => {
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
    await sourcePage.goto("/service-desk/tools/asset-management");
    await sourcePage.getByPlaceholder("Search assets").fill("NX-4831");
    await sourcePage.getByText("NX-4831", { exact: true }).first().click();
    const statusSelect = sourcePage.locator("#status-NX-4831");
    await statusSelect.selectOption({ index: 1 });
    const changedStatus = await statusSelect.inputValue();
    await sourcePage.getByRole("button", { name: "Update status" }).click();
    await sourcePage.getByRole("dialog").getByRole("button", { name: /Mark / }).click();

    await expect.poll(async () => {
      const response = await sourcePage.request.get(`/api/service-desk/attempts/${attemptId}`);
      return (await response.json()).current_state;
    }).toMatchObject({
      schema_version: 1,
      nexus_service_desk_attempt: {
        chatThreads: expect.any(Object),
        deploymentRuns: expect.any(Object),
        assetOverlays: { "NX-4831": { status: changedStatus } },
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
    await cleanPage.goto("/service-desk/tools/asset-management");
    await cleanPage.getByPlaceholder("Search assets").fill("NX-4831");
    await cleanPage.getByText("NX-4831", { exact: true }).first().click();
    await expect(cleanPage.locator("#status-NX-4831")).toHaveValue(changedStatus);
    await cleanContext.close();
  });

  test("student resolves a ticket through the real UI; grade, XP, and evidence are Nexus-authoritative", async ({ browser }) => {
    test.setTimeout(90_000);
    // --- Student A: work the ticket through the real Service Desk UI ---
    const contextA1 = await browser.newContext();
    const pageA1 = await contextA1.newPage();
    await studentLogin(pageA1, studentCUsername, studentCPassword);

    const assignmentBefore = await getMyAssignment(pageA1, SCENARIO_STABLE_KEY);
    const hadPriorAttempt = assignmentBefore.most_recent_attempt !== null;

    await pageA1.goto(`/service-desk/tickets/${TICKET_ID}`);
    await expect(pageA1.getByText(TICKET_ID).first()).toBeVisible();
    await prepareInc2401Workflow(pageA1);
    await pageA1.getByRole("button", { name: "Close ticket" }).click();
    await expect(pageA1.getByText("Server assessment complete")).toBeVisible({ timeout: 10_000 });
    await expect(pageA1.getByText("Saving…")).toBeHidden();

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
    expect(eventTypes).toContain("remote_desktop.perform_scenario_step");
    expect(timeline.events.find((event) => event.event_type === "remote_desktop.perform_scenario_step").trusted).toBe(true);

    await pageAdmin.goto("/admin/service-desk-review");
    await expect(pageAdmin.getByRole("heading", { name: "Event timeline" })).toBeVisible();
    await expect(pageAdmin.getByText(/#\d+ remote_desktop\.perform_scenario_step/).first()).toBeVisible();

    const feedbackResponse = await pageAdmin.request.post(
      `/api/admin/service-desk/attempts/${attemptId}/feedback`,
      withOrigin({ data: { mentor_feedback: "Nice work verifying the original portal symptom after the profile repair." } }),
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
      "Nice work verifying the original portal symptom after the profile repair.",
    );
    await contextA3.close();
  });

  test("INC2402 can be diagnosed, repaired, verified, and closed through Remote Desktop", async ({ page }) => {
    test.setTimeout(90_000);
    await studentLogin(page, studentAUsername, studentAPassword);
    await page.goto("/service-desk/tickets/INC2402");
    await expect(page.getByText("INC2402").first()).toBeVisible();

    await connectRemoteDesktop(page, "INC2402", "NX-7714");
    await openDesktopApp(page, "Command Prompt");
    await page.locator("#terminal-command").fill("ipconfig");
    await page.locator("#terminal-command").press("Enter");
    await page.locator("#terminal-command").fill("ping 10.77.14.1");
    await page.locator("#terminal-command").press("Enter");
    await openDesktopApp(page, "Settings");
    await page.getByRole("button", { name: "Repair network profile" }).click();
    await openDesktopApp(page, "System Information");
    await page.getByRole("button", { name: "Renew network address" }).click();
    await openDesktopApp(page, "Company Chat");
    await page.getByPlaceholder("Write a ticket update").fill("The scanner connection remained stable after the profile repair.");
    await page.getByRole("button", { name: "Send", exact: true }).click();
    await page.getByLabel("Student-authored internal note").fill(
      "I confirmed the managed profile caused the failure, applied the repair, renewed the address, and verified stable service.",
    );
    await page.getByRole("button", { name: "Save internal note" }).click();
    await page.getByRole("button", { name: "Close ticket" }).click();
    await expect(page.getByText("Server assessment complete")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("Saving…")).toBeHidden();

    const assignment = await getMyAssignment(page, "inc2402");
    const attempt = await (await page.request.get(
      `/api/service-desk/attempts/${assignment.most_recent_attempt.id}`,
    )).json();
    expect(attempt.status).toBe("completed");
    expect(attempt.grade.passed).toBe(true);
  });

  test("INC2404 requires real asset, shipping, note, and close actions", async ({ page }) => {
    test.setTimeout(90_000);
    await studentLogin(page, studentBUsername, studentBPassword);
    await page.goto("/service-desk/tickets/INC2404");
    await expect(page.getByText("INC2404").first()).toBeVisible();

    await page.goto("/service-desk/tools/asset-management");
    await page.getByPlaceholder("Search assets").fill("NX-9052");
    await page.getByText("NX-9052", { exact: true }).first().click();
    await page.getByRole("button", { name: "Test affected headset on known-good workstation" }).click();
    await page.getByRole("button", { name: "Test known-good headset on affected workstation" }).click();
    await page.locator("#status-NX-9052").selectOption("damaged");
    await page.getByRole("button", { name: "Update status" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Mark damaged" }).click();
    await expect(page.getByText("Asset status changed to damaged.")).toBeVisible();

    await page.goto("/service-desk/tools/shipping-manager");
    await page.getByLabel("Recipient name").fill("Elliot Ward");
    await page.getByRole("checkbox", { name: "Headset", exact: true }).check();
    await page.getByRole("radio", { name: /Express/ }).check();
    await page.getByRole("checkbox", { name: /Include return label/ }).check();
    await page.getByRole("button", { name: "Ship", exact: true }).click();
    await expect(page.getByText("Replacement shipped")).toBeVisible();

    await page.goto("/service-desk/tools/asset-management");
    await page.getByPlaceholder("Search assets").fill("NX-9052");
    await page.getByText("NX-9052", { exact: true }).first().click();
    await page.getByRole("button", { name: "Confirm clean audio with replacement" }).click();

    await page.goto("/service-desk/tickets/INC2404");
    const noteBox = page.getByPlaceholder(/note/i).or(page.locator("textarea").first());
    await noteBox.first().fill(
      "Confirmed the static followed the headset, marked NX-9052 damaged, and shipped Elliot a replacement for verification.",
    );
    await page.getByRole("button", { name: /add.*note/i }).first().click();
    await page.getByRole("button", { name: "Resolve / close" }).click();
    await page.getByLabel("Resolution note").fill(
      "Replacement headset shipped; Elliot will verify clear audio on the next call.",
    );
    await page.getByRole("checkbox", { name: /verified the requester/i }).check();
    await page.getByRole("button", { name: "Continue to review" }).click();
    await page.getByRole("button", { name: "Resolve ticket" }).click();
    await expect(page.getByText("Saving…")).toBeHidden();

    const assignment = await getMyAssignment(page, "inc2404");
    const attempt = await (await page.request.get(
      `/api/service-desk/attempts/${assignment.most_recent_attempt.id}`,
    )).json();
    expect(attempt.status).toBe("completed");
    expect(attempt.grade.passed).toBe(true);
  });

  test("launch curriculum scenarios expose their current student workflows", async ({ page }) => {
    await studentLogin(page, studentDUsername, studentDPassword);
    const scenarios = [
      ["INC2401", "Finance portal returns to sign-in after verification"],
      ["INC2405", "Facilities calendar shortcut shows a location error"],
      ["INC2407", "Internal sites fail while IP connectivity still works"],
      ["INC2501", "Desktop and Documents are missing after sign-in"],
      ["INC2506", "Assistant requests access to restricted salary records"],
      ["INC2508", "Employee entered credentials into a phishing page"],
    ];

    for (const [ticketId, title] of scenarios) {
      await page.goto(`/service-desk/tickets/${ticketId}`);
      await expect(page.getByText(ticketId).first()).toBeVisible();
      await expect(page.getByRole("heading", { name: title })).toBeVisible();
      await expect(page.getByRole("region", { name: "Ticket actions" })).toBeVisible();
      await expect(page.getByRole("navigation", { name: "Suggested tools" })).toBeVisible();
    }

    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/service-desk");
    await expect(page.getByRole("heading", { name: "My Service Desk" })).toBeVisible();
    const dimensions = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
  });

  test("workstation shell remains keyboard-operable at desktop and mobile viewports", async ({ browser }, testInfo) => {
    test.setTimeout(90_000);

    const runViewportCheck = async (viewport, screenshotName) => {
      const context = await browser.newContext({ viewport });
      const page = await context.newPage();
      await studentLogin(page, studentAUsername, studentAPassword);
      await connectRemoteDesktop(page, "INC2406", "NX-2047");

      const ticketWorkspace = page.getByRole("button", { name: "Ticket workspace" });
      await ticketWorkspace.focus();
      await expect(ticketWorkspace).toBeFocused();
      await page.keyboard.press("Enter");
      if (viewport.width < 1280) {
        await expect(ticketWorkspace).toBeHidden();
      } else {
        await expect(ticketWorkspace).toHaveAttribute("aria-expanded", "false");
      }

      const startButton = page.getByRole("button", { name: "Open Start menu" });
      await startButton.focus();
      await expect(startButton).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(startButton).toHaveAttribute("aria-expanded", "true");

      const terminalLauncher = page.getByRole("button", { name: "Command Prompt", exact: true }).last();
      await terminalLauncher.focus();
      await page.keyboard.press("Enter");
      const terminalWindow = page.getByLabel("Command Prompt window");
      await expect(terminalWindow).toBeVisible();

      const terminalInput = page.locator("#terminal-command");
      await terminalInput.fill("hostname");
      await terminalInput.press("Enter");
      await expect(terminalWindow).toContainText("PM-LT-41> hostname");
      await terminalInput.press("ArrowUp");
      await expect(terminalInput).toHaveValue("hostname");

      const minimizeButton = page.getByRole("button", { name: "Minimize Command Prompt" });
      await minimizeButton.focus();
      await page.keyboard.press("Enter");
      await expect(terminalWindow).toBeHidden();
      const focusTerminal = page.getByRole("button", { name: "Focus Command Prompt" });
      await focusTerminal.focus();
      await page.keyboard.press("Enter");
      await expect(terminalWindow).toBeVisible();

      await expect(page.getByRole("link", { name: "Back to Nexus" })).toBeVisible();
      const dimensions = await page.evaluate(() => ({
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
      }));
      expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);

      const screenshotPath = testInfo.outputPath(screenshotName);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: screenshotPath });
      await testInfo.attach(screenshotName, { path: screenshotPath, contentType: "image/png" });
      await context.close();
    };

    await runViewportCheck({ width: 1440, height: 1000 }, "workstation-desktop-1440x1000.png");
    await runViewportCheck({ width: 375, height: 812 }, "workstation-mobile-375x812.png");
  });
});
