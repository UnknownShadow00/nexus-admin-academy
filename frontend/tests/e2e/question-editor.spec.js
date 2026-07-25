import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";

const adminUsername = process.env.NEXUS_E2E_ADMIN_USERNAME || "browser-admin";
const adminPassword = process.env.NEXUS_E2E_ADMIN_PASSWORD || "BrowserAdmin!2026";
const apiBaseUrl = process.env.NEXUS_E2E_API_URL || "http://127.0.0.1:8011";

function buildCsv(quizTitle) {
  const header =
    "quiz_title,question_type,question_text,option_a,option_b,option_c,option_d,option_e,option_f,option_g,option_h,correct_answers,explanation,difficulty,tags,source,published";
  const row = `${quizTitle},single,"Which protocol resolves domain names?",DNS,DHCP,ARP,NAT,,,,,A,"DNS resolves domain names to IP addresses.",1,networking,e2e-fixture,false`;
  return `${header}\n${row}\n`;
}

function writeTempCsv(content) {
  const filePath = path.join(os.tmpdir(), `nexus-e2e-editor-${Date.now()}-${Math.random().toString(36).slice(2)}.csv`);
  fs.writeFileSync(filePath, content, "utf-8");
  return filePath;
}

async function adminLogin(page) {
  await page.goto("/admin-login");
  await page.getByLabel("Username").fill(adminUsername);
  await page.getByLabel("Password").fill(adminPassword);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/admin$/);
}

/** Imports a single, valid, single-choice question via the real importer UI. */
async function importQuiz(page, quizTitle) {
  const csvPath = writeTempCsv(buildCsv(quizTitle));
  await page.goto("/admin/question-import");
  await page.getByLabel("Question import file").setInputFiles(csvPath);
  await page.getByRole("button", { name: "Preview" }).click();
  await expect(page.getByText("Valid rows (1)")).toBeVisible();

  const [confirmResponse] = await Promise.all([
    page.waitForResponse((res) => res.url().includes("/api/admin/quiz/import/confirm") && res.status() === 200),
    page.getByRole("button", { name: /Confirm import of 1 question/ }).click(),
  ]);
  const body = await confirmResponse.json();
  fs.unlinkSync(csvPath);
  return body.data.quiz_ids[0];
}

