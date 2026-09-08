import { expect, test } from "@playwright/test";
test.describe.configure({ mode: "serial" });
async function login(page, admin = false) {
  if (new URL(process.env.NEXUS_E2E_BASE_URL).hostname !== "127.0.0.1")
    throw new Error("Disposable loopback fixture required");
  await page.goto(admin ? "/admin-login" : "/login");
  await page
    .getByLabel("Username")
    .fill(admin ? "wave1-admin" : "wave1-learner");
  await page.getByLabel("Password").fill(process.env.WAVE1_PASSWORD);
  await page.getByRole("button", { name: /Login|Sign in/i }).click();
  await expect(page).not.toHaveURL(/login/);
}
async function attempt(page, correct, total = 4, quizId = 1) {
  await page.goto(`/quizzes/${quizId}`);
  for (let i = 0; i < total; i++) {
    await expect(
      page.getByText(`Question ${i + 1} of ${total}`, { exact: true }),
    ).toBeVisible();
    await page
      .locator("label")
      .filter({ hasText: i < correct ? /Correct$/ : /Wrong$/ })
      .click();
    await expect(
      page.getByRole("radio", { name: i < correct ? /Correct$/ : /Wrong$/ }),
    ).toBeChecked();
    if (i < total - 1)
      await page.getByRole("button", { name: "Next", exact: true }).click();
  }
  const response = page.waitForResponse(
    (r) =>
      r.url().endsWith(`/quizzes/${quizId}/submit`) &&
      r.request().method() === "POST",
  );
  await page.getByRole("button", { name: /Submit/ }).click();
  const res = await response;
  expect(res.status()).toBe(200);
  const data = (await res.json()).data;
  expect(data.correct_count).toBe(correct);
  expect(data.question_count).toBe(total);
  expect(data.percentage).toBe(
    Math.round(((correct * 100) / total) * 100) / 100,
  );
  await expect(
    page.getByRole("heading", { name: "Answer Review" }),
  ).toBeVisible();
  await expect(
    page.getByText(`${data.percentage}%`, { exact: true }).first(),
  ).toBeVisible();
  return data;
}
async function shot(page, name) {
  await page.screenshot({
    path: `${process.env.WAVE1_SCREENSHOTS || "/tmp/core-wave1-screenshots"}/${name}.png`,
    fullPage: true,
  });
}
test("fresh failure → Today → pass → Progress → latest and historical review", async ({
  page,
}) => {
  await login(page);
  const failed = await attempt(page, 0);
  await expect(page.getByText("Not passed", { exact: true })).toBeVisible();
  await shot(page, "failed-result");
  await page.goto("/");
  await expect(
    page.getByText("Score 0%", { exact: true }).first(),
  ).toBeVisible();
  const passed = await attempt(page, 4);
  await expect(page.getByText("Passed", { exact: true })).toBeVisible();
  await shot(page, "passed-result");
  await page.goto("/");
  await expect(
    page.getByText("Score 100%", { exact: true }).first(),
  ).toBeVisible();
  await shot(page, "today-after-pass");
  await page.goto("/progress");
  await expect(
    page.getByRole("heading", { name: "Quiz results" }),
  ).toBeVisible();
  await expect(
    page.getByText(/Latest attempt: 4\/4 · 100% · Passed/),
  ).toBeVisible();
  await expect(page.getByText("Skills Mastery")).toHaveCount(0);
  await shot(page, "progress-after-pass");
  await page.goto("/quizzes/1/review");
  await expect(
    page.getByText(`Latest attempt: #${passed.attempt_id} · Passed`),
  ).toBeVisible();
  await shot(page, "saved-review-after-fail-pass");
  await page.reload();
  await expect(
    page.getByText(`Latest attempt: #${passed.attempt_id} · Passed`),
  ).toBeVisible();
  await page
    .getByRole("navigation", { name: "Attempt history" })
    .getByRole("link", { name: "Attempt 1: 0% · Not passed", exact: true })
    .click();
  await expect(
    page.getByText(`Historical attempt: #${failed.attempt_id} · Not passed`),
  ).toBeVisible();
  await expect(page.getByText("0%", { exact: true }).first()).toBeVisible();
  await page.reload();
  await expect(
    page.getByText(`Historical attempt: #${failed.attempt_id} · Not passed`),
  ).toBeVisible();
});
test("75 percent and a later failure preserve the best passing result", async ({
  page,
}) => {
  await login(page);
  await attempt(page, 3);
  await page.goto("/");
  await expect(
    page.getByText("Score 75%", { exact: true }).first(),
  ).toBeVisible();
  await page.goto("/quizzes/1/review");
  await expect(page.getByText("75%", { exact: true }).first()).toBeVisible();
  const failed = await attempt(page, 0);
  await page.goto("/quizzes/1/review");
  await expect(
    page.getByText(`Latest attempt: #${failed.attempt_id} · Not passed`),
  ).toBeVisible();
  await expect(
    page.getByText(/Best result: 4\/4 · 100% · Passed/),
  ).toBeVisible();
  await expect(
    page.getByText("Passing requirement earned", { exact: true }),
  ).toBeVisible();
  await page.goto("/progress");
  await expect(
    page.getByText(/Latest attempt: 0\/4 · 0% · Not passed/),
  ).toBeVisible();
  await expect(
    page.getByText(/Best result: 4\/4 · 100% · Passed/),
  ).toBeVisible();
});
test("mixed sizes retain explicit denominators and percentages", async ({
  page,
}) => {
  await login(page);
  await attempt(page, 2, 2, 2);
  await attempt(page, 3, 6, 3);
  await page.goto("/progress");
  await expect(
    page.getByText(/Latest attempt: 2\/2 · 100% · Passed/),
  ).toBeVisible();
  await expect(
    page.getByText(/Latest attempt: 3\/6 · 50% · Not passed/),
  ).toBeVisible();
});
test("admin learner summary has truthful units and evidence", async ({
  page,
}) => {
  await login(page, true);
  await page.goto("/admin/students");
  await expect(
    page.getByRole("columnheader", { name: "Average attempt (%)" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Details", exact: true })
    .first()
    .click();
  await expect(page.getByText(/Required quizzes passed: 2 \/ 3/)).toBeVisible();
  await expect(
    page.getByText(/Latest attempt: 0\/4 · 0% · Not passed/),
  ).toBeVisible();
  await expect(page.getByText("Skills Mastery")).toHaveCount(0);
  await shot(page, "admin-learner-summary");
});
