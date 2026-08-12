import { expect, test } from "@playwright/test";

const studentUsername = process.env.NEXUS_E2E_STUDENT_USERNAME || "browser-training-student";
const studentPassword = process.env.NEXUS_E2E_STUDENT_PASSWORD || "BrowserTraining!2026";
const adminUsername = process.env.NEXUS_E2E_ADMIN_USERNAME || "browser-admin";
const adminPassword = process.env.NEXUS_E2E_ADMIN_PASSWORD || "BrowserAdmin!2026";
const apiBaseUrl = process.env.NEXUS_E2E_API_URL || "http://127.0.0.1:8011";
const browserBaseUrl = process.env.NEXUS_E2E_BASE_URL || "http://127.0.0.1:5173";
const allowCloudflareBeaconWarning = process.env.NEXUS_E2E_ALLOW_CLOUDFLARE_BEACON_WARNING === "true";

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
  const knownConsoleWarnings = [];
  const failedRequests = [];
  const knownFailedRequests = [];
  const httpErrors = [];
  let active = true;
  page.on("console", (message) => {
    if (!active) return;
    const text = message.text();
    if (message.type() !== "error") return;
    if (allowCloudflareBeaconWarning && isCloudflareBeaconCspWarning(text)) {
      knownConsoleWarnings.push(text);
      return;
    }
    consoleErrors.push(text);
  });
  page.on("requestfailed", (request) => {
    if (!active) return;
    const reason = request.failure()?.errorText || "unknown error";
    if (allowCloudflareBeaconWarning && isCloudflareBeaconCspRequest(request, reason)) {
      knownFailedRequests.push(`${request.method()} ${request.url()}: ${reason}`);
      return;
    }
    // SPA navigation intentionally cancels in-flight reads from the page being
    // left. Record every other failure, including any injected analytics.
    if (!reason.includes("ERR_ABORTED")) {
      failedRequests.push(`${request.method()} ${request.url()}: ${reason}`);
    }
  });
  page.on("response", (response) => {
    if (!active) return;
    if (response.status() >= 400) httpErrors.push(`${response.status()} ${response.url()}`);
  });
  return {
    consoleErrors,
    knownConsoleWarnings,
    failedRequests,
    knownFailedRequests,
    httpErrors,
    pause: () => { active = false; },
    resume: () => { active = true; },
  };
}

async function studentLogin(page, username = studentUsername, password = studentPassword) {
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

async function assertNoHorizontalOverflow(page) {
  const dimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width + 1);
}

