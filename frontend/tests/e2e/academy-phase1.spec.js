import { test, expect } from "@playwright/test";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve, join, dirname, basename, isAbsolute } from "node:path";

const credentialPath = process.env.NEXUS_ACADEMY_CREDENTIALS;
const fixture = credentialPath ? JSON.parse(readFileSync(credentialPath, "utf8")) : null;
test.skip(!fixture, "Start scripts/e2e/academy_phase1_preview.py and supply its disposable credential file.");
if (fixture && (!isAbsolute(fixture.database) || !basename(dirname(fixture.database)).startsWith("nexus-academy-phase1-") || !fixture.api.startsWith("http://127.0.0.1:") || !fixture.frontend.startsWith("http://127.0.0.1:"))) throw new Error("Academy browser tests require the isolated loopback preview, never live accounts.");

async function get(page, path) {
  const response = await page.request.get(fixture.api + path);
  expect(response.status(), path).toBe(200);
  const body = await response.json();
  return body.data ?? body;
}

async function login(page, role = "v2", theme = "light", destination = "/") {
  await page.addInitScript(value => { if (!localStorage.getItem("theme")) localStorage.setItem("theme", value); }, theme);
  await page.goto(fixture.frontend + "/login?next=" + encodeURIComponent(destination));
  await page.getByLabel("Username", { exact: true }).fill(fixture[role].username);
  await page.getByLabel("Password", { exact: true }).fill(fixture[role].password);
  await page.getByRole("button", { name: "Login", exact: true }).click();
  if (destination === "/") await expect(page.getByRole("heading", { name: /Good (morning|afternoon|evening)/ })).toBeVisible();
}

async function noOverflow(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(await page.evaluate(() => innerWidth));
}

for (const width of [1440, 1280, 390]) for (const theme of ["light", "dark"]) {
  test(`real API Today, geometry and art ${width} ${theme}`, async ({ page }) => {
    const errors = [];
    page.on("pageerror", e => errors.push(e.message));
    await page.setViewportSize({ width, height: 900 });
    await login(page, "v2", theme);
    await expect(page.locator(".today-work-plan li").first()).toBeVisible();
    const learning = await get(page, "/api/v2/curriculum");
    const stats = await get(page, `/api/students/${fixture.v2.student_id}/stats`);
    await expect(page.locator("#today-primary-heading")).toHaveText(learning.current.continue.title);
    await expect(page.locator("#continue-learning .continue-copy a")).toHaveAttribute("href", learning.current.continue.route);
    await expect(page.locator(".streak-count strong")).toHaveText(String(stats.streak));
    if (width >= 1280) await expect(page.locator(".rank")).toContainText(`${stats.total_xp} XP`);
    const groups = learning.current.progress.groups;
    await expect(page.locator(".progress-ring strong")).toHaveText(`${Math.round(groups.completed / groups.total * 100)}%`);
    await expect(page.locator(".academy")).toHaveClass(new RegExp(theme));
    await noOverflow(page);
    const contrast = await page.locator(".academy").evaluate(element => {
      const style = getComputedStyle(element);
      const luminance = hex => {
        let value = hex.replace("#", "");
        if (value.length === 3) value = [...value].map(char => char + char).join("");
        const rgb = value.match(/../g).map(channel => parseInt(channel, 16) / 255);
        const linear = rgb.map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
        return .2126 * linear[0] + .7152 * linear[1] + .0722 * linear[2];
      };
      const token = name => style.getPropertyValue(name).trim();
      return [[token("--ink"), token("--card")], [token("--sub"), token("--card2")], [token("--mute"), token("--card")], [token("--purple-ink"), token("--card")], ["#FFFFFF", "#7C3AED"]].map(([fg, bg]) => {
        const a = luminance(fg), b = luminance(bg);
        return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
      });
    });
    expect(Math.min(...contrast)).toBeGreaterThanOrEqual(4.5);
    const art = await page.evaluate(async () => {
      await Promise.all([...document.images].map(i => i.decode()));
      return [...document.querySelectorAll(".scene img")].map(i => ({ natural: [i.naturalWidth, i.naturalHeight], rendered: [i.getBoundingClientRect().width, i.getBoundingClientRect().height], fit: getComputedStyle(i).objectFit, hero: i.closest(".scene-hero") !== null, name: i.className }));
    });
    expect(art.every(i => i.natural[0] > 0 && ["contain", "cover"].includes(i.fit))).toBe(true);
    for (const item of art.filter(i => i.hero && ["castle", "wanderer"].includes(i.name))) expect(Math.abs(item.natural[0] / item.natural[1] - item.rendered[0] / item.rendered[1])).toBeLessThan(.01);
    expect(await page.locator(".scene .wanderer").count()).toBe(1);
    if (width >= 1280) {
      expect(await page.locator(".sidebar").evaluate(e => e.getBoundingClientRect().width)).toBe(248);
      expect(await page.locator(".hero").evaluate(e => e.getBoundingClientRect().y)).toBe(96);
    }
    const capture = process.env.NEXUS_ACADEMY_CAPTURE;
    if (capture) { mkdirSync(resolve(capture), { recursive: true }); await page.screenshot({ path: join(capture, `today-${theme}-${width}.png`), fullPage: true }); }
    expect(errors).toEqual([]);
  });
}