test.describe("Manual question editor", () => {
  test("supports dynamic option add/remove and toggling single-choice to multi-select", async ({ page }) => {
    await adminLogin(page);
    const quizId = await importQuiz(page, `E2E Editor Quiz ${Date.now()}`);
    await page.goto(`/admin/quizzes/${quizId}/edit`);

    // Only A-D exist at first (option_a-d are the only ones the CSV filled in).
    await expect(page.getByPlaceholder("Option E text")).toHaveCount(0);

    // Dynamically add a 5th option.
    await page.getByRole("button", { name: "Add option" }).click();
    await page.getByPlaceholder("Option E text").fill("MDNS");

    // Toggling a second correct answer turns this into a multi-select question.
    await page.getByLabel("Option C is correct").check();
    await expect(page.getByText("Students must select all correct answers and no incorrect answers.")).toBeVisible();

    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect(page.getByRole("button", { name: "Saved", exact: true })).toBeVisible();

    // Reload from the server to confirm the edit actually persisted, not just local state.
    await page.reload();
    await expect(page.getByPlaceholder("Option E text")).toHaveValue("MDNS");
    await expect(page.getByLabel("Option A is correct")).toBeChecked();
    await expect(page.getByLabel("Option C is correct")).toBeChecked();
    await expect(page.getByText("Students must select all correct answers and no incorrect answers.")).toBeVisible();

    // Dynamically remove it again.
    await page.getByRole("button", { name: "Remove option E" }).click();
    await expect(page.getByPlaceholder("Option E text")).toHaveCount(0);
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect(page.getByRole("button", { name: "Saved", exact: true })).toBeVisible();

    await page.reload();
    await expect(page.getByPlaceholder("Option E text")).toHaveCount(0);
  });

  test("validation-before-publish blocks a question broken by an edit until it's fixed", async ({ page }) => {
    await adminLogin(page);
    const quizId = await importQuiz(page, `E2E Validation Quiz ${Date.now()}`);
    await page.goto(`/admin/quizzes/${quizId}/edit`);

    // Break the question: say "Select 2 answers" while only one correct answer
    // is stored — a real select-N/answer-count mismatch. Live debounced
    // validation must flag this before save, and the save itself must
    // auto-flag the row for review.
    await page.getByLabel("Question text").fill("Which protocol resolves domain names? (Select 2 answers)");
    await expect(page.getByText("This question says Select 2, but 1 correct answer(s) are stored.")).toBeVisible();
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect(page.getByRole("button", { name: "Saved", exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByText("Flagged for review")).toBeVisible();

    // Validate the quiz's editorial metadata so only question-level validity gates publish.
    await page.getByLabel("Editorial status").selectOption("validated");
    await page.getByLabel("Answers validated").check();
    await page.getByRole("button", { name: "Save Organization" }).click();
    await expect(page.getByText("Organization saved.")).toBeVisible();

    await page.getByRole("button", { name: "Publish Quiz" }).click();
    await expect(page.getByText(/Cannot publish:.*flagged for/i)).toBeVisible();

    // Fix the question text; the edit auto-unflags it, and publish now succeeds.
    await page.getByLabel("Question text").fill("Which protocol resolves domain names?");
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await expect(page.getByRole("button", { name: "Saved", exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByText("Flagged for review")).toHaveCount(0);

    await page.getByRole("button", { name: "Publish Quiz" }).click();
    await expect(page.getByText("Published")).toBeVisible();
  });
});

test.describe("ExamCompass import regression", () => {
  test("bookmarklet-import preserves multi-select answers and flags invalid questions without rejecting the batch", async ({
    page,
  }) => {
    await adminLogin(page);
    const title = `E2E ExamCompass Quiz ${Date.now()}`;
    const payload = {
      title,
      source_url: "https://www.examcompass.com/some-a-plus-exam-quiz",
      week_number: 1,
      questions: [
        {
          question_text: "Which of these are private IP ranges? (Select 2 answers)",
          option_a: "10.0.0.0/8",
          option_b: "8.8.8.8/32",
          option_c: "192.168.0.0/16",
          option_d: "1.1.1.1/32",
          correct_answer: "A",
          all_correct_answers: ["A", "C"],
          explanation: "10.0.0.0/8 and 192.168.0.0/16 are both reserved private ranges.",
        },
        {
          // Deliberately unanswerable (no correct answer detected) — must be
          // flagged, not silently dropped or allowed to sink the whole batch.
          question_text: "Broken question scraped with no detected answer",
          option_a: "Only one option",
          correct_answer: "",
          all_correct_answers: [],
          explanation: "",
        },
      ],
    };

    // The admin session cookie triggers the backend's CSRF origin check, so an
    // Origin header matching a trusted origin (the frontend dev origin) is
    // required — a raw request-context call has no page navigation to derive
    // one from automatically the way a real browser fetch() would.
    const res = await page.request.post(`${apiBaseUrl}/api/admin/quiz/bookmarklet-import`, {
      data: payload,
      headers: { Origin: new URL(page.url()).origin },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.data.question_count).toBe(2);
    expect(body.data.flagged_for_review_count).toBe(1);

    await page.goto(`/admin/quizzes/${body.data.quiz_id}/edit`);
    // Two question cards render (the valid multi-select question, then the
    // broken one) — scope assertions to each card so identically-labeled
    // controls ("Option A is correct") on the other card can't collide.
    const question1Card = page.locator(".panel").filter({ hasText: "Question 1" });
    const question2Card = page.locator(".panel").filter({ hasText: "Question 2" });

    await expect(question1Card.getByText("Students must select all correct answers and no incorrect answers.")).toBeVisible();
    await expect(question1Card.getByLabel("Option A is correct")).toBeChecked();
    await expect(question1Card.getByLabel("Option C is correct")).toBeChecked();
    await expect(question1Card.getByText("Flagged for review")).toHaveCount(0);

    await expect(question2Card.getByText("Flagged for review")).toBeVisible();
  });
});
