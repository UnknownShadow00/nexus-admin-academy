import { expect, test } from "@playwright/test";

const studentUsername = process.env.NEXUS_E2E_STUDENT_USERNAME || "browser-training-student";
const studentPassword = process.env.NEXUS_E2E_STUDENT_PASSWORD || "BrowserTraining!2026";
const adminUsername = process.env.NEXUS_E2E_ADMIN_USERNAME || "browser-admin";
const adminPassword = process.env.NEXUS_E2E_ADMIN_PASSWORD || "BrowserAdmin!2026";
const apiBaseUrl = process.env.NEXUS_E2E_API_URL || "http://127.0.0.1:8011";
const browserBaseUrl = process.env.NEXUS_E2E_BASE_URL || "http://127.0.0.1:5173";

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

// Creates a disposable student and walks Week 0 (orientation lesson + Ticketing
// Systems quiz) via the real UI, exactly as a beginner would, so tests land on
// an unlocked Week 1 instead of the Week 0 lock screen. Mirrors the flow in
// my-training.spec.js's "Week 0 unlock" test.
async function createStudentAtWeekOne(page) {
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  const username = `browser-w1-${suffix}`;
  const password = "BrowserWeek1!2026";

  await adminLogin(page);
  const createResponse = await page.request.post(`${apiBaseUrl}/api/admin/students`, {
    headers: { Origin: browserBaseUrl, Referer: `${browserBaseUrl}/admin/students` },
    data: { name: "Disposable Week 1 Student", email: `${username}@example.invalid`, username, password },
  });
  const createBody = await createResponse.json();
  expect(createResponse.ok(), JSON.stringify(createBody)).toBeTruthy();
  const studentId = createBody.data.student_id;
  await page.getByRole("button", { name: "Admin Sign Out" }).click();

  await studentLogin(page, username, password);
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

  return { username, password, studentId, orientationLessonPath };
}

async function deleteStudent(page, studentId) {
  await adminLogin(page);
  const deleteResponse = await page.request.delete(`${apiBaseUrl}/api/admin/students/${studentId}`, {
    headers: { Origin: browserBaseUrl, Referer: `${browserBaseUrl}/admin/students` },
  });
  expect(deleteResponse.ok()).toBeTruthy();
}

test("Week 1 journey: labels, CLI CTA, Practice/Apply split, and formative ticket exercise", async ({ page }) => {
  test.setTimeout(120_000);
  let studentId;
  try {
    const created = await createStudentAtWeekOne(page);
    studentId = created.studentId;

    await page.goto("/training/week/1");
    await expect(page.getByRole("heading", { name: "IT Support and Ticket Basics" })).toBeVisible();

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

    // Phase 6/8: Practice and Apply are distinct sections; no required Guided Lab in Week 1
    await expect(page.getByRole("heading", { name: "3. Practice" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "4. Apply" })).toBeVisible();
    await expect(page.locator('article[data-activity-type="guided_lab"]')).toHaveCount(0);
    await expect(page.locator('article[data-activity-type="networking_lab"]')).toHaveCount(1);
    const practiceSection = page.locator("section").filter({ has: page.getByRole("heading", { name: "3. Practice" }) });
    await expect(practiceSection.locator('article[data-activity-type="networking_lab"]')).toBeVisible();
    const applySection = page.locator("section").filter({ has: page.getByRole("heading", { name: "4. Apply" }) });
    await expect(applySection.locator('article[data-activity-type="service_desk_scenario"]')).toBeVisible();

    // Phase 3: "Meet the Command Line" no longer claims a dead requirement, CTA works
    await page.locator("details > summary").click();
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
    await page.locator("details > summary").click();
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
  await studentLogin(page);
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
  const submit = page.getByRole("button", { name: "Submit Answers" });
  await expect(submit).toBeEnabled();
});

test("Weeks 3-6 provide deterministic practice and Week 3 uses the real terminal", async ({ page }) => {
  await studentLogin(page);

  await page.goto("/labs/3");
  await expect(page.getByRole("heading", { name: "Windows Command-Line Diagnostics", exact: true })).toBeVisible();
  await expect(page.getByText("Work and explain", { exact: false })).toHaveCount(0);
  await expect(page.getByText("Use the practice terminal first", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /Try hostname/ }).click();
  await page.locator(".xterm-helper-textarea").press("Enter");
  await expect(page.getByRole("button", { name: /hostname/ })).toContainText("✓");
  await expect(page.locator("fieldset").first()).toBeVisible();

  await page.goto("/labs/6");
  await expect(page.getByRole("heading", { name: "Prioritize the Queue", exact: true })).toBeVisible();
  await expect(page.getByText("Work and explain", { exact: false })).toHaveCount(0);
  await expect(page.locator("fieldset").first()).toBeVisible();

  await page.goto("/labs/7");
  await expect(page.getByRole("heading", { name: "Isolate the Windows Failure", exact: true })).toBeVisible();
  await expect(page.locator("fieldset")).toHaveCount(3);

  await page.goto("/labs/8");
  await expect(page.getByRole("heading", { name: "Make the Safe Access Decision", exact: true })).toBeVisible();
  await expect(page.locator("fieldset")).toHaveCount(3);
});

test("no mobile horizontal overflow on rebuilt lab pages", async ({ page }) => {
  await studentLogin(page);
  await page.setViewportSize({ width: 375, height: 812 });
  for (const labId of [4, 3, 6]) {
    await page.goto(`/labs/${labId}`);
    await expect(page.locator("fieldset").first()).toBeVisible();
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
