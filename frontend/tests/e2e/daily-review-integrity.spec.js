import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";

const studentUsername = process.env.NEXUS_E2E_STUDENT_USERNAME || "browser-training-student";
const studentPassword = process.env.NEXUS_E2E_STUDENT_PASSWORD || "BrowserTraining!2026";
const adminUsername = process.env.NEXUS_E2E_ADMIN_USERNAME || "browser-admin";
const adminPassword = process.env.NEXUS_E2E_ADMIN_PASSWORD || "BrowserAdmin!2026";

// Reproduces the originally reported bug exactly: a 5-option, 3-answer
// multi-select question ("Select 3 answers") with option_f/g/h left blank —
// imported the way an ExamCompass-style import would produce it.
function buildCsv(quizTitle) {
  const header =
    "quiz_title,question_type,question_text,option_a,option_b,option_c,option_d,option_e,option_f,option_g,option_h,correct_answers,explanation,difficulty,tags,source,published";
  const row = `${quizTitle},multi,"When creating a new help desk ticket for ${quizTitle}, which basic information is typically required? (Select 3 answers)",User information,Expected resolution date,Device information,Escalation levels required,Problem description,,,,A|C|E,"Tickets need requester, device, and problem details up front.",2,help-desk,e2e-fixture,false`;
  return `${header}\n${row}\n`;
}

function writeTempCsv(content) {
  const filePath = path.join(os.tmpdir(), `nexus-e2e-review-${Date.now()}-${Math.random().toString(36).slice(2)}.csv`);
  fs.writeFileSync(filePath, content, "utf-8");
  return filePath;
}

function monitorPage(page) {
  const consoleErrors = [];
  const failedRequests = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("requestfailed", (request) => {
    const reason = request.failure()?.errorText || "unknown error";
    if (!reason.includes("ERR_ABORTED")) failedRequests.push(`${request.method()} ${request.url()}: ${reason}`);
  });
  return { consoleErrors, failedRequests };
}

async function assertNoHorizontalOverflow(page) {
  const dimensions = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width + 1);
}

async function adminLogin(page) {
  await page.goto("/admin-login");
  await page.getByLabel("Username").fill(adminUsername);
  await page.getByLabel("Password").fill(adminPassword);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/admin$/);
}

async function studentLogin(page) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(studentUsername);
  await page.getByLabel("Password").fill(studentPassword);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
}

/** Imports and publishes the fixture quiz via the real admin UI (importer +
 * editor), returning its quiz id. */
async function importAndPublishQuiz(page, quizTitle) {
  const csvPath = writeTempCsv(buildCsv(quizTitle));
  await adminLogin(page);
  await page.goto("/admin/question-import");
  await page.getByLabel("Question import file").setInputFiles(csvPath);
  await page.getByRole("button", { name: "Preview" }).click();
  await expect(page.getByText("Valid rows (1)")).toBeVisible();

  const [confirmResponse] = await Promise.all([
    page.waitForResponse((res) => res.url().includes("/api/admin/quiz/import/confirm") && res.status() === 200),
    page.getByRole("button", { name: /Confirm import of 1 question/ }).click(),
  ]);
  const body = await confirmResponse.json();
  const quizId = body.data.quiz_ids[0];
  fs.unlinkSync(csvPath);

  await page.goto(`/admin/quizzes/${quizId}/edit`);
  // Imported content starts unreviewed (matches the ExamCompass import
  // convention) — an admin must attest the answer keys before any
  // visibility flag, including publishing, can be enabled.
  await page.getByLabel("Editorial status").selectOption("validated");
  await page.getByLabel("Answers validated").check();
  await page.getByRole("button", { name: "Save Organization" }).click();
  await expect(page.getByText("Organization saved.")).toBeVisible();

  await page.getByRole("button", { name: "Publish Quiz" }).click();
  await expect(page.getByText("Published")).toBeVisible();

  return quizId;
}

async function runDailyReviewFlow(page, { viewport, quizTitleSuffix }) {
  await page.setViewportSize(viewport);
  const monitor = monitorPage(page);
  const quizTitle = `E2E Daily Review Quiz ${quizTitleSuffix}`;
  const quizId = await importAndPublishQuiz(page, quizTitle);

  await studentLogin(page);
  await page.goto(`/quizzes/${quizId}`);

  // The quiz-taking screen must never show a blank option.
  await expect(page.getByText("User information")).toBeVisible();
  const optionLabels = page.locator("label").filter({ hasText: /./ });
  const optionCount = await optionLabels.count();
  expect(optionCount).toBeGreaterThanOrEqual(5);

  // Deliberately answer wrong: pick only the incorrect option "Expected
  // resolution date" (option_b), not any of the correct A/C/E answers.
  await page.getByText("Expected resolution date").click();
  await page.getByRole("button", { name: "Submit Quiz" }).click();
  await page.on("dialog", (dialog) => dialog.accept()); // in case of an "unanswered questions" confirm

  await expect(page.getByText("Answer Review")).toBeVisible();
  await expect(page.getByText("User information")).toBeVisible();
  await expect(page.getByText("Device information", { exact: true })).toBeVisible();
  await expect(page.getByText("Problem description")).toBeVisible();
  await expect(page.getByText("Correct answer")).toHaveCount(3); // A, C, E all shown
  await expect(page.getByText("Your answer")).toHaveCount(1); // only the wrong pick, B

  if (viewport.width < 500) await assertNoHorizontalOverflow(page);

  // Daily Review: the wrong answer must have created a flashcard for this question.
  await page.goto("/");
  await expect(page.getByText("Show Answer")).toBeVisible({ timeout: 10000 });
  await page.getByRole("button", { name: "Show Answer" }).click();

  // No blank F/G/H rows: exactly the 5 real options render.
  await expect(page.getByText("User information")).toBeVisible();
  await expect(page.getByText("Expected resolution date")).toBeVisible();
  await expect(page.getByText("Device information")).toBeVisible();
  await expect(page.getByText("Escalation levels required")).toBeVisible();
  await expect(page.getByText("Problem description")).toBeVisible();

  // All three correct answers shown (the original bug: only one appeared).
  await expect(page.getByText("Correct", { exact: true })).toHaveCount(3);
  // The student's actual wrong pick (B) is distinguished from the correct ones.
  await expect(page.getByText("Your answer", { exact: true })).toHaveCount(1);
  // Explanation and quiz reference (Part 3 requirements) are present.
  await expect(page.getByText(/Tickets need requester/)).toBeVisible();
  await expect(page.getByText(new RegExp(`From: ${quizTitle}`))).toBeVisible();

  if (viewport.width < 500) await assertNoHorizontalOverflow(page);

  // Rating buttons are keyboard-reachable and labeled.
  const goodButton = page.getByRole("button", { name: /Good \(3\)/ });
  await expect(goodButton).toBeVisible();
  await goodButton.focus();
  await expect(goodButton).toBeFocused();
  await page.keyboard.press("Enter");

  await expect(page.getByText(/All caught up for today|Session complete/)).toBeVisible();

  expect(monitor.consoleErrors).toEqual([]);
  expect(monitor.failedRequests).toEqual([]);
}

test("Daily Review shows all correct answers with no blank options — desktop", async ({ page }) => {
  await runDailyReviewFlow(page, { viewport: { width: 1440, height: 1000 }, quizTitleSuffix: `desktop-${Date.now()}` });
});

test("Daily Review shows all correct answers with no blank options — mobile", async ({ page }) => {
  await runDailyReviewFlow(page, { viewport: { width: 375, height: 812 }, quizTitleSuffix: `mobile-${Date.now()}` });
});
