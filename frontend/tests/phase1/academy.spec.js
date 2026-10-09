import { expect, test } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import * as fixture from './fixtures.mjs';
import { contrastMeasurements } from './contrast.mjs';

const gallery = resolve('../docs/visual-qa/academy-phase1');
mkdirSync(gallery, { recursive: true });
async function signIn(page, cohort = 'v2', action = true, origin = '') {
  await page.goto(origin + '/login');
  await page.getByLabel('Username').fill(`phase1-${cohort}`);
  await page.getByLabel('Password').fill('fixture-only-password');
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Today', exact: true })).toBeVisible();
  if (action) await expect(page.locator('.today-primary-action')).toBeVisible();
}
async function noOverflow(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
}
test.beforeEach(async ({ context }) => {
  await context.route('**/*', (route) => {
    const url = new URL(route.request().url());
    if (url.protocol === 'http:' && url.hostname === '127.0.0.1' && ['5819', '5820', '5818'].includes(url.port)) return route.continue();
    return route.abort('blockedbyclient');
  });
});
for (const theme of ['light', 'dark']) {
  for (const width of [1440, 1280, 1024, 390]) {
    test(`Today ${theme} ${width}: server route, one action, responsive shell`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.addInitScript((mode) => localStorage.setItem('theme', mode), theme);
      await signIn(page);
      await expect(page.locator('.today-primary-action')).toHaveAttribute('href', fixture.continuation.route);
      await expect(page.locator('.today-page .btn-primary')).toHaveCount(1);
      await expect(page.getByRole('progressbar', { name: 'Lessons completed' })).toHaveAttribute('value', '2');
      await expect(page.getByRole('progressbar', { name: 'Quick Checks passed' })).toHaveAttribute('max', '5');
      await expect(page.getByRole('region', { name: 'Your learning record' })).not.toContainText('Mastered');
      await expect(page.getByRole('complementary', { name: 'Mentor follow-up' })).toHaveCount(0);
      const nav = page.getByRole('navigation', { name: 'Primary navigation', exact: true });
      if (width >= 1280) await expect(nav).toBeVisible(); else await expect(nav).toBeHidden();
      await noOverflow(page);
      await page.screenshot({ path: `${gallery}/today-${theme}-${width}.png`, fullPage: true });
      const samples = await page.evaluate(() => {
        const specs = [
          ['.app-brand-subtitle', false], ['.today-primary-title', false], ['.today-context', false],
          ['.today-primary .type-label', false], ['.today-primary .type-secondary', false],
          ['.today-primary .type-meta', false], ['.today-primary-action', true],
          ['.today-primary .status-tone', true], ['.today-record-item .type-label', false],
          ['.today-motivation-item .type-meta', false], ['.today-record > .type-meta', false],
          ['.today-bottom-line', false], ['.today-bottom-line a', false],
          ['.academy-sidebar .app-nav-link', true], ['.academy-sidebar-footer span', false],
          ['.app-bottom-nav-link', true],
        ];
        return specs.flatMap(([selector, box]) => [...document.querySelectorAll(selector)].filter((el) => el.checkVisibility()).map((el) => {
          const rect = el.getBoundingClientRect();
          return { selector, color: getComputedStyle(el).color,
            x: rect.left + (box ? rect.width / 2 : -3), y: rect.top + (box ? 4 : rect.height / 2) };
        }));
      });
      const measured = contrastMeasurements(`${gallery}/today-${theme}-${width}.png`, samples);
      writeFileSync(`${gallery}/contrast-${theme}-${width}.json`, JSON.stringify(measured, null, 2) + '\n');
      for (const sample of measured) expect(sample.ratio, `${theme}/${width}: ${sample.selector}`).toBeGreaterThanOrEqual(4.5);
      if (width === 1440) {
        await nav.getByRole('button', { name: 'Extra Practice' }).click();
        await expect(nav.getByRole('link', { name: 'CLI Labs', exact: true })).toBeVisible();
        await page.screenshot({ path: `${gallery}/sidebar-expanded-${theme}.png` });
        await page.keyboard.press('Escape');
        await expect(nav.getByRole('button', { name: 'Extra Practice' })).toHaveAttribute('aria-expanded', 'false');
        await nav.getByRole('link', { name: 'Today', exact: true }).focus();
        expect(await nav.getByRole('link', { name: 'Today', exact: true }).evaluate((el) => getComputedStyle(el).outlineWidth)).toBe('3px');
        await page.screenshot({ path: `${gallery}/sidebar-focus-${theme}.png` });
      }
      if (width === 390) {
        await page.getByRole('button', { name: 'Toggle menu' }).click();
        await expect(page.locator('#app-main')).toHaveAttribute('inert', '');
        await page.screenshot({ path: `${gallery}/mobile-menu-${theme}.png` });
        await page.keyboard.press('Escape');
        await expect(page.getByRole('button', { name: 'Toggle menu' })).toBeFocused();
      }
    });
  }
}
test('Continue opens supplied lesson; back, theme persistence and logout work', async ({ page }) => {
  await signIn(page);
  await page.locator('.today-primary-action').click();
  await expect(page).toHaveURL(new URL(fixture.continuation.route, 'http://127.0.0.1:5819').href);
  await expect(page.getByRole('heading', { name: fixture.lesson.title, exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Toggle dark mode' }).click();
  await page.reload();
  await expect(page.locator('html')).toHaveClass('dark');
  await page.goBack();
  await expect(page.getByRole('heading', { name: 'Today', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Account menu' }).click();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.locator('.academy-sidebar')).toHaveCount(0);
  await page.goto('/');
  await expect(page).toHaveURL(/\/login$/);
});
test('legacy keeps three destinations and backend Continue; admin access stays closed', async ({ page }) => {
  await signIn(page, 'legacy');
  const nav = page.getByRole('navigation', { name: 'Primary navigation', exact: true });
  await expect(nav.getByRole('link')).toHaveCount(3);
  await expect(nav.getByRole('link', { name: 'My Course' })).toHaveCount(0);
  await expect(page.locator('.today-primary-action')).toHaveAttribute('href', fixture.legacyActivity.destination_route);
  await page.screenshot({ path: `${gallery}/legacy-light-1440.png`, fullPage: true });
  await page.locator('.today-primary-action').click();
  await expect(page.getByRole('heading', { name: 'Welcome to Nexus', exact: true })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole('heading', { name: 'Today', exact: true })).toBeVisible();
  await page.goto('/learning-v2');
  await expect(page.getByRole('alert')).toBeVisible();
  await page.goto('/admin');
  await expect(page).toHaveURL(/\/admin-login/);
  await expect(page.locator('.app-header-admin')).toHaveCount(0);
});
test('loading, retry and empty state remain honest', async ({ page }) => {
  let release;
  const waiting = new Promise((resolve) => { release = resolve; });
  await page.route('**/api/students/*/stats', async (route) => { await waiting; return route.fulfill({ status: 400, json: { detail: 'Fixture failure' } }); });
  await page.goto('/login');
  await page.getByLabel('Username').fill('phase1-v2');
  await page.getByLabel('Password').fill('fixture-only-password');
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  await expect(page.getByRole('status', { name: 'Loading Today' })).toBeVisible();
  release();
  await expect(page.getByRole('alert')).toContainText('Today is temporarily unavailable');
  await expect(page.locator('.today-primary-action')).toHaveCount(0);
  await page.unroute('**/api/students/*/stats');
  await page.route('**/api/v2/curriculum', (route) => route.fulfill({ json: { success: true, data: { current: null, modules: [], corrections: [] } } }));
  await page.route('**/api/training', (route) => route.fulfill({ json: { success: true, data: {} } }));
  await page.getByRole('button', { name: 'Try again' }).click();
  await expect(page.getByRole('heading', { name: 'Nothing else to do here yet' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Your learning record' })).toHaveCount(0);
  await expect(page.locator('.today-page .btn-primary')).toHaveCount(0);
});
test('mentor waiting and correction do not imply mastery', async ({ page }) => {
  let correction = false;
  await page.route('**/api/v2/curriculum', (route) => {
    const current = { ...fixture.current, progress: { ...fixture.progress, status: correction ? 'needs_correction' : 'awaiting_mentor_review' }, continue: { ...fixture.continuation, kind: correction ? 'correction' : 'review_pending', route: '/learning-v2/modules/module.aplus.core1.ip_configuration' } };
    return route.fulfill({ json: { success: true, data: { current, modules: [current], corrections: [] } } });
  });
  await signIn(page, 'v2', false);
  await expect(page.getByRole('heading', { name: 'Learning is up to date' })).toBeVisible();
  await expect(page.getByRole('complementary', { name: 'Mentor follow-up' })).toContainText('With your mentor');
  await expect(page.locator('.today-page .btn-primary')).toHaveCount(0);
  correction = true;
  await page.reload();
  await expect(page.getByRole('link', { name: 'Update your practical' })).toHaveCount(1);
  await expect(page.locator('.today-page')).not.toContainText('Stage mastered');
});
test('reduced motion and keyboard skip link', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce', colorScheme: 'dark' });
  await signIn(page);
  await expect(page.locator('html')).toHaveClass('dark');
  await page.locator('.academy-skip-link').focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#app-main')).toBeFocused();
  expect(await page.locator('.today-primary-action').evaluate((el) => getComputedStyle(el).transitionDuration)).toBe('0s');
});


if (process.env.NEXUS_PHASE1_BASELINE_DIR) {
  for (const theme of ['light', 'dark']) {
    test(`before Today ${theme} 1440 from verified main`, async ({ page }) => {
      await page.addInitScript((mode) => localStorage.setItem('theme', mode), theme);
      await signIn(page, 'v2', true, 'http://127.0.0.1:5818');
      await page.screenshot({ path: `${gallery}/before-${theme}-1440.png`, fullPage: true });
    });
  }
}
