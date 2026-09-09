import { expect, test } from "@playwright/test";

const screenshotDir = process.env.WAVE4_SCREENSHOTS || "../docs/core-wave4/screenshots";

async function login(page, learner) {
  if (new URL(process.env.NEXUS_E2E_BASE_URL).hostname !== "127.0.0.1") throw new Error("Loopback fixture required");
  await page.goto("/login");
  await page.getByLabel("Username").fill(`wave4-learner-${learner}`);
  await page.getByLabel("Password").fill(process.env.WAVE4_PASSWORD);
  await page.getByRole("button", { name: /Login|Sign in/i }).click();
  await expect(page).not.toHaveURL(/login/);
}

async function capture(page, name, fullPage = false) {
  await page.screenshot({ path: `${screenshotDir}/${name}.png`, fullPage });
}

async function completeOrientation(page) {
  await page.goto("/");
  await page.getByRole("link", { name: "Continue lesson", exact: true }).click();
  await page.getByRole("button", { name: "Mark lesson complete", exact: true }).click();
  await page.getByRole("link", { name: "Take quiz", exact: true }).click();
  await expect(page.getByText("Assessment", { exact: true })).toBeVisible();
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
    for (const checked of await page.locator('input:checked').all()) await checked.click({ force: true });
    for (const text of desired) await page.locator("label").filter({ hasText: new RegExp(`${text}$`) }).click();
    if (index < 3) await page.getByRole("button", { name: "Next", exact: true }).click();
  }
}

test("practice teaches without credit, then assessment withholds a failed key and awards legitimate credit", async ({ page }) => {
  test.setTimeout(90_000);
  await login(page, 1);

  await page.goto("/quizzes/99");
  await expect(page.getByText("Practice Check", { exact: true })).toBeVisible();
  await expect(page.getByText(/does not affect module credit/)).toBeVisible();
  await capture(page, "practice-intro");
  await page.locator("label").filter({ hasText: /Requester name$/ }).click();
  await page.getByRole("button", { name: "Check answer" }).click();
  await expect(page.getByText("Not quite — learn from this")).toBeVisible();
  await expect(page.getByText(/Progress notes preserve/)).toBeVisible();
  await capture(page, "practice-wrong-answer-feedback");
  const practiceState = await page.request.get("http://127.0.0.1:8190/api/quizzes?student_id=1");
  const practiceRow = (await practiceState.json()).data.find((row) => row.id === 99);
  expect(practiceRow.status).toBe("not_started");
  expect(practiceRow.earned_pass).toBe(false);

  await completeOrientation(page);
  await expect(page.getByText(/Counts toward module completion/)).toBeVisible();
  await capture(page, "assessment-intro");
  await answerAssessment(page, false);
  await page.getByRole("button", { name: "Submit assessment" }).click();
  await expect(page.getByText("Not passed", { exact: true })).toBeVisible();
  await expect(page.getByText(/No module credit earned/)).toBeVisible();
  await expect(page.getByText(/Exact answers stay hidden/)).toBeVisible();
  await expect(page.getByText(/Correct answer/)).toHaveCount(0);
  await capture(page, "assessment-failed-result", true);
  await page.getByText("Review recommendations").scrollIntoViewIfNeeded();
  await capture(page, "review-recommendation", true);

  await page.getByRole("button", { name: "Retry assessment" }).click();
  await expect(page.getByText("Assessment", { exact: true })).toBeVisible();
  await capture(page, "assessment-retry");
  await page.locator("label").first().click();
  await expect(page.getByText(/Saving answers|Answers saved/)).toBeVisible();
  await page.reload();
  await expect(page.locator("input:checked")).toHaveCount(1);

  await answerAssessment(page, true);
  await page.getByRole("button", { name: "Submit assessment" }).click();
  await expect(page.getByText("Passed", { exact: true })).toBeVisible();
  await expect(page.getByText(/Module requirement completed/)).toBeVisible();
  await capture(page, "assessment-pass", true);
  await page.getByRole("link", { name: /Saved review of this attempt/ }).click();
  await expect(page.getByRole("navigation", { name: "Attempt history" })).toContainText("Attempt 1");
  await expect(page.getByRole("navigation", { name: "Attempt history" })).toContainText("Attempt 2");
  await capture(page, "historical-attempt-selector-review", true);
});

test("same-browser account drafts are separated and active assessment survives navigation", async ({ page }) => {
  await login(page, 2);
  await completeOrientation(page);
  let saveFailures = 1;
  await page.route("**/api/quizzes/*/attempts/*", async (route) => {
    if (route.request().method() === "PATCH" && saveFailures-- > 0) {
      await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "injected" }) });
    } else await route.continue();
  });
  await page.locator("label").first().click();
  await expect(page.getByText(/Couldn't save to the server/)).toBeVisible();
  await page.locator("label").nth(1).click();
  await expect(page.getByText("Answers saved", { exact: true })).toBeVisible();
  await expect.poll(() => page.evaluate(() => Object.keys(localStorage).filter((key) => key.startsWith("nexus:quiz-draft:")).join("|"))).toContain("nexus:quiz-draft:2:42:");
  await page.goBack();
  await page.goForward();
  await expect(page.locator("input:checked")).toHaveCount(1);
  await page.getByRole("button", { name: /Wave 4 Learner 2/ }).click();

  const secondPage = await page.context().newPage();
  await page.close();
  await login(secondPage, 3);
  await completeOrientation(secondPage);
  await expect(secondPage.locator("input:checked")).toHaveCount(0);
  const keys = await secondPage.evaluate(() => Object.keys(localStorage).filter((key) => key.startsWith("nexus:quiz-draft:")));
  expect(keys.some((key) => key.startsWith("nexus:quiz-draft:2:42:"))).toBe(true);
  expect(keys.some((key) => key.startsWith("nexus:quiz-draft:3:42:"))).toBe(false);
});

test("390px assessment has usable choices and action without horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, 4);
  await completeOrientation(page);
  await expect(page.getByText("Assessment", { exact: true })).toBeVisible();
  await expect(page.locator("input").first()).toBeAttached();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await capture(page, "mobile-390-quiz", true);
});
