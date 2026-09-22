import { randomBytes } from "node:crypto";
import { expect, test } from "@playwright/test";

const api = process.env.NEXUS_E2E_API_URL;
const base = process.env.NEXUS_E2E_BASE_URL;
const local = api?.startsWith("http://127.0.0.1:") && base?.startsWith("http://127.0.0.1:");

async function login(page, username, password, admin = false) {
  await page.goto(admin ? "/admin-login" : "/login");
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Login", exact: true }).click();
  await expect(page).toHaveURL(admin ? /\/admin$/ : /\/(change-password)?$/);
}
const serverFailure = (route) => route.fulfill({ status: 500, contentType: "application/json", body: '{"detail":"Internal server error"}' });

test("beginner recovers notes, quiz position, and service failures on mobile", async ({ page }, testInfo) => {
  test.skip(!local, "This mutation test requires the disposable loopback stack.");
  test.setTimeout(150_000);
  const username = `browser-recovery-${randomBytes(6).toString("hex")}`;
  const password = randomBytes(18).toString("hex");
  const permanent = randomBytes(18).toString("hex");
  let studentId;
  try {
    await login(page, process.env.NEXUS_E2E_ADMIN_USERNAME, process.env.NEXUS_E2E_ADMIN_PASSWORD, true);
    const created = await page.request.post(`${api}/api/admin/students`, { headers: { Origin: base }, data: { name: "Disposable Recovery Learner", username, email: `${username}@example.invalid`, password } });
    expect(created.ok()).toBeTruthy();
    studentId = (await created.json()).data.student_id;
    await page.getByRole("button", { name: "Admin Sign Out" }).click();
    await login(page, username, password);
    await page.getByLabel("New password", { exact: true }).fill(permanent);
    await page.getByLabel("Confirm new password", { exact: true }).fill(permanent);
    await page.getByRole("button", { name: "Change password", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Today", exact: true })).toBeVisible();
    await page.goto("/lessons/1");
    await expect(page.getByRole("heading", { name: "Before your first quiz: what goes in a ticket?" })).toBeVisible();
    const note = page.getByRole("textbox", { name: "Your study notes" });
    await expect(note).toBeEnabled();
    await page.route("**/api/lessons/1/notes", (route) => route.request().method() === "PUT" ? serverFailure(route) : route.continue());
    await note.fill("A ticket records the user, device, problem, and evidence.");
    await page.getByRole("button", { name: "Save notes", exact: true }).click();
    await expect(page.getByText(/Notes could not be saved to your account/)).toBeVisible();
    await page.reload();
    await expect(page.getByRole("button", { name: "Restore draft" })).toBeVisible();
    await expect(note).toHaveValue("");
    await page.unroute("**/api/lessons/1/notes");
    await page.getByRole("button", { name: "Restore draft" }).click();
    await page.getByRole("button", { name: "Save notes", exact: true }).click();
    await expect(page.getByText("Saved to your account", { exact: true })).toBeVisible();
    await page.reload();
    await expect(note).toHaveValue("A ticket records the user, device, problem, and evidence.");
    await page.getByRole("button", { name: "Mark lesson complete", exact: true }).click();
    await expect(page.getByRole("button", { name: "Orientation complete", exact: true })).toBeVisible();
    await page.getByRole("link", { name: "Take quiz", exact: true }).click();
    await expect(page.getByText("Question 1 of 4", { exact: true })).toBeVisible();
    for (const width of [375, 390, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      const dimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
      expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width + 1);
      const answer = page.locator("fieldset label").first();
      expect((await answer.boundingBox()).height).toBeGreaterThanOrEqual(44);
    }
    await page.setViewportSize({ width: 375, height: 900 });
    const first = page.locator("fieldset input").first();
    await first.focus();
    await page.keyboard.press("Space");
    await expect(first).toBeChecked();
    const focusShadow = await first.evaluate((element) => getComputedStyle(element.parentElement).boxShadow);
    expect(focusShadow).not.toBe("none");
    await page.screenshot({ path: testInfo.outputPath("quiz-mobile-focus.png"), fullPage: true });
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(page.locator("fieldset h2")).toBeFocused();
    const question = await page.locator("fieldset").innerText();
    await page.reload();
    await expect(page.getByText("Question 2 of 4", { exact: true })).toBeVisible();
    await expect(page.locator("fieldset")).toHaveText(question, { useInnerText: true });
    await page.getByRole("button", { name: "Previous", exact: true }).click();
    await expect(page.locator("fieldset input:checked")).toHaveCount(1);
    // Complete a deliberately imperfect attempt to exercise learning feedback.
    for (let index = 1; index <= 4; index += 1) {
      await page.locator("fieldset label").first().click();
      if (index < 4) await page.getByRole("button", { name: "Next", exact: true }).click();
    }
    page.on("dialog", (dialog) => dialog.accept());
    await page.route("**/api/quizzes/42/submit", serverFailure);
    await page.getByRole("button", { name: "Submit Quiz", exact: true }).click();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.getByRole("button", { name: "Submit Quiz", exact: true })).toBeEnabled();
    await page.unroute("**/api/quizzes/42/submit");
    await page.getByRole("button", { name: "Submit Quiz", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Answer Review" })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath("quiz-mobile-feedback.png"), fullPage: true });
    await page.getByRole("button", { name: "Review missed questions" }).click();
    await expect(page.getByText("Correct", { exact: true })).toHaveCount(0);
    await page.getByRole("button", { name: "Try Again", exact: true }).click();
    await expect(page.getByText("Question 1 of 4", { exact: true })).toBeVisible();
    await expect(page.getByText("0 answered", { exact: true })).toBeVisible();
    await page.route("**/api/quizzes/42/review/**", serverFailure);
    await page.goto("/quizzes/42/review");
    await expect(page.getByRole("heading", { name: "Quiz review unavailable" })).toBeVisible();
    await page.unroute("**/api/quizzes/42/review/**");
    await page.getByRole("button", { name: "Try again", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Answer Review" })).toBeVisible();
    await page.route("**/api/lessons/1", serverFailure);
    await page.goto("/lessons/1");
    await expect(page.getByRole("heading", { name: "Lesson unavailable" })).toBeVisible();
    await page.unroute("**/api/lessons/1");
    await page.getByRole("button", { name: "Retry lesson" }).click();
    await expect(page.getByRole("heading", { name: "Welcome to Nexus", exact: true })).toBeVisible();
  } finally {
    if (studentId) {
      await page.context().clearCookies();
      await login(page, process.env.NEXUS_E2E_ADMIN_USERNAME, process.env.NEXUS_E2E_ADMIN_PASSWORD, true);
      const deleted = await page.request.delete(`${api}/api/admin/students/${studentId}`, { headers: { Origin: base } });
      expect(deleted.ok()).toBeTruthy();
    }
  }
});
