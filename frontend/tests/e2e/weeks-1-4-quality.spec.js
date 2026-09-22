import { expect, test } from "@playwright/test";

const studentUsername = process.env.NEXUS_E2E_STUDENT_USERNAME || "browser-training-student";
const studentPassword = process.env.NEXUS_E2E_STUDENT_PASSWORD || "BrowserTraining!2026";
const adminUsername = process.env.NEXUS_E2E_ADMIN_USERNAME || "browser-admin";
const adminPassword = process.env.NEXUS_E2E_ADMIN_PASSWORD || "BrowserAdmin!2026";
const apiBaseUrl = process.env.NEXUS_E2E_API_URL || "http://127.0.0.1:8011";
const browserBaseUrl = process.env.NEXUS_E2E_BASE_URL || "http://127.0.0.1:5173";
const weeks34Username = process.env.NEXUS_E2E_W34_USERNAME || "browser-weeks-3-4-student";
const weeks34Password = process.env.NEXUS_E2E_W34_PASSWORD || "BrowserWeeks34!2026";

async function studentLogin(page, username = studentUsername, password = studentPassword, replacementPassword = null) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
  if (replacementPassword) {
    await expect(page).toHaveURL(/\/change-password$/);
    await page.getByLabel("New password", { exact: true }).fill(replacementPassword);
    await page.getByLabel("Confirm new password", { exact: true }).fill(replacementPassword);
    await page.getByRole("button", { name: "Change password" }).click();
  }
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

