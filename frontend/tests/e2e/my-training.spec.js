import { expect, test } from "@playwright/test";

const studentUsername = process.env.NEXUS_E2E_STUDENT_USERNAME || "browser-training-student";
const studentPassword = process.env.NEXUS_E2E_STUDENT_PASSWORD || "BrowserTraining!2026";
const adminUsername = process.env.NEXUS_E2E_ADMIN_USERNAME || "browser-admin";
const adminPassword = process.env.NEXUS_E2E_ADMIN_PASSWORD || "BrowserAdmin!2026";

function monitorPage(page) {
  const consoleErrors = [];
  const failedRequests = [];
  const httpErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("requestfailed", (request) => {
    const reason = request.failure()?.errorText || "unknown error";
    // SPA navigation intentionally cancels in-flight reads from the page being
    // left. Record real transport failures, not Chromium's navigation aborts.
    if (!reason.includes("ERR_ABORTED")) failedRequests.push(`${request.method()} ${request.url()}: ${reason}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 400) httpErrors.push(`${response.status()} ${response.url()}`);
  });
  return { consoleErrors, failedRequests, httpErrors };
}

async function studentLogin(page) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(studentUsername);
  await page.getByLabel("Password").fill(studentPassword);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page.getByRole("heading", { name: /Browser Training Student|Student Home/ })).toBeVisible();
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

  await page.getByRole("link", { name: "Quiz Library" }).click();
  await expect(page.getByRole("heading", { name: "Quiz Library" })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { name: "All Course Content" })).toBeVisible();
  await page.goForward();
  await expect(page.getByRole("heading", { name: "Quiz Library" })).toBeVisible();

  await page.goto("/training");
  await page.getByRole("button", { name: /Practice Library/ }).click();
  for (const name of ["Support Tickets", "Guided Labs", "Networking Labs", "Command Library", "Terminal Practice"]) {
    await expect(page.getByRole("menuitem", { name, exact: true })).toBeVisible();
  }
  await expect(page.getByRole("menuitem", { name: "Capstones", exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "Progress", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Progress", exact: true })).toBeVisible();

  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/training");
  await page.getByRole("button", { name: "Toggle menu" }).click();
  await expect(page.getByRole("link", { name: "My Training", exact: true })).toBeVisible();
  await expect(page.getByRole("paragraph").filter({ hasText: /^Practice Library$/ })).toBeVisible();
  await assertNoHorizontalOverflow(page);
  await page.goto("/training/week/0");
  await assertNoHorizontalOverflow(page);

  expect(monitor.consoleErrors).toEqual([]);
  expect(monitor.failedRequests).toEqual([]);
  expect(monitor.httpErrors).toEqual([]);
});

test("admin can open Weekly Training under Learning Content", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/admin-login");
  await page.getByLabel("Username").fill(adminUsername);
  await page.getByLabel("Password").fill(adminPassword);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/admin$/);
  const monitor = monitorPage(page);
  await page.getByRole("button", { name: /Learning Content/ }).click();
  await page.getByRole("menuitem", { name: "Weekly Training" }).click();
  await expect(page.getByRole("heading", { name: "Weekly Training" })).toBeVisible();
  await expect(page.getByText("References valid")).toBeVisible();
  await expect(page.getByText(/Week 0 ·/).first()).toBeVisible();
  await assertNoHorizontalOverflow(page);

  await page.reload();
  await expect(page.getByRole("heading", { name: "Weekly Training" })).toBeVisible();
  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByRole("button", { name: "Toggle menu" }).click();
  await expect(page.getByRole("navigation").getByText("Learning Content", { exact: true })).toBeVisible();
  await assertNoHorizontalOverflow(page);

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
