import { test, expect } from "@playwright/test";
import { readFileSync, mkdirSync } from "node:fs";
import { basename, dirname, isAbsolute, join } from "node:path";

const credentialPath = process.env.NEXUS_ACADEMY_CREDENTIALS;
const fixture = credentialPath ? JSON.parse(readFileSync(credentialPath, "utf8")) : null;
test.skip(!fixture, "Supply the disposable Academy preview credential file.");
if (fixture && (!isAbsolute(fixture.database) || !basename(dirname(fixture.database)).startsWith("nexus-academy-phase1-") || !fixture.api.startsWith("http://127.0.0.1:") || !fixture.frontend.startsWith("http://127.0.0.1:"))) throw new Error("Disposable loopback fixtures are required.");
const moduleKey = "module.nexus.beginner.stage1";
const lessonKey = "lesson.nexus.beginner.s1.support_work";
const lessonRoute = `/learning-v2/modules/${moduleKey}/lessons/${lessonKey}`;
const apiLesson = `/api/v2/curriculum/modules/${moduleKey}/lessons/${lessonKey}`;
async function get(page, path) { const response = await page.request.get(fixture.api + path); expect(response.status(), path).toBe(200); return (await response.json()).data; }
async function login(page, role = "v2", theme = "light") {
  await page.goto(fixture.frontend + "/login");
  await page.evaluate(value => localStorage.setItem("theme", value), theme);
  await page.reload();
  await page.getByLabel("Username", { exact: true }).fill(fixture[role].username);
  await page.getByLabel("Password", { exact: true }).fill(fixture[role].password);
  await page.getByRole("button", { name: "Login", exact: true }).click();
  await expect(page.locator(".today-dashboard")).toBeVisible();
}
async function noOverflow(page) { expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(await page.evaluate(() => innerWidth)); }

