import { expect, test } from "@playwright/test";

const screenshotDir = process.env.WAVE5_SCREENSHOTS || "../docs/core-wave5/screenshots";

async function login(page, learner) {
  if (new URL(process.env.NEXUS_E2E_BASE_URL).hostname !== "127.0.0.1") throw new Error("Loopback fixture required");
  await page.context().clearCookies();
  await page.goto("/login");
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.getByLabel("Username").fill(`wave5-learner-${learner}`);
  await page.getByLabel("Password").fill(process.env.WAVE5_PASSWORD);
  await page.getByRole("button", { name: /Login|Sign in/i }).click();
  await expect(page).not.toHaveURL(/login/);
}

async function capture(page, name, fullPage = true) {
  await page.screenshot({ path: `${screenshotDir}/${name}.png`, fullPage });
}

async function completeOrientationLesson(page) {
  await page.goto("/");
  await page.getByRole("link", { name: "Continue lesson", exact: true }).click();
  await page.getByRole("button", { name: "Mark lesson complete", exact: true }).click();
}

async function finishPractice(page) {
  await page.goto("/quizzes/99");
  await page.locator("label").filter({ hasText: /Progress notes$/ }).click();
  await page.getByRole("button", { name: "Check answer" }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.locator("label").filter({ hasText: /Device information$/ }).click();
  await page.getByRole("button", { name: "Check answer" }).click();
  await page.getByRole("button", { name: "Finish practice" }).click();
  await expect(page.getByText("Practice complete", { exact: true })).toBeVisible();
}

async function answerAssessment(page, correct) {
  const correctChoices = [
    [/initial data collection phase/, ["User information", "Device information", "Problem description"]],
    [/recurring problems/, ["Category"]],
    [/memory failure/, ["Escalation level"]],
    [/network printer/, ["Progress notes"]],
  ];
  const wrongChoices = [
    [/initial data collection phase/, ["Expected resolution date"]],
    [/recurring problems/, ["Issue description"]],
    [/memory failure/, ["Issue description"]],
    [/network printer/, ["Issue description"]],
  ];
  const choices = correct ? correctChoices : wrongChoices;
  for (let index = 0; index < 4; index += 1) {
    const heading = await page.locator("p").filter({ hasText: /^\d+\./ }).textContent();
    const desired = choices.find(([pattern]) => pattern.test(heading))[1];
    for (const checked of await page.locator("input:checked").all()) await checked.click({ force: true });
    for (const text of desired) await page.locator("label").filter({ hasText: new RegExp(`${text}$`) }).click();
    if (index < 3) await page.getByRole("button", { name: "Next", exact: true }).click();
  }
  await page.getByRole("button", { name: "Submit assessment" }).click();
}

test("fresh learner sees truthful progress through lesson, practice, fail, and pass", async ({ page }) => {
  test.setTimeout(120_000);
  await login(page, 1);
  await page.goto("/progress");
  await expect(page.getByText("You’re just getting started")).toBeVisible();
  await expect(page.getByText("Review will appear after you complete some learning.")).toBeVisible();
  await expect(page.getByText(/mastery or job readiness/)).toBeVisible();
  await expect(page.getByText(/All caught up/)).toHaveCount(0);
  await capture(page, "fresh-progress");

  await completeOrientationLesson(page);
  await page.goto("/progress");
  await expect(page.getByText("Lessons", { exact: true }).locator("..")).toContainText("1 / 1 complete");
  await expect(page.getByText("Assessment", { exact: true }).locator("..")).toContainText("0 / 1 passed");
  await capture(page, "partial-progress");

  await finishPractice(page);
  await page.goto("/progress");
  await expect(page.getByText(/Practice completed: 1/)).toBeVisible();
  await expect(page.getByText("Assessment", { exact: true }).locator("..")).toContainText("0 / 1 passed");

  await page.goto("/quizzes/42");
  await answerAssessment(page, false);
  await expect(page.getByText("Not passed", { exact: true })).toBeVisible();
  await page.goto("/progress");
  await expect(page.getByText("Passed: No")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Support ticket workflow" }).first()).toBeVisible();
  await capture(page, "assessment-failed");
  await capture(page, "actionable-review-recommendation");

  await page.goto("/quizzes/42");
  await answerAssessment(page, true);
  await expect(page.getByText("Passed", { exact: true })).toBeVisible();
  await page.goto("/progress");
  await expect(page.getByText("Passed: Yes")).toBeVisible();
  await expect(page.getByText("Required assessments passed", { exact: true }).locator("..")).toContainText("1 / 2");
  await expect(page.getByText(/Latest:/).locator("..")).toContainText("100%");
  await expect(page.getByText(/Best:/).locator("..")).toContainText("100%");
  await capture(page, "assessment-passed");
});

test("seeded evidence states remain distinct and review is useful only when due", async ({ page }) => {
  await login(page, 2);
  await page.goto("/progress");
  await expect(page.getByText("No review is due right now.")).toBeVisible();
  await capture(page, "no-review-due-state");

  await login(page, 3);
  await page.goto("/progress");
  await expect(page.getByText("Passed: No")).toBeVisible();
  await expect(page.getByRole("link", { name: "Review worked example" })).toBeVisible();
  await page.goto("/");
  await expect(page.getByText("Review 1 concept")).toBeVisible();
  await capture(page, "today-review-due");

  await login(page, 4);
  await page.goto("/progress");
  await expect(page.getByText("Passed: Yes")).toBeVisible();
  await expect(page.getByText(/Latest:/).locator("..")).toContainText("100%");
  await expect(page.getByText(/Best:/).locator("..")).toContainText("100%");

  await login(page, 5);
  await page.goto("/progress");
  await expect(page.getByText(/Practice completed: 1/)).toBeVisible();
  await expect(page.getByText("Required assessments passed", { exact: true }).locator("..")).toContainText("0 / 2");

  await login(page, 6);
  await page.goto("/progress");
  await expect(page.getByText("Guided practice", { exact: true }).locator("..")).toContainText("1 / 1");
  await expect(page.getByText("Independent demonstrations", { exact: true }).locator("..")).toContainText("0 / 0");
  await expect(page.getByText("Service Desk tickets passed", { exact: true }).locator("..")).toContainText("1");
  await expect(page.getByText("Passed: Yes")).toBeVisible();
  await capture(page, "knowledge-vs-practical-evidence");
});

test("review failure is not success and 390px Progress has no overflow", async ({ page }) => {
  await page.route("**/api/flashcards/due", (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "injected" }) }));
  await login(page, 2);
  await page.goto("/progress");
  await expect(page.getByRole("alert")).toContainText("We couldn’t load your review items.");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(page.getByText(/All caught up/)).toHaveCount(0);
  await capture(page, "review-error-state");

  await page.unroute("**/api/flashcards/due");
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, 6);
  await page.goto("/progress");
  await expect(page.getByRole("heading", { name: "Progress", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await capture(page, "mobile-progress");
});