test("student authentication rejects invalid credentials and protects private routes", async ({ page }) => {
  await page.goto("/progress");
  await expect(page).toHaveURL(/\/login$/);

  await page.getByLabel("Username").fill(studentUsername);
  await page.getByLabel("Password").fill("definitely-not-the-password");
  const rejectedLogin = page.waitForResponse((response) => response.url().endsWith("/auth/login"));
  await page.getByRole("button", { name: "Login" }).click();
  expect((await rejectedLogin).status()).toBe(401);
  await expect(page.getByText("Invalid credentials", { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);

  await page.getByLabel("Password").fill(studentPassword);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/progress");
  await expect(page.getByRole("heading", { name: "Progress", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Progress", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Browser Training Student" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto("/progress");
  await expect(page).toHaveURL(/\/login$/);
});

test("student follows My Training on desktop and mobile", async ({ page }) => {
  test.setTimeout(60_000);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await studentLogin(page);
  const monitor = monitorPage(page);

  await expect(page.getByRole("link", { name: "Today", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /Extra Practice/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "Progress", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: /Learning Path/i })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: /Begin Your IT Training|Continue where you left off/ })).toBeVisible();
  await assertNoHorizontalOverflow(page);

  await page.getByRole("link", { name: "This Week", exact: true }).click();
  await expect(page).toHaveURL(/\/training$/);
  await expect(page.getByRole("heading", { name: "My Training", exact: true })).toBeVisible();
  await expect(page.getByText("Weekly Roadmap")).toBeVisible();
  await expect(page.getByText(/Week 0 — Welcome to Nexus/).first()).toBeVisible();
  await assertNoHorizontalOverflow(page);

  await page.goto("/training/week/0");
  await page.reload();
  await expect(page.getByRole("heading", { name: "Welcome to Nexus", exact: true })).toBeVisible();
  await page.getByText(/Extra practice \(/).click();
  const ticketingVideo = page.locator("article").filter({ hasText: "Ticketing Systems" }).filter({ has: page.getByRole("link", { name: "Take Quiz" }) }).first();
  await expect(ticketingVideo.getByRole("link", { name: "Take Quiz" })).toHaveAttribute("href", /\/quizzes\/42$/);
  const markButton = ticketingVideo.getByRole("button", { name: "Mark Watched" });
  if (await markButton.count()) {
    await markButton.click();
    await expect(ticketingVideo.getByRole("link", { name: "Take Quiz" })).toBeVisible();
    await expect(ticketingVideo.getByRole("link", { name: "Watch Again" })).toBeVisible();
  }
  await assertNoHorizontalOverflow(page);

  await page.goto("/study-tracker");
  await expect(page).toHaveURL(/\/training\/content$/);
  await expect(page.getByRole("heading", { name: "All Course Content" })).toBeVisible();
  await page.getByRole("searchbox", { name: "Search course content" }).fill("Ticketing Systems");
  await expect(page.getByText("Ticketing Systems", { exact: true }).first()).toBeVisible();
  await page.getByRole("searchbox", { name: "Search course content" }).fill("");
  const catalogVideos = page.locator("[data-video-row]");
  await expect(catalogVideos).toHaveCount(137);
  for (const row of await catalogVideos.all()) {
    await expect(row.locator('a[href^="/quizzes/"]').first()).toBeVisible();
  }
  const mappedQuizRoutes = await catalogVideos.locator('a[href^="/quizzes/"]').evaluateAll((links) => [...new Set(links.map((link) => link.getAttribute("href").replace(/\/review$/, "")))]);
  expect(mappedQuizRoutes).toHaveLength(21);

  await page.getByRole("link", { name: "Quiz Library" }).click();
  await expect(page.getByRole("heading", { name: "Quiz Library" })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { name: "All Course Content" })).toBeVisible();
  await page.goForward();
  await expect(page.getByRole("heading", { name: "Quiz Library" })).toBeVisible();

  for (const route of mappedQuizRoutes) {
    const response = await page.request.get(`${apiBaseUrl}/api${route}`);
    const body = await response.json();
    expect(response.ok(), `mapped quiz route ${route}`).toBeTruthy();
    expect(body.data.questions.length, `mapped quiz route ${route} has questions`).toBeGreaterThan(0);
  }

  await page.goto("/training");
  await page.getByRole("button", { name: /Extra Practice/ }).click();
  for (const name of ["Guided Labs", "Networking Labs", "Command Library", "Terminal Practice"]) {
    await expect(page.getByRole("menuitem", { name, exact: true })).toBeVisible();
  }
  await expect(page.getByRole("menuitem", { name: "Support Tickets", exact: true })).toHaveCount(0);
  await expect(page.getByRole("menuitem", { name: "Capstones", exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "Progress", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Progress", exact: true })).toBeVisible();
  await expect(page.getByText("Course progress", { exact: true })).toBeVisible();
  await expect(page.getByText(/Average quiz score: .*Best quiz score:/)).toBeVisible();

  const studentRoutes = [
    ["/quizzes", "Quiz Library"],
    ["/labs", "Lab Exercises"],
    ["/cli-labs", "Networking Labs"],
    ["/commands", "Command Library"],
    ["/terminal", "Terminal Practice"],
  ];
  for (const [route, heading] of studentRoutes) {
    await page.goto(route);
    await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
    await assertNoHorizontalOverflow(page);
  }
  await page.goto("/training");
  await page.goto("/learning-path");
  await expect(page).toHaveURL(/\/training$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/training$/);
  await expect(page.getByRole("heading", { name: "My Training", exact: true })).toBeVisible();
  // Lesson IDs are not stable across a fresh seed vs. production's
  // accumulated history, so reach the orientation lesson through the UI rather
  // than a hard-coded /lessons/{id} route.
  await page.goto("/training/week/0");
  await page.locator('article[data-activity-type="lesson"]').filter({ hasText: "Welcome to Nexus: Your First Week" }).getByRole("link").click();
  const orientationLessonPath = new URL(page.url()).pathname;
  await expect(page.getByRole("heading", { name: "Welcome to Nexus", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Mark lesson complete", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Optional notes", exact: true })).toBeVisible();
  await page.goto("/quizzes/42");
  await expect(page.getByText("Question 1 of 4", { exact: true })).toBeVisible();
  await page.goto("/tickets");
  await expect(page.getByRole("heading", { name: "That page is not part of your learning path." })).toBeVisible();
  await page.goto("/labs/4");
  await expect(page.getByRole("heading", { name: "Hardware Component Identification", exact: true })).toBeVisible();
  await page.goto("/cli-labs/meet-cli-001");
  await expect(page.getByRole("heading", { name: "First Contact", exact: true })).toBeVisible();

  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/training");
  await page.getByRole("button", { name: "Toggle menu" }).click();
  await expect(page.getByRole("link", { name: "This Week", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: /Learning Path/i })).toHaveCount(0);
  await expect(page.getByRole("paragraph").filter({ hasText: /^Extra Practice$/ })).toBeVisible();
  await assertNoHorizontalOverflow(page);
  await page.goto("/training/week/0");
  await assertNoHorizontalOverflow(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Begin Your IT Training|Continue where you left off/ })).toBeVisible();
  await assertNoHorizontalOverflow(page);
  await page.goto("/progress");
  await expect(page.getByRole("heading", { name: "Progress", exact: true })).toBeVisible();
  await assertNoHorizontalOverflow(page);
  await page.goto(orientationLessonPath);
  await expect(page.getByRole("heading", { name: "Welcome to Nexus", exact: true })).toBeVisible();
  await assertNoHorizontalOverflow(page);
  await page.goto("/quizzes/42");
  await expect(page.getByText("Question 1 of 4", { exact: true })).toBeVisible();
  await assertNoHorizontalOverflow(page);
  await page.goto("/service-desk", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "My Service Desk" })).toBeVisible({ timeout: 15_000 });
  await assertNoHorizontalOverflow(page);

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await page.getByRole("button", { name: "Browser Training Student" }).click();
  await expect(page).toHaveURL(/\/login$/);

  expect(monitor.consoleErrors).toEqual([]);
  expect(monitor.failedRequests).toEqual([]);
  expect(monitor.httpErrors).toEqual([]);
});

test("admin can open Weekly Training under Learning Content", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await adminLogin(page);
  const monitor = monitorPage(page);
  await page.getByRole("button", { name: /Learning Content/ }).click();
  await page.getByRole("menuitem", { name: "Weekly Training" }).click();
  await expect(page.getByRole("heading", { name: "Weekly Training" })).toBeVisible();
  await expect(page.getByText("References valid")).toBeVisible();
  await expect(page.getByText("137 of 137", { exact: false })).toBeVisible();
  await expect(page.getByText(/Week \d+ · \d+ activities/)).toHaveCount(25);
  await expect(page.getByText(/Week 0 ·/).first()).toBeVisible();
  await page.getByText(/Week 0 ·/).first().click();
  await expect(page.getByLabel(/Quiz for week-0-video-/).first()).toBeVisible();
  await assertNoHorizontalOverflow(page);

  await page.reload();
  await expect(page.getByRole("heading", { name: "Weekly Training" })).toBeVisible();
  const adminRoutes = [
    ["/admin/modules", "Module Manager"],
    ["/admin/students", "Student Activity Overview"],
    ["/admin/labs", "Lab Templates"],
    ["/admin/capstones", "Capstone Templates"],
    ["/admin/ai-costs", "AI Cost Dashboard"],
  ];
  for (const [route, heading] of adminRoutes) {
    await page.goto(route);
    await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
  }
  await page.goto("/admin/review");
  await expect(page).toHaveURL(/\/admin\/service-desk-review$/);
  await expect(page.getByRole("heading", { name: "Service Desk Review" })).toBeVisible();
  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByRole("button", { name: "Toggle menu" }).click();
  await expect(page.getByRole("navigation").getByText("Learning Content", { exact: true })).toBeVisible();
  await assertNoHorizontalOverflow(page);

  await page.setViewportSize({ width: 1440, height: 1000 });
  // Let StrictMode's duplicate initial data requests settle before logout
  // revokes the shared admin session cookie. Otherwise a request can cross
  // the logout boundary and produce a harmless but noisy 403 in the console.
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Admin Sign Out" }).click();
  await expect(page).toHaveURL(/\/admin-login/);

  expect(monitor.consoleErrors).toEqual([]);
  expect(monitor.failedRequests).toEqual([]);
  expect(monitor.httpErrors).toEqual([]);
});

test("capstone navigation remains role gated", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill(process.env.NEXUS_E2E_QUALIFIED_USERNAME || "browser-qualified-student");
  await page.getByLabel("Password").fill(process.env.NEXUS_E2E_QUALIFIED_PASSWORD || "BrowserQualified!2026");
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page.getByRole("heading", { name: /Qualified Browser Student|Student Home/ })).toBeVisible();
  await page.getByRole("button", { name: /Extra Practice/ }).click();
  await expect(page.getByRole("menuitem", { name: "Capstones", exact: true })).toBeVisible();
  await page.getByRole("menuitem", { name: "Capstones", exact: true }).click();
  await expect(page).toHaveURL(/\/capstones$/);
  await expect(page.getByRole("heading", { name: /Capstone/i }).first()).toBeVisible();
});

