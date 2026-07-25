import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { expect, test } from "@playwright/test";

const adminUsername = process.env.NEXUS_E2E_ADMIN_USERNAME || "browser-admin";
const adminPassword = process.env.NEXUS_E2E_ADMIN_PASSWORD || "BrowserAdmin!2026";

function buildSampleCsv(quizTitle) {
  const header =
    "quiz_title,question_type,question_text,option_a,option_b,option_c,option_d,option_e,option_f,option_g,option_h,correct_answers,explanation,difficulty,tags,source,published";
  const rows = [
    `${quizTitle},multi,"When creating a new help desk ticket, which basic information is typically required? (Select 3 answers)",User information,Expected resolution date,Device information,Escalation levels required,Problem description,,,,A|C|E,"Tickets need requester, device, and problem details up front.",2,help-desk,e2e-fixture,false`,
    `${quizTitle},single,Which command shows IP configuration on Windows?,ipconfig,dir,copy,del,,,,,A,ipconfig displays interface addressing.,1,networking,e2e-fixture,false`,
    `${quizTitle},multi,This row is intentionally broken for the preview test,Only one option,,,,,,,,A,,,,,false`,
  ];
  return [header, ...rows].join("\n") + "\n";
}

function writeTempCsv(content) {
  const filePath = path.join(os.tmpdir(), `nexus-e2e-import-${Date.now()}-${Math.random().toString(36).slice(2)}.csv`);
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

async function adminLogin(page) {
  await page.goto("/admin-login");
  await page.getByLabel("Username").fill(adminUsername);
  await page.getByLabel("Password").fill(adminPassword);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/admin$/);
}

test.describe("CSV/XLSX question importer", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
  });

  test("admin reaches the importer via Learning Content nav, beside ExamCompass Import", async ({ page }) => {
    const monitor = monitorPage(page);
    await adminLogin(page);

    await page.getByRole("button", { name: "Learning Content" }).click();
    await expect(page.getByRole("menuitem", { name: "ExamCompass Import" })).toBeVisible();
    await page.getByRole("menuitem", { name: "Import Questions (CSV/XLSX)" }).click();

    await expect(page).toHaveURL(/\/admin\/question-import$/);
    await expect(page.getByRole("heading", { name: "Import Questions" })).toBeVisible();

    expect(monitor.consoleErrors).toEqual([]);
    expect(monitor.failedRequests).toEqual([]);
  });

  test("preview separates valid and invalid rows, confirm imports only the valid ones, error report downloads, re-import skips duplicates", async ({
    page,
  }) => {
    const monitor = monitorPage(page);
    const quizTitle = `E2E Help Desk Import Quiz ${Date.now()}`;
    const csvPath = writeTempCsv(buildSampleCsv(quizTitle));

    await adminLogin(page);
    await page.goto("/admin/question-import");

    await page.getByLabel("Question import file").setInputFiles(csvPath);
    await page.getByRole("button", { name: "Preview" }).click();

    await expect(page.getByText(/3 row\(s\) parsed/)).toBeVisible();
    await expect(page.getByText("Valid rows (2)")).toBeVisible();
    await expect(page.getByText("Invalid rows (1)")).toBeVisible();
    await expect(page.getByText(/at least two valid options/i)).toBeVisible();

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download error report" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe("question_import_errors.csv");

    const confirmButton = page.getByRole("button", { name: /Confirm import of 2 question/ });
    await expect(confirmButton).toBeEnabled();

    const [confirmResponse] = await Promise.all([
      page.waitForResponse((res) => res.url().includes("/api/admin/quiz/import/confirm") && res.status() === 200),
      confirmButton.click(),
    ]);
    const confirmBody = await confirmResponse.json();
    expect(confirmBody.data.created).toBe(2);
    // The invalid row is filtered out client-side before confirm is ever
    // called — only the 2 rows shown as "valid" in preview are submitted.
    expect(confirmBody.data.skipped_invalid).toBe(0);

    await expect(page.getByText(/Import complete: 2 created/)).toBeVisible();

    expect(monitor.consoleErrors).toEqual([]);
    expect(monitor.failedRequests).toEqual([]);

    // Re-importing the exact same file must skip duplicates, not create copies.
    await page.getByLabel("Question import file").setInputFiles(csvPath);
    await page.getByRole("button", { name: "Preview" }).click();
    await expect(page.getByText("Valid rows (2)")).toBeVisible();

    const [secondConfirmResponse] = await Promise.all([
      page.waitForResponse((res) => res.url().includes("/api/admin/quiz/import/confirm") && res.status() === 200),
      page.getByRole("button", { name: /Confirm import of 2 question/ }).click(),
    ]);
    const secondBody = await secondConfirmResponse.json();
    expect(secondBody.data.created).toBe(0);
    expect(secondBody.data.skipped_duplicates).toBe(2);

    fs.unlinkSync(csvPath);
  });
});
