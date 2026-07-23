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

test("student follows My Training on desktop and mobile", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await studentLogin(page);
  const monitor = monitorPage(page);

  await expect(page.getByRole("link", { name: "Home", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "My Training", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /Practice Library/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "Progress", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: /Learning Path/i })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: /Begin Your IT Training|Continue Your Training/ })).toBeVisible();
  await assertNoHorizontalOverflow(page);

  await page.getByRole("link", { name: "My Training", exact: true }).click();
  await expect(page).toHaveURL(/\/training$/);
  await expect(page.getByRole("heading", { name: "My Training", exact: true })).toBeVisible();
  await expect(page.getByText("Weekly Roadmap")).toBeVisible();
  await expect(page.getByText(/Week 0 — Welcome to Nexus/).first()).toBeVisible();
  await assertNoHorizontalOverflow(page);

  await page.goto("/training/week/0");
  await page.reload();
  await expect(page.getByRole("heading", { name: "Welcome to Nexus", exact: true })).toBeVisible();
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
  await page.getByRole("button", { name: /Practice Library/ }).click();
  for (const name of ["Support Tickets", "Guided Labs", "Networking Labs", "Command Library", "Terminal Practice"]) {
    await expect(page.getByRole("menuitem", { name, exact: true })).toBeVisible();
  }
  await expect(page.getByRole("menuitem", { name: "Capstones", exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "Progress", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Progress", exact: true })).toBeVisible();
  await expect(page.getByText("Course progress", { exact: true })).toBeVisible();
  await expect(page.getByText(/Average quiz score: .*Best quiz score:/)).toBeVisible();

  const studentRoutes = [
    ["/quizzes", "Quiz Library"],
    ["/tickets", "Available Tickets"],
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
  await page.goto("/lessons/1");
  await expect(page.getByRole("heading", { name: "CompTIA 6-Step Process", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "In this lesson, you'll learn", exact: true })).toBeVisible();
  await expect(page.getByRole("listitem").filter({ hasText: /^Can identify symptoms$/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Lesson notes", exact: true })).toBeVisible();
  await page.goto("/quizzes/42");
  await expect(page.locator("main")).toContainText("Question 1 of 4");
  await page.goto("/tickets/1");
  await expect(page.locator("main")).toContainText("DNS resolution failing");
  await page.goto("/labs/4");
  await expect(page.locator("main")).toContainText("Hardware Component Identification");
  await page.goto("/cli-labs/meet-cli-001");
  await expect(page.locator("main")).toContainText("First Contact");

  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/training");
  await page.getByRole("button", { name: "Toggle menu" }).click();
  await expect(page.getByRole("link", { name: "My Training", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: /Learning Path/i })).toHaveCount(0);
  await expect(page.getByRole("paragraph").filter({ hasText: /^Practice Library$/ })).toBeVisible();
  await assertNoHorizontalOverflow(page);
  await page.goto("/training/week/0");
  await assertNoHorizontalOverflow(page);

  await page.setViewportSize({ width: 1440, height: 1000 });
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
  await expect(page).toHaveURL(/\/admin\/ticket-review$/);
  await expect(page.getByRole("heading", { name: "Ticket Review Queue" })).toBeVisible();
  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByRole("button", { name: "Toggle menu" }).click();
  await expect(page.getByRole("navigation").getByText("Learning Content", { exact: true })).toBeVisible();
  await assertNoHorizontalOverflow(page);

  await page.setViewportSize({ width: 1440, height: 1000 });
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
  await page.getByRole("button", { name: /Practice Library/ }).click();
  await expect(page.getByRole("menuitem", { name: "Capstones", exact: true })).toBeVisible();
  await page.getByRole("menuitem", { name: "Capstones", exact: true }).click();
  await expect(page).toHaveURL(/\/capstones$/);
  await expect(page.getByRole("heading", { name: /Capstone/i }).first()).toBeVisible();
});

test("a disposable beginner completes Week 0 with a shared quiz and persistent progress", async ({ page, browser }) => {
  test.setTimeout(240_000);
  await page.setViewportSize({ width: 1440, height: 1000 });
  let monitor;
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  const username = `browser-flow-${suffix}`;
  const password = "BrowserFlow!2026";
  let studentId;

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
    studentId = createBody.data.student_id;
    await page.getByRole("button", { name: "Admin Sign Out" }).click();

    await studentLogin(page, username, password);
    monitor = monitorPage(page);
    await expect(page.getByRole("heading", { name: "Disposable Browser Flow Student" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Begin Your IT Training" })).toBeVisible();
    await page.getByRole("link", { name: "Start Training" }).first().click();
    await expect(page).toHaveURL(/\/lessons\/64$/);

    const orientationNote = page.getByPlaceholder("Write one sentence: Where will you look when you are unsure what comes next?");
    const orientationSaved = page.waitForResponse((response) => response.url().endsWith("/api/lessons/64/notes") && response.request().method() === "PUT" && response.ok());
    await orientationNote.fill("I will open Home and follow the next My Training activity.");
    await orientationSaved;
    await expect(page.locator("p.opacity-100").getByText("Saved", { exact: true })).toBeVisible();

    await page.goto("/training/week/0");
    const sharedQuizLinks = page.getByRole("link", { name: "Take Quiz" });
    await expect(sharedQuizLinks).toHaveCount(3);
    for (const link of await sharedQuizLinks.all()) {
      await expect(link).toHaveAttribute("href", "/quizzes/42");
    }
    const ticketingVideo = page.locator('article[data-activity-type="video"]').filter({ hasText: "Ticketing Systems" }).first();
    await expect(ticketingVideo.getByRole("button", { name: "Mark Watched" })).toBeVisible();
    await ticketingVideo.getByRole("link", { name: "Take Quiz" }).click();
    await expect(page).toHaveURL(/\/quizzes\/42$/);

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
        await questionPanel.getByText(option, { exact: true }).click();
      }
      const action = index === 4 ? "Submit Quiz" : "Next";
      await page.getByRole("button", { name: action, exact: true }).click();
    }
    await expect(page.getByRole("heading", { name: "Ticketing Systems Quiz" })).toBeVisible();
    await expect(page.getByText("Passed", { exact: true })).toBeVisible();
    await expect(page.getByText("Answer Review", { exact: true })).toBeVisible();
    await page.getByRole("link", { name: "Return to This Week" }).click();
    await expect(page).toHaveURL(/\/training\/week\/0$/);

    const reviewLinks = page.getByRole("link", { name: /Review Quiz · \d+%/ });
    await expect(reviewLinks).toHaveCount(3);
    for (const link of await reviewLinks.all()) {
      await expect(link).toHaveAttribute("href", "/quizzes/42/review");
    }
    await expect(page.locator('article[data-activity-type="video"]').filter({ hasText: "Ticketing Systems" }).first().getByRole("button", { name: "Mark Watched" })).toBeVisible();

    await page.goto("/lessons/1");
    const methodologyNote = page.getByPlaceholder("Your notes for this lesson...");
    const methodologySaved = page.waitForResponse((response) => response.url().endsWith("/api/lessons/1/notes") && response.request().method() === "PUT" && response.ok());
    await methodologyNote.fill("I will identify the problem before testing a theory and document the result.");
    await methodologySaved;
    await expect(page.locator("p.opacity-100").getByText("Saved", { exact: true })).toBeVisible();

    await page.goto("/training/week/0");
    for (const title of ["Ticketing Systems", "Document Types"]) {
      const row = page.locator('article[data-activity-type="video"]').filter({ hasText: title }).first();
      await row.getByRole("button", { name: "Mark Watched" }).click();
      await expect(page.locator('article[data-activity-type="video"]').filter({ hasText: title }).first().getByRole("link", { name: "Watch Again" })).toBeVisible();
    }
    const weekHeaderText = await page.locator("main > header").innerText();
    expect(weekHeaderText).toContain("5 of 5 required complete");
    await expect(page.getByRole("heading", { name: "Week 0 Complete" })).toBeVisible();
    await expect(page.locator('article[data-activity-type="video"]').filter({ hasText: "How to Pass Your A+" }).first().getByRole("button", { name: "Mark Watched" })).toBeVisible();

    await page.goto("/training");
    const weekOne = page.locator('a[href="/training/week/1"]');
    await expect(weekOne).toBeVisible();
    await expect(weekOne).not.toContainText("Locked");
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Continue Your Training" })).toBeVisible();
    await expect(page.getByText(/Week 1 —/).first()).toBeVisible();

    monitor.pause();
    await page.getByRole("button", { name: "Disposable Browser Flow Student" }).click();
    await expect(page).toHaveURL(/\/login$/);
    await studentLogin(page, username, password);
    monitor.resume();
    await expect(page.getByRole("heading", { name: "Continue Your Training" })).toBeVisible();
    await expect(page.getByText(/Week 1 —/).first()).toBeVisible();
    await page.goto("/training/week/0");
    await expect(page.getByText("5 of 5 required activities complete").first()).toBeVisible();
    await assertNoHorizontalOverflow(page);

    await page.setViewportSize({ width: 375, height: 812 });
    await page.reload();
    await assertNoHorizontalOverflow(page);
    await expect(page.getByRole("heading", { name: "Week 0 Complete" })).toBeVisible();
  } finally {
    if (studentId) {
      const cleanupContext = await browser.newContext({ baseURL: browserBaseUrl });
      const cleanupPage = await cleanupContext.newPage();
      await adminLogin(cleanupPage);
      const deleteResponse = await cleanupPage.request.delete(`${apiBaseUrl}/api/admin/students/${studentId}`, {
        headers: { Origin: browserBaseUrl, Referer: `${browserBaseUrl}/admin/students` },
      });
      expect(deleteResponse.ok()).toBeTruthy();
      await cleanupContext.close();
    }
  }

  expect(monitor?.consoleErrors || []).toEqual([]);
  expect(monitor?.failedRequests || []).toEqual([]);
  expect(monitor?.httpErrors || []).toEqual([]);
});