test("required Nexus-authored quiz grades and reviews every answer", async ({ page }) => {
  await studentLogin(page);
  await page.goto("/quizzes/1");
  await expect(page.getByText(/Question 1 of 8/)).toBeVisible();

  for (let index = 1; index <= 8; index += 1) {
    const questionPanel = page.locator("section .panel").first();
    const questionText = await questionPanel.textContent();
    const correctOptions = questionText.includes("FIRST thing missing")
      ? ["The reported symptom"]
      : questionText.includes("USER-FACING resolution")
        ? ["Your profile was repaired and your files open normally."]
        : questionText.includes("without doing what")
          ? ["Repeating the same questions"]
          : questionText.includes("INTERNAL notes")
            ? ["Exact command output proving the fix", "Event ID and source", "What was ruled out and how"]
            : questionText.includes("grading anchor")
              ? ["verification"]
              : questionText.includes("MSPs care intensely")
                ? ["They support billing and auditability"]
                : questionText.includes("confirms the scope")
                  ? ["Can you reproduce it in another browser?"]
                  : ["It is unproven and unprofessional"];
    for (const option of correctOptions) {
      await questionPanel.getByText(option, { exact: true }).click();
    }
    await page.getByRole("button", { name: index === 8 ? "Submit Quiz" : "Next", exact: true }).click();
  }

  await expect(page.getByText("Passed", { exact: true })).toBeVisible();
  await expect(page.getByText("Answer Review", { exact: true })).toBeVisible();
  await expect(page.getByText("Why this is correct", { exact: true })).toHaveCount(8);
  await assertNoHorizontalOverflow(page);

  await page.goto("/quizzes/1/review");
  await expect(page.getByRole("heading", { name: "Answer Review" })).toBeVisible();
  // Ten selected correct options (the multi-select has three) plus the score summary label.
  await expect(page.getByText("Correct", { exact: true })).toHaveCount(11);
});

