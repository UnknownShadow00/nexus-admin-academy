import { test, expect } from "@playwright/test";
import { readFileSync, mkdirSync } from "node:fs";
import { basename, dirname, isAbsolute, join } from "node:path";
const credentialPath = process.env.NEXUS_ACADEMY_CREDENTIALS;
const fixture = credentialPath ? JSON.parse(readFileSync(credentialPath, "utf8")) : null;
test.skip(!fixture, "Supply explicit disposable Academy preview credentials.");
if (fixture && (!isAbsolute(fixture.database) || !basename(dirname(fixture.database)).startsWith("nexus-academy-phase1-") || !fixture.api.startsWith("http://127.0.0.1:") || !fixture.frontend.startsWith("http://127.0.0.1:"))) throw Error("Disposable loopback fixtures required");
const moduleKey = "module.nexus.beginner.stage1";
const key = "assess.nexus.beginner.s1.support_work";
const route = `/learning-v2/modules/${moduleKey}/assessments/${key}`;
const apiRoute = `/api/v2/curriculum/modules/${moduleKey}/assessments/${key}`;
async function get(page, path) { const res = await page.request.get(fixture.api + path); expect(res.status(), path).toBe(200); return (await res.json()).data; }
async function login(page, role = "v2", theme = "light") {
  await page.goto(fixture.frontend + "/login");
  await page.evaluate(value => localStorage.setItem("theme", value), theme); await page.reload();
  await page.getByLabel("Username", { exact: true }).fill(fixture[role].username);
  await page.getByLabel("Password", { exact: true }).fill(fixture[role].password);
  await page.getByRole("button", { name: "Login", exact: true }).click(); await expect(page.locator(".today-dashboard")).toBeVisible();
}
async function ready(page) { await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map(image => image.decode().catch(() => {}))); }); }
async function capture(page, name) { if (process.env.NEXUS_ACADEMY_CAPTURE) { mkdirSync(process.env.NEXUS_ACADEMY_CAPTURE, { recursive: true }); await ready(page); await page.screenshot({ path: join(process.env.NEXUS_ACADEMY_CAPTURE, name + ".png"), fullPage: true }); } }
async function noOverflow(page) { expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(await page.evaluate(() => innerWidth)); }
for (const width of [1440, 1280, 390]) for (const theme of ["light", "dark"]) test(`real Quiz ${width} ${theme}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 }); await login(page, "v2", theme); await page.request.post(fixture.api + apiRoute + "/attempts"); await page.goto(route);
  const data = await get(page, apiRoute);
  await expect(page.getByRole("heading", { level: 1, name: data.assessment.title })).toBeVisible();
  await expect(page.locator(".question-title h2")).toHaveText(data.questions[0].question_text);
  expect(data.questions.length).toBeGreaterThan(1);
  await page.locator(".choice").first().click();
  await page.getByRole("button", { name: "Next question", exact: true }).click();
  await expect(page.locator(".question-title h2")).toBeFocused();
  await expect(page.getByRole("progressbar", { name: "Questions answered" })).toHaveAttribute("aria-valuenow", "1");
  await expect(page.locator(".quiz-heading")).toContainText(`Current question 2 of ${data.questions.length}`);
  await expect(page.locator(".quiz-heading")).toContainText(`${Math.round(100 / data.questions.length)}% answered`);
  await expect(page.locator(".question-card")).toContainText("Not submitted to the server yet");
  await page.getByRole("button", { name: "Flag for review" }).click();
  await noOverflow(page);
  await page.evaluate(() => scrollTo(0, 0));
  if (width >= 1280) { const header = await page.locator(".quiz-header").boundingBox(); expect(header.x).toBe(276); expect(header.y).toBe(96); expect((await page.locator(".quiz-rail").boundingBox()).width).toBe(300); }
  const art = await page.locator(`.quiz-${theme === "light" ? "day" : "night"}`).evaluate(async image => { await image.decode(); return { width: image.naturalWidth, fit: getComputedStyle(image).objectFit }; }); expect(art.width).toBeGreaterThan(2000); expect(art.fit).toBe("cover");
  await capture(page, `quiz-${theme}-${width}`);
  await page.reload(); await expect(page.getByText(`Question 2 of ${data.questions.length}`, { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Previous", exact: true }).click(); await expect(page.locator(".choices input:checked")).toHaveCount(1);
});

test("real quiz unanswered review, failed transport retry, server result and deliberate retake", async ({ page }) => {
  await login(page); await page.request.post(fixture.api + apiRoute + "/attempts"); await page.goto(route); const data = await get(page, apiRoute);
  await page.getByRole("button", { name: "Review and submit", exact: true }).click();
  await expect(page.locator(".quiz-submit-review")).toContainText(`${data.questions.length} unanswered`);
  await page.getByRole("button", { name: "Review unanswered", exact: true }).click();
  for (let i = 0; i < data.questions.length; i++) { await page.locator(".choice").first().click(); if (i < data.questions.length - 1) await page.getByRole("button", { name: "Next question", exact: true }).click(); }
  await page.route("**/assessments/*/submit", route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Temporary fixture transport failure" }) }));
  await page.getByRole("button", { name: "Submit answers", exact: true }).click(); await expect(page.getByRole("alert")).toBeVisible(); await expect(page.locator(".choices input:checked")).toHaveCount(1);
  await page.unroute("**/assessments/*/submit");
  await page.getByRole("button", { name: "Submit answers", exact: true }).click(); await expect(page.locator("#assessment-outcome")).toBeVisible();
  const saved = await get(page, apiRoute); expect(saved.result.grading_state).toBe("graded");
  await expect(page.locator(".quiz-result-status")).toContainText(`Score: ${saved.result.score}%`);
  await capture(page, "quiz-result-light");
  await page.getByRole("button", { name: "Toggle dark mode" }).click(); await capture(page, "quiz-result-dark");
  if (!saved.result.passed) { await page.getByRole("button", { name: "Try again", exact: true }).click(); await expect(page.locator(".quiz-heading")).toContainText("0 answered"); }
});

const interactions = [
  ["matching", 1, "supports"], ["ordering", 1, "support_work"], ["safe_action", 1, "safe_thinking"],
  ["image_identification", 2, "connections"], ["typed_answer", 2, "files_apps"], ["command_output", 3, "whoami_preview"],
];
for (const theme of ["light", "dark"]) for (const [type, stage, suffix] of interactions) test(`real ${type} feedback restoration ${theme}`, async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 }); await login(page, "practice", theme);
  const module = `module.nexus.beginner.stage${stage}`, key = `interaction.nexus.beginner.s${stage}.${suffix}`;
  const path = `/api/v2/curriculum/modules/${module}/interactions/${key}`;
  await page.goto(`/learning-v2/modules/${module}/interactions/${key}`); const data = await get(page, path); const content = data.interaction.content;
  await expect(page.getByRole("heading", { level: 1, name: data.interaction.title })).toBeVisible();
  if (type === "matching") { const selects = page.locator(".academy-interaction select"); for (let i = 0; i < content.left.length; i++) await selects.nth(i).selectOption(content.right[i].id); }
  else if (type === "ordering") await page.getByRole("button", { name: / up$/ }).last().click();
  else if (type === "typed_answer") await page.getByLabel(content.question).fill("a different natural description");
  else await page.getByRole("radio").first().check();
  const formState = () => page.locator(".academy-interaction form").evaluate(form => ({ inputs: [...form.querySelectorAll("input,select")].map(input => ({ value: input.value, checked: input.checked || false })), order: form.querySelector("ol")?.textContent }));
  const before = await formState();
  await page.reload(); await expect(page.getByRole("button", { name: "Check answer", exact: true })).toBeVisible(); expect(await formState()).toEqual(before);
  const savedResponse = page.waitForResponse(response => response.url().endsWith(path + "/submit") && response.ok());
  await page.getByRole("button", { name: "Check answer", exact: true }).click(); const submitted = (await (await savedResponse).json()).data;
  const after = await get(page, path); expect(after.progress.attempt_count).toBe(data.progress.attempt_count + 1);
  await expect(page.locator(".academy-interaction .learning-feedback")).toContainText(submitted.submission_result.feedback);
  // Authoritative safety and exact-term rules are unchanged, including an incorrect typed paraphrase.
  if (type === "typed_answer") expect(submitted.submission_result.passed).toBe(false);
  if (type === "safe_action") { await page.getByRole("button", { name: /Practice again|Try again/, exact: true }).click(); await page.getByRole("radio", { name: "The issue is fixed and verified.", exact: true }).check(); await page.getByRole("button", { name: "Check answer", exact: true }).click(); await expect(page.locator(".learning-feedback")).toContainText("Not quite"); }
  await noOverflow(page);
  await capture(page, `exercise-${type}-${theme}`);
});

test("real legacy quiz keeps randomization/drafts, saves/reviews result and navigates back", async ({ page }) => {
  await login(page, "legacy"); await page.goto("/quizzes"); await page.getByRole("button", { name: "All Weeks", exact: true }).click();
  await page.locator(`a[href="/quizzes/${fixture.legacy_quiz_id}"]`).first().click(); await expect(page.locator(".question-title h2")).toBeVisible();
  await page.locator(".choice").first().click(); await page.getByRole("button", { name: "Next", exact: true }).click();
  const title = await page.locator(".question-title h2").textContent(); await page.reload(); await expect(page.locator(".question-title h2")).toHaveText(title);
  const buttons = page.locator(".question-grid button"), count = await buttons.count();
  for (let i = 0; i < count; i++) { await buttons.nth(i).click(); await page.locator(".choice").first().click(); }
  await page.getByRole("button", { name: "Submit Quiz", exact: true }).click(); await expect(page.getByRole("heading", { name: "Answer Review", exact: true })).toBeVisible();
  await capture(page, "legacy-quiz-result");
  await page.getByRole("link", { name: "Continue Learning", exact: true }).click(); await expect(page.locator(".today-dashboard")).toBeVisible(); await page.goBack(); await expect(page.locator(".quiz-header")).toBeVisible();
});

test("320px keyboard, theme persistence, authenticated access and real prerequisite denial", async ({ page, playwright }) => {
  await page.setViewportSize({ width: 320, height: 900 }); await login(page); await page.goto(route); await noOverflow(page);
  const input = page.getByRole("radio").first(); await input.focus(); await page.keyboard.press("Space"); await expect(input).toBeChecked();
  await page.getByRole("button", { name: "Toggle dark mode" }).click(); await page.reload(); await expect(page.locator(".academy")).toHaveClass(/dark/);
  const next = page.getByRole("button", { name: "Next question", exact: true });
  await next.evaluate(button => button.scrollIntoView({ block: "center" }));
  const control = await next.boundingBox(), mobileNav = await page.locator(".mobile-nav").boundingBox();
  expect(control.y + control.height).toBeLessThanOrEqual(mobileNav.y);
  const denied = await page.request.get(fixture.api + "/api/v2/curriculum/modules/module.nexus.beginner.stage4"); expect(denied.status()).toBe(403);
  const anonymous = await playwright.request.newContext(); expect((await anonymous.get(fixture.api + apiRoute)).status()).toBe(401); await anonymous.dispose();
  await page.getByRole("button", { name: "Account menu" }).click(); await page.getByRole("button", { name: "Sign out" }).click(); await expect(page).toHaveURL(/login/);
});