for (const width of [1440, 1280, 390]) for (const theme of ["light", "dark"]) test(`real Lesson content, geometry and art ${width} ${theme}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 }); await login(page, "v2", theme); await page.goto(lessonRoute);
  const data = await get(page, apiLesson);
  const module = await get(page, `/api/v2/curriculum/modules/${moduleKey}`);
  await expect(page.getByRole("heading", { level: 1, name: data.lesson.title, exact: true })).toBeVisible();
  await expect(page.locator(".lesson-heading")).toContainText(data.lesson.summary);
  await expect(page.locator(".lesson-prose")).toContainText("Listening and testing save time.");
  for (const objective of data.lesson.objectives) await expect(page.locator(".lesson-objectives")).toContainText(objective.text);
  await expect(page.locator(".lesson-catalog .lesson-list li")).toHaveCount(module.lessons.length);
  await expect(page.locator(".lesson-list [aria-current=page]")).toContainText(data.lesson.title);
  await expect(page.locator(".lesson-video .btn-video")).toHaveAttribute("href", data.lesson.resources[0].url);
  await expect(page.locator(".embedded-practice").getByRole("button", { name: "Check answer", exact: true })).toBeVisible();
  await expect(page.locator(".academy-lesson").getByRole("button", { name: "Mark lesson complete", exact: true })).toHaveCount(0);
  await noOverflow(page);
  const art = await page.locator(".lesson-video img").evaluate(async image => { await image.decode(); return { width: image.naturalWidth, height: image.naturalHeight, fit: getComputedStyle(image).objectFit }; });
  expect(art).toEqual({ width: 2172, height: 724, fit: "cover" });
  const poster = await page.locator(".lesson-video").boundingBox();
  expect(Math.abs(poster.width / poster.height - (width < 768 ? 4 / 3 : 2))).toBeLessThan(.02);
  if (width >= 1280) {
    const card = await page.locator(".lesson-heading-card").boundingBox(); expect(card.x).toBe(276); expect(card.y).toBe(96);
    expect(await page.locator(".lesson-rail").evaluate(e => e.getBoundingClientRect().width)).toBe(290);
    expect(await page.locator(".sidebar").evaluate(e => e.getBoundingClientRect().width)).toBe(248);
  }
  if (process.env.NEXUS_ACADEMY_CAPTURE) { mkdirSync(process.env.NEXUS_ACADEMY_CAPTURE, { recursive: true }); await page.evaluate(() => document.fonts.ready); await page.screenshot({ path: join(process.env.NEXUS_ACADEMY_CAPTURE, `lesson-${theme}-${width}.png`), fullPage: true }); }
});

test("embedded exercise submissions persist through the real backend without awarding lesson mastery", async ({ page }) => {
  await login(page); await page.goto(lessonRoute);
  const before = await get(page, apiLesson);
  const interaction = await get(page, `/api/v2/curriculum/modules/${moduleKey}/interactions/${before.interactions[0].interaction.key}`);
  const rows = page.locator('.embedded-practice ol[aria-label="Steps in your chosen order"] > li');
  await expect(rows).toHaveCount(4);
  // Authored order in backend/content/interactions/nexus-beginner-aplus-v1.yaml;
  // the public API deliberately shuffles its presentation.
  for (const [index, id] of ["listen", "ask", "check", "verify"].entries()) {
    const step = interaction.interaction.content.steps.find(item => item.id === id);
    const row = rows.filter({ hasText: step.text });
    while ((await rows.allTextContents()).findIndex(text => text.includes(step.text)) > index) await row.getByRole("button", { name: / up$/ }).click();
  }
  await page.locator(".embedded-practice").getByRole("button", { name: "Check answer", exact: true }).click();
  await expect(page.locator(".embedded-practice").getByRole("status").filter({ hasText: /^Correct/ })).toBeVisible();
  const after = await get(page, apiLesson);
  expect(after.interactions[0].progress.passed).toBe(true);
  expect(after.lesson.group_status).not.toBe("completed");
  await page.reload(); await expect(page.locator(".embedded-practice")).toContainText(`${after.interactions[0].progress.attempt_count} attempt`);
  await expect(page.getByRole("heading", { name: "Lesson done", exact: true })).toHaveCount(0);
});

test("resources record exposure, lesson sequence and browser back use real routes", async ({ page }) => {
  await login(page); await page.goto(lessonRoute);
  const data = await get(page, apiLesson);
  const saved = page.waitForResponse(response => response.url().endsWith(`/resources/${data.lesson.resources[0].key}/activity`) && response.ok());
  const popup = page.waitForEvent("popup"); await page.locator(".lesson-video .btn-video").click(); await saved; (await popup).close();
  const after = await get(page, apiLesson); expect(after.lesson.resources[0].opened_at).toBeTruthy(); expect(after.lesson.resources[0].watched_at).toBeNull();
  await page.getByRole("link", { name: "Previous lesson", exact: true }).click();
  await expect(page).toHaveURL(fixture.frontend + `/learning-v2/modules/${moduleKey}/lessons/${data.previous_lesson_key}`);
  await page.goBack(); await expect(page.getByRole("heading", { level: 1, name: data.lesson.title })).toBeVisible();
});

test("legacy lesson notes and completion save to the disposable API and survive reload", async ({ page }) => {
  await login(page, "legacy"); const training = await get(page, "/api/training"); const route = (training.next_activity || training.recently_completed).destination_route;
  await page.goto(route); const lesson = await get(page, `/api${route}`);
  await expect(page.getByRole("heading", { level: 1, name: lesson.title, exact: true })).toBeVisible();
  const notes = page.getByRole("textbox", { name: "Your study notes" }); await expect(notes).toBeEnabled();
  const note = `Phase 2 disposable study note: record only observed evidence. ${Date.now()}`;
  await notes.fill(note);
  const saved = page.waitForResponse(response => response.url().endsWith(`/lessons/${lesson.id}/notes`) && response.request().method() === "PUT" && response.ok());
  await page.getByRole("button", { name: "Save notes", exact: true }).click(); await saved;
  if (!lesson.is_complete) await page.getByRole("button", { name: "Mark lesson complete", exact: true }).click();
  await expect.poll(async () => (await get(page, `/api${route}`)).is_complete).toBe(true);
  await page.reload(); await expect(notes).toHaveValue(note);
});

test("server prerequisite lock, non-enrolled V2 access and lesson retry remain enforced", async ({ page }) => {
  await login(page); await page.goto("/learning-v2/modules/module.nexus.beginner.stage4/lessons/lesson.nexus.beginner.s4.find_protect");
  await expect(page.getByRole("alert")).toContainText("Finish Stage 1");
  await expect(page.locator(".lesson-video")).toHaveCount(0);
  await page.route(`**${apiLesson}`, route => route.fulfill({ status: 500, contentType: "application/json", body: '{"detail":"Unavailable"}' }));
  await page.goto(lessonRoute); await expect(page.getByRole("alert")).toBeVisible();
  await page.unroute(`**${apiLesson}`); await page.getByRole("button", { name: /Try again/ }).click();
  await expect(page.getByRole("heading", { level: 1, name: "What support technicians do" })).toBeVisible();
  await page.getByRole("button", { name: "Account menu" }).click(); await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await login(page, "legacy"); await page.goto(lessonRoute); await expect(page.getByRole("alert")).toBeVisible(); await expect(page.locator(".academy-lesson")).toHaveCount(0);
});

test("lesson section links, theme persistence and mobile controls remain usable at 320px", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 812 }); await login(page); await page.goto(lessonRoute); await noOverflow(page);
  await page.getByRole("navigation", { name: "Lesson sections" }).getByRole("link", { name: "Try it", exact: true }).click();
  await expect(page.locator("#lesson-practice")).toBeFocused();
  await page.locator(".lesson-bottom .btn-primary").scrollIntoViewIfNeeded();
  const button = await page.locator(".lesson-bottom .btn-primary").boundingBox(); const nav = await page.locator(".mobile-nav").boundingBox(); expect(button.y + button.height).toBeLessThanOrEqual(nav.y);
  await page.getByRole("button", { name: "Toggle dark mode", exact: true }).click();
  await page.reload(); await expect(page.locator(".academy")).toHaveClass(/dark/); await noOverflow(page);
});

test("visiting a lesson leaves the approved Today presentation unchanged", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.clock.install({ time: new Date("2026-10-09T15:00:00Z") });
  await login(page); await expect(page.locator(".today-work-plan li").first()).toBeVisible();
  await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map(image => image.decode())); });
  const before = await page.screenshot({ fullPage: true, animations: "disabled" });
  await page.goto(lessonRoute); await expect(page.locator(".embedded-practice")).toBeVisible();
  // Navigate through the SPA so the lesson stylesheet remains loaded.
  await page.locator(".sidebar").getByRole("link", { name: "Today", exact: true }).click();
  await expect(page.locator(".today-work-plan li").first()).toBeVisible();
  await page.locator("body").click({ position: { x: 1, y: 1 } });
  await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map(image => image.decode())); });
  const after = await page.screenshot({ fullPage: true, animations: "disabled" });
  expect(after.equals(before)).toBe(true);
});