test("Week 0 unlock is student-scoped, persistent, and links back from Service Desk", async ({ page, browser }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 1440, height: 1000 });
  let monitor;
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  const username = `browser-flow-${suffix}`;
  const password = "BrowserFlow!2026";
  const studentIds = [];
  const secondUsername = `browser-fresh-${suffix}`;

  try {
    await adminLogin(page);
    const createResponse = await page.request.post(`${apiBaseUrl}/api/admin/students`, {
      headers: { Origin: browserBaseUrl, Referer: `${browserBaseUrl}/admin/students` },
      data: {
        name: "Disposable Browser Flow Student",
        email: `${username}@example.invalid`,
        username,
        password,
      },
    });
    const createBody = await createResponse.json();
    expect(createResponse.ok(), JSON.stringify(createBody)).toBeTruthy();
    studentIds.push(createBody.data.student_id);
    const secondCreateResponse = await page.request.post(`${apiBaseUrl}/api/admin/students`, {
      headers: { Origin: browserBaseUrl, Referer: `${browserBaseUrl}/admin/students` },
      data: {
        name: "Second Fresh Browser Student",
        email: `${secondUsername}@example.invalid`,
        username: secondUsername,
        password,
      },
    });
    const secondCreateBody = await secondCreateResponse.json();
    expect(secondCreateResponse.ok(), JSON.stringify(secondCreateBody)).toBeTruthy();
    studentIds.push(secondCreateBody.data.student_id);
    await page.getByRole("button", { name: "Admin Sign Out" }).click();

    await studentLogin(page, username, password);
    monitor = monitorPage(page);
    await expect(page.getByRole("heading", { name: "Disposable Browser Flow Student" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Begin Your IT Training" })).toBeVisible();
    await page.getByRole("link", { name: "Start Training" }).first().click();
    // Orientation's lesson ID is not stable across a fresh seed vs.
    // production's accumulated history — match any lesson ID and read the
    // real one back off the URL.
    await expect(page).toHaveURL(/\/lessons\/\d+$/);
    const orientationLessonId = new URL(page.url()).pathname.split("/").pop();
    const orientationLessonPath = new URL(page.url()).pathname;
    await expect(page.getByRole("heading", { name: "Welcome to Nexus", exact: true })).toBeVisible();
    await expect(page.getByText("Week 0 is a quick setup so you know how Nexus works.")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Two quick steps" })).toBeVisible();
    await expect(page.getByText("Week 0 guided practice")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Save practice response" })).toHaveCount(0);
    await expect(page.getByText(/sample screenshot/i)).toHaveCount(0);

    const weekOnePlan = await page.request.get(`${apiBaseUrl}/api/students/me/week-plan?week=1`);
    expect(weekOnePlan.ok()).toBeTruthy();
    const weekOneLessonPath = (await weekOnePlan.json()).data.next_action.route;

    monitor.pause();
    await page.goto(weekOneLessonPath);
    await expect(page.getByRole("heading", { name: "Week 1 locked" })).toBeVisible();
    await expect(page.getByText("Complete Week 0's required lesson and quiz first.")).toBeVisible();
    monitor.resume();
    await page.goto(orientationLessonPath);

    const orientationNote = page.getByPlaceholder("Optional: note where you will look when you are unsure what comes next.");
    const orientationSaved = page.waitForResponse((response) => response.url().endsWith(`/api/lessons/${orientationLessonId}/notes`) && response.request().method() === "PUT" && response.ok());
    await orientationNote.fill("I will open Home and follow the next My Training activity.");
    await orientationSaved;
    await expect(page.locator("p.opacity-100").getByText("Saved", { exact: true })).toBeVisible();

    await page.getByRole("button", { name: "Mark lesson complete", exact: true }).click();
    await expect(page.getByRole("button", { name: "Orientation complete", exact: true })).toBeVisible();
    await expect(page.getByText("Pass the Ticketing Systems Quiz to unlock Week 1.")).toBeVisible();

    monitor.pause();
    await page.goto(weekOneLessonPath);
    await expect(page.getByText("Complete Week 0's required quiz first.")).toBeVisible();
    monitor.resume();
    await page.goto(orientationLessonPath);
    await page.getByRole("link", { name: "Take quiz", exact: true }).click();
    await expect(page).toHaveURL(/\/quizzes\/42$/);
    await page.waitForLoadState("networkidle");

    for (let index = 1; index <= 4; index += 1) {
      await expect(page.getByText(`Question ${index} of 4`, { exact: true })).toBeVisible();
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
        const answer = questionPanel.getByText(option, { exact: true });
        await expect(answer).toBeVisible({ timeout: 5000 });
        await answer.click();
      }
      const action = index === 4 ? "Submit Quiz" : "Next";
      await page.getByRole("button", { name: action, exact: true }).click();
    }
    await expect(page.getByRole("heading", { name: "Ticketing Systems Quiz" })).toBeVisible();
    await expect(page.getByText("Passed", { exact: true })).toBeVisible();
    await expect(page.getByText("Answer Review", { exact: true })).toBeVisible();
    await expect(page.getByText("Why this is correct", { exact: true })).toHaveCount(4);
    await expect(page.getByRole("link", { name: "Continue Learning" })).toHaveAttribute("href", "/");
    await page.goto("/training/week/0");
    await expect(page.getByText("2 of 2 required activities complete").first()).toBeVisible();
    const weekHeaderText = await page.locator("main > header").innerText();
    expect(weekHeaderText).toContain("2 of 2 required complete");
    await expect(page.getByRole("heading", { name: "Week 0 Complete" })).toBeVisible();
    await page.getByText(/Extra practice \(/).click();
    await expect(page.locator('article[data-activity-type="video"]').filter({ hasText: "How to Pass Your A+" }).first().getByRole("button", { name: "Mark Watched" })).toBeVisible();

    await page.goto(orientationLessonPath);
    await expect(page.getByText("✓ Week 0 complete")).toBeVisible();
    await page.getByRole("link", { name: "Start Week 1" }).click();
    await expect(page).toHaveURL(new RegExp(`${weekOneLessonPath}$`));
    await expect(page.getByRole("heading", { name: "Anatomy of a Good Ticket" })).toBeVisible();
    await page.reload();
    await expect(page.getByRole("heading", { name: "Anatomy of a Good Ticket" })).toBeVisible();

    await page.goto("/training");
    const weekOne = page.locator('a[href="/training/week/1"]');
    await expect(weekOne).toBeVisible();
    await expect(weekOne).not.toContainText("Locked");
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Continue where you left off" })).toBeVisible();
    await expect(page.getByText(/Week 1 —/).first()).toBeVisible();

    monitor.pause();
    await page.getByRole("button", { name: "Disposable Browser Flow Student" }).click();
    await expect(page).toHaveURL(/\/login$/);
    await studentLogin(page, username, password);
    monitor.resume();
    await expect(page.getByRole("heading", { name: "Continue where you left off" })).toBeVisible();
    await expect(page.getByText(/Week 1 —/).first()).toBeVisible();
    await page.goto("/training/week/0");
    await expect(page.getByText("2 of 2 required activities complete").first()).toBeVisible();
    await assertNoHorizontalOverflow(page);

    await page.goto("/");
    await page.getByRole("link", { name: "Service Desk", exact: true }).click();
    await expect(page).toHaveURL(/\/service-desk\/?$/);
    await expect(page.getByRole("link", { name: "Back to Nexus" })).toBeVisible();
    // The link is server-rendered before Next hydration. Wait for the client
    // router so a deliberately slow CI runner cannot drop this navigation.
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: "Company Chat" }).click();
    await expect(page).toHaveURL(/\/service-desk\/tools\/company-chat$/, { timeout: 15_000 });
    await page.getByRole("link", { name: "Back to Nexus" }).click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("heading", { name: "Continue where you left off" })).toBeVisible();

    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/service-desk");
    await expect(page.getByRole("link", { name: "Back to Nexus" })).toBeVisible();
    await assertNoHorizontalOverflow(page);
    await page.getByRole("link", { name: "Back to Nexus" }).click();
    await expect(page.getByRole("heading", { name: "Continue where you left off" })).toBeVisible();
    await assertNoHorizontalOverflow(page);

    const secondContext = await browser.newContext({ baseURL: browserBaseUrl });
    const secondPage = await secondContext.newPage();
    await secondPage.setViewportSize({ width: 375, height: 812 });
    await studentLogin(secondPage, secondUsername, password);
    await secondPage.goto(weekOneLessonPath);
    await expect(secondPage.getByRole("heading", { name: "Week 1 locked" })).toBeVisible();
    await expect(secondPage.getByText("Complete Week 0's required lesson and quiz first.")).toBeVisible();
    await assertNoHorizontalOverflow(secondPage);
    await secondContext.close();
  } finally {
    if (studentIds.length) {
      const cleanupContext = await browser.newContext({ baseURL: browserBaseUrl });
      const cleanupPage = await cleanupContext.newPage();
      await adminLogin(cleanupPage);
      for (const studentId of studentIds) {
        const deleteResponse = await cleanupPage.request.delete(`${apiBaseUrl}/api/admin/students/${studentId}`, {
          headers: { Origin: browserBaseUrl, Referer: `${browserBaseUrl}/admin/students` },
        });
        expect(deleteResponse.ok()).toBeTruthy();
      }
      await cleanupContext.close();
    }
  }

  expect(monitor?.consoleErrors || []).toEqual([]);
  expect(monitor?.failedRequests || []).toEqual([]);
  expect(monitor?.httpErrors || []).toEqual([]);
});
