// UI fixture coverage only; real assessment persistence/reconciliation is tested in pytest.
import { test, expect } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { join } from "node:path";
for (const theme of ["light", "dark"]) test(`written pending status is not a provisional pass ${theme}`, async ({ page }) => {
  const question = { id: 41, type: "free_response", question_text: "Explain why an observed symptom is not yet a verified cause.", options: [] };
  let original, submitted = false;
  await page.addInitScript(value => { localStorage.setItem("theme", value); localStorage.setItem("selected_profile", JSON.stringify({ id: 42, name: "Assessment fixture" })); }, theme);
  await page.route("**/auth/**", route => route.fulfill({ json: { success: true, data: { student_id: 42, name: "Assessment fixture" } } }));
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let data = {};
    if (path.endsWith("/access")) data = { master_enabled: true, student_enabled: true, mode: "pilot" };
    else if (path.endsWith("/submit")) { original = route.request().postDataJSON().answers[41]; submitted = true; data = { score: 0, passed: true, grading_state: "pending", pass_percent: 80, results: [{ question_id: 41, question_text: question.question_text, student_answer: original, grading_status: "needs_review", is_correct: null, correct_answer: ["PRIVATE KEY"], explanation: "PRIVATE EXPLANATION" }] }; }
    else if (path.endsWith("/assessments/fixture")) data = { assessment: { title: "Written assessment fixture", role: "quick_check" }, attempt: { id: 91 }, questions: [question] };
    return route.fulfill({ json: { success: true, data } });
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/learning-v2/modules/module.fixture/assessments/fixture");
  const input = page.getByLabel("Your answer"); await input.fill("  I would record what the person saw, then compare it with a safe observation.\nA change alone does not prove the cause.  ");
  await page.getByRole("button", { name: "Submit answers", exact: true }).click();
  expect(submitted).toBe(true); expect(original.startsWith("  ")).toBe(true); expect(original.endsWith("  ")).toBe(true);
  await expect(page.getByRole("heading", { name: "Grading pending", exact: true })).toBeVisible();
  await expect(page.getByText("PRIVATE KEY")).toHaveCount(0); await expect(page.getByText("PRIVATE EXPLANATION")).toHaveCount(0);
  await expect(page.getByText(/Score:|Passed assessment|Failed assessment/)).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Try again", exact: true })).toHaveCount(0);
  if (process.env.NEXUS_ACADEMY_CAPTURE) { mkdirSync(process.env.NEXUS_ACADEMY_CAPTURE, { recursive: true }); await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map(image => image.decode().catch(() => {}))); }); await page.screenshot({ path: join(process.env.NEXUS_ACADEMY_CAPTURE, `written-pending-${theme}-fixture.png`), fullPage: true }); }
});