// Creates a disposable student and walks Week 0 (orientation lesson + Ticketing
// Systems quiz) via the real UI, exactly as a beginner would, so tests land on
// an unlocked Week 1 instead of the Week 0 lock screen. Mirrors the flow in
// my-training.spec.js's "Week 0 unlock" test.
async function createStudentAtWeekOne(page) {
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  const username = `browser-w1-${suffix}`;
  const password = "BrowserWeek1!2026";
  const permanentPassword = "BrowserWeek1Permanent!2026";

  await adminLogin(page);
  const createResponse = await page.request.post(`${apiBaseUrl}/api/admin/students`, {
    headers: { Origin: browserBaseUrl, Referer: `${browserBaseUrl}/admin/students` },
    data: { name: "Disposable Week 1 Student", email: `${username}@example.invalid`, username, password },
  });
  const createBody = await createResponse.json();
  expect(createResponse.ok(), JSON.stringify(createBody)).toBeTruthy();
  const studentId = createBody.data.student_id;
  await page.getByRole("button", { name: "Admin Sign Out" }).click();

  await studentLogin(page, username, password, permanentPassword);
  await page.getByRole("link", { name: "Start Training" }).first().click();
  await expect(page).toHaveURL(/\/lessons\/\d+$/);
  const orientationLessonPath = new URL(page.url()).pathname;
  await expect(page.getByRole("heading", { name: "Welcome to Nexus", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Mark lesson complete", exact: true }).click();
  await expect(page.getByRole("button", { name: "Orientation complete", exact: true })).toBeVisible();
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
    await page.getByRole("button", { name: index === 4 ? "Submit Quiz" : "Next", exact: true }).click();
  }
  await expect(page.getByText("Passed", { exact: true })).toBeVisible();

  return { username, password: permanentPassword, studentId, orientationLessonPath };
}

async function deleteStudent(page, studentId) {
  await adminLogin(page);
  const deleteResponse = await page.request.delete(`${apiBaseUrl}/api/admin/students/${studentId}`, {
    headers: { Origin: browserBaseUrl, Referer: `${browserBaseUrl}/admin/students` },
  });
  expect(deleteResponse.ok()).toBeTruthy();
}

test("Support Workflow Essentials: learning roles, CLI CTA, and formative ticket exercise", async ({ page }) => {
  test.setTimeout(120_000);
  let studentId;
  try {
    const created = await createStudentAtWeekOne(page);
    studentId = created.studentId;

    await page.goto("/training/week/1");
    await expect(page.getByRole("heading", { name: "Support Workflow Essentials" })).toBeVisible();

    // Phase 2: video importance labels + legend
    await expect(page.getByText("Video importance:")).toBeVisible();
    const legend = page.getByText("Video importance:").locator("..");
    await expect(legend.getByText("Job Critical", { exact: true })).toBeVisible();
    await expect(legend.getByText("Know It", { exact: true })).toBeVisible();
    await expect(legend.getByText("Awareness", { exact: true })).toBeVisible();
    const videoCards = page.locator('article[data-activity-type="video"]');
    await expect(videoCards.first()).toBeVisible();
    const cardCount = await videoCards.count();
    let badgedCount = 0;
    for (let index = 0; index < cardCount; index += 1) {
      const text = await videoCards.nth(index).innerText();
      if (/Job Critical|Know It|Awareness/.test(text)) badgedCount += 1;
    }
    expect(badgedCount).toBeGreaterThan(0);
    await assertNoHorizontalOverflow(page);

    // Practice and Troubleshoot are distinct roles; this module has no required Guided Lab.
    await expect(page.getByRole("heading", { name: "3. Practice" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "4. Troubleshoot" })).toBeVisible();
    await expect(page.locator('article[data-activity-type="guided_lab"]')).toHaveCount(0);
    await expect(page.locator('article[data-activity-type="networking_lab"]')).toHaveCount(1);
    const practiceSection = page.locator("section").filter({ has: page.getByRole("heading", { name: "3. Practice" }) });
    await expect(practiceSection.locator('article[data-activity-type="networking_lab"]')).toBeVisible();
    const applySection = page.locator("section").filter({ has: page.getByRole("heading", { name: "4. Troubleshoot" }) });
    await expect(applySection.locator('article[data-activity-type="service_desk_scenario"]')).toBeVisible();

    // The required CLI introduction appears before the required CLI practice.
    const requiredLessons = page.locator('article[data-activity-type="lesson"]');
    await expect(requiredLessons).toHaveCount(2);
    await expect(requiredLessons.nth(0)).toContainText("Anatomy of a Good Ticket");
    await expect(requiredLessons.nth(1)).toContainText("Meet the Command Line");
    await page.locator('article[data-activity-type="lesson"]').filter({ hasText: "Meet the Command Line" }).getByRole("link").click();
    await expect(page.getByRole("heading", { name: "Meet the Command Line", exact: true })).toBeVisible();
    await expect(page.getByText(/complete CLI labs 1-9/i)).toHaveCount(0);
    const cta = page.getByRole("link", { name: "Start CLI Practice" });
    await expect(cta).toBeVisible();
    const cliPracticeRoute = await cta.getAttribute("href");
    expect(cliPracticeRoute).toBe("/cli-labs/meet-cli-001");
    await page.goto(cliPracticeRoute);
    await expect(page).toHaveURL(/\/cli-labs\/meet-cli-001$/);
    await expect(page.getByRole("heading", { name: "First Contact", exact: true })).toBeVisible();

    // Phase 3: "Anatomy of a Good Ticket" has a real formative exercise
    await page.goto("/training/week/1");
    await expect(page.locator('article[data-activity-type="lesson"]').filter({ hasText: "Anatomy of a Good Ticket" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Rewrite this bad ticket note" })).toBeVisible();
    await page.getByRole("button", { name: "Check my note" }).click();
    await expect(page.getByText("Not filled in yet.").first()).toBeVisible();
    await assertNoHorizontalOverflow(page);

    // Mobile pass on the same unlocked account
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/training/week/1");
    await expect(page.getByText("Video importance:")).toBeVisible();
    await assertNoHorizontalOverflow(page);
  } finally {
    if (studentId) await deleteStudent(page, studentId);
  }
});

test("Hardware Component Identification is a real structured exercise, not a textbox+upload shell", async ({ page }) => {
  await studentLogin(page, weeks34Username, weeks34Password);
  await page.goto("/labs/4");
  await expect(page.getByRole("heading", { name: "Hardware Component Identification", exact: true })).toBeVisible();
  await expect(page.getByText("Evidence Upload", { exact: false })).toHaveCount(0);
  await expect(page.getByText("Work and explain", { exact: false })).toHaveCount(0);

  const questions = page.locator("fieldset");
  await expect(questions.first()).toBeVisible();
  const questionCount = await questions.count();
  expect(questionCount).toBeGreaterThanOrEqual(5);
  for (const fieldset of await questions.all()) {
    await fieldset.locator('input[type="radio"], input[type="checkbox"]').first().click();
  }
  // Submission grading itself (server computes correctness from stored
  // answer keys) is covered by the backend structured-lab test suite; here
  // we only need to confirm this is a real interactive exercise, not a shell.
});

test("Weeks 3-4 follow Learn, Check, Practice, Troubleshoot with deterministic practice", async ({ page }) => {
  await studentLogin(page, weeks34Username, weeks34Password);

  await page.goto("/training/module/module.windows.fundamentals");
  await expect(page.getByRole("heading", { name: "Windows Fundamentals & Diagnostics", exact: true })).toBeVisible();
  for (const heading of ["1. Learn", "2. Check", "3. Practice", "4. Troubleshoot"]) {
    await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
  }
  await expect(page.locator('article[data-activity-type="guided_lab"]')).toContainText("Windows Command-Line Diagnostics");
  await expect(page.locator('article[data-activity-type="service_desk_scenario"]')).toContainText("My Desktop and Documents have disappeared");

  await page.goto("/labs/3");
  await expect(page.getByRole("heading", { name: "Windows Command-Line Diagnostics", exact: true })).toBeVisible();
  await expect(page.getByText("Work and explain", { exact: false })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Use the practice terminal first", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /Try hostname/ })).toBeVisible();

  await page.goto("/training/module/module.windows.queue_operations");
  await expect(page.getByRole("heading", { name: "Queue & Endpoint Operations", exact: true })).toBeVisible();
  await expect(page.locator('article[data-activity-type="guided_lab"]')).toHaveCount(2);
  await page.goto("/labs/6");
  await expect(page.getByRole("heading", { name: "Prioritize the Queue", exact: true })).toBeVisible();
  await expect(page.getByText("Work and explain", { exact: false })).toHaveCount(0);
  await expect(page.locator("fieldset").first()).toBeVisible();

  await page.goto("/training/module/module.windows.queue_operations");
  await page.locator('article[data-activity-type="guided_lab"]')
    .filter({ hasText: "Work the Queue: Three Tickets" })
    .getByRole("link", { name: "Review", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: "Work the Queue: Three Tickets", exact: true })).toBeVisible();
  await expect(page.locator("fieldset")).toHaveCount(3);
});

test("Weeks 3-4 key student screens do not overflow at mobile width", async ({ page }) => {
  await studentLogin(page, weeks34Username, weeks34Password);
  await page.setViewportSize({ width: 375, height: 812 });
  for (const route of ["/", "/training/module/module.windows.fundamentals", "/quizzes/4", "/labs/3", "/service-desk/tickets/INC2501", "/progress"]) {
    await page.goto(route);
    await expect(page.locator("main")).toBeVisible();
    await assertNoHorizontalOverflow(page);
  }
});

test("admin Curriculum Structure reflects the early-module realignment", async ({ page }) => {
  await adminLogin(page);
  await page.getByRole("button", { name: /Learning Content/ }).click();
  await page.getByRole("menuitem", { name: "Curriculum Structure" }).click();
  await expect(page.getByRole("heading", { name: "Curriculum Structure" })).toBeVisible();
  await expect(page.getByText("References valid")).toBeVisible();
});