test("real login, Continue lesson, browser back, search and persistent theme", async ({ page }) => {
  await login(page);
  const learning = await get(page, "/api/v2/curriculum");
  const route = learning.current.continue.route;
  await page.locator("#continue-learning .continue-copy a").click();
  await expect(page).toHaveURL(fixture.frontend + route);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { name: /Good / })).toBeVisible();
  await page.getByRole("button", { name: "Toggle dark mode", exact: true }).click();
  await expect(page.locator(".academy")).toHaveClass(/dark/);
  await page.reload();
  await expect(page.locator(".academy")).toHaveClass(/dark/);
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("searchbox")).toBeFocused();
  await page.getByRole("searchbox").fill("Nexus");
  await expect(page.getByRole("region", { name: "Search results" })).toBeVisible();
  await expect(page.getByText("Searching…", { exact: true })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Account menu", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign out", exact: true })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Account menu", exact: true })).toBeFocused();
});

test("legacy enrollment keeps legacy continuation and V2 rejects a typed route", async ({ page }) => {
  await login(page, "legacy");
  const access = await get(page, "/api/v2/curriculum/access");
  expect(access.student_enabled).toBe(false);
  await expect(page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "My Course", exact: true })).toHaveCount(0);
  const training = await get(page, "/api/training");
  await expect(page.locator("#continue-learning .continue-copy a")).toHaveAttribute("href", training.next_activity.destination_route);
  await page.locator("#continue-learning .continue-copy a").click();
  await expect(page).toHaveURL(fixture.frontend + training.next_activity.destination_route);
  const denied = await page.request.get(fixture.api + "/api/v2/curriculum");
  // The existing API conceals non-enrolled V2 endpoints with 404.
  expect(denied.status()).toBe(404);
  await page.goto(fixture.frontend + "/learning-v2");
  await expect(page.getByRole("alert")).toBeVisible();
});

test("logout clears the student session and protected Today returns to login", async ({ page }) => {
  await login(page);
  await page.getByRole("button", { name: "Account menu", exact: true }).click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(fixture.frontend + "/login");
  expect((await page.request.get(fixture.api + "/auth/me")).status()).toBe(401);
  await page.goto(fixture.frontend + "/");
  await expect(page).toHaveURL(fixture.frontend + "/login");
  expect(await page.evaluate(() => localStorage.getItem("selected_profile"))).toBeNull();
});

test("mobile navigation and menu stay keyboard accessible", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await page.getByRole("button", { name: "Toggle menu", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "Learner navigation" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Close menu", exact: true })).toBeFocused();
  await expect(page.getByRole("navigation", { name: "Mobile primary navigation" })).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Toggle menu", exact: true })).toBeFocused();
  await page.getByRole("navigation", { name: "Mobile primary navigation" }).getByRole("link", { name: "My Course", exact: true }).click();
  await expect(page).toHaveURL(fixture.frontend + "/learning-v2");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await noOverflow(page);
});

test("Today loading, failed response and retry use real data after recovery", async ({ page }) => {
  await login(page);
  let release;
  const pending = new Promise(resolve => { release = resolve; });
  await page.route(`**/api/students/${fixture.v2.student_id}/stats`, async route => { await pending; await route.fulfill({ status: 500, json: { detail: "Disposable test failure" } }); });
  await page.reload();
  await expect(page.getByRole("status", { name: "Loading Today" })).toBeVisible();
  release();
  await expect(page.getByRole("heading", { name: "Today is temporarily unavailable" })).toBeVisible();
  await expect(page.locator(".hero")).toHaveCount(0);
  await page.unroute(`**/api/students/${fixture.v2.student_id}/stats`);
  await page.getByRole("button", { name: "Try again", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Good / })).toBeVisible();
});

test("optional work-plan failure preserves real Continue and can retry", async ({ page }) => {
  await login(page);
  const learning = await get(page, "/api/v2/curriculum");
  const path = `**/api/v2/curriculum/modules/${learning.current.module.key}`;
  await page.route(path, route => route.fulfill({ status: 500, json: { detail: "Disposable test failure" } }));
  await page.reload();
  await expect(page.getByRole("button", { name: "Retry work plan" })).toBeVisible();
  await expect(page.locator("#continue-learning .continue-copy a")).toHaveAttribute("href", learning.current.continue.route);
  await page.unroute(path);
  await page.getByRole("button", { name: "Retry work plan" }).click();
  await expect(page.locator(".today-work-plan li").first()).toBeVisible();
});

test("admin authentication and appearance remain separate from the learner shell", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  await page.goto(fixture.frontend + "/admin");
  await expect(page.getByRole("heading", { name: "Admin Login" })).toBeVisible();
  await page.getByLabel("Username", { exact: true }).fill(fixture.admin.username);
  await page.getByLabel("Password", { exact: true }).fill(fixture.admin.password);
  await page.getByRole("button", { name: "Login", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Admin Dashboard", exact: true })).toBeVisible();
  await expect(page.locator(".app-header-admin")).toBeVisible();
  await expect(page.locator(".academy")).toHaveCount(0);
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--nexus-action").trim())).toBe("#0c6b80");
  await expect(page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", { name: "Students", exact: true })).toBeVisible();
});
