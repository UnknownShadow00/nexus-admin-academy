import { expect, test } from '@playwright/test';

function requireDisposableStack() {
  const base = process.env.NEXUS_E2E_BASE_URL;
  if (!base || !['localhost', '127.0.0.1'].includes(new URL(base).hostname)) {
    throw new Error('A disposable loopback stack is required');
  }
}

async function login(page, username, password, admin = false) {
  requireDisposableStack();
  await page.goto(admin ? '/admin-login' : '/login');
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  await expect(page).toHaveURL(admin ? /\/admin$/ : /\/$/);
}

async function assertNoPageOverflow(page) {
  const dimensions = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    client: document.documentElement.clientWidth,
    headerScroll: document.querySelector('.topbar, .app-header')?.scrollWidth,
    headerClient: document.querySelector('.topbar, .app-header')?.clientWidth,
  }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client);
  expect(dimensions.headerScroll).toBeLessThanOrEqual(dimensions.headerClient);
}

test('approved learner sidebar and mobile navigation keep controls reachable', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page, process.env.NEXUS_E2E_STUDENT_A_USERNAME, process.env.NEXUS_E2E_STUDENT_A_PASSWORD);
  await page.evaluate(() => document.fonts.ready);

  for (const width of [1440, 1280, 1024, 900, 768, 720, 600, 480, 375, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await assertNoPageOverflow(page);
    const desktop = width >= 768;
    if (desktop) {
      await expect(page.getByRole('navigation', { name: 'Primary navigation', exact: true })).toBeVisible();
      await expect(page.getByRole('navigation', { name: 'Mobile primary navigation', exact: true })).toBeHidden();
      await expect(page.getByRole('button', { name: 'Toggle menu' })).toBeHidden();
    } else {
      await expect(page.getByRole('navigation', { name: 'Primary navigation', exact: true })).toBeHidden();
      await expect(page.getByRole('navigation', { name: 'Mobile primary navigation', exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Toggle menu' })).toBeVisible();
    }
    await expect(page.getByRole('button', { name: 'Toggle dark mode' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Account menu' })).toBeVisible();
  }

  await page.setViewportSize({ width: 375, height: 812 });
  const mobileNav = page.getByRole('navigation', { name: 'Mobile primary navigation', exact: true });
  await expect(mobileNav.getByRole('link', { name: 'Today', current: 'page' })).toBeVisible();
  for (const [label, path] of [['My Course', '/learning-v2'], ['Progress', '/skills'], ['Extra Practice', '/learning-path'], ['Today', '/']]) {
    await mobileNav.getByRole('link', { name: label }).click();
    await expect(page).toHaveURL(new URL(path, process.env.NEXUS_E2E_BASE_URL).href);
    await expect(mobileNav.getByRole('link', { name: label, current: 'page' })).toBeVisible();
    await assertNoPageOverflow(page);
  }
  await expect(mobileNav.getByRole('link', { name: 'Service Desk' })).toHaveAttribute('href', '/service-desk');

  const toggle = page.getByRole('button', { name: 'Toggle menu' });
  await toggle.click();
  await expect(page.getByRole('navigation', { name: 'All navigation', exact: true }).getByRole('link', { name: 'My Course' })).toBeVisible();
  await expect(page.locator('.mobile-nav')).toHaveAttribute('inert', '');
  await expect(page.locator('.academy-content')).toHaveAttribute('inert', '');
  await expect(page.getByRole('navigation', { name: 'Mobile primary navigation', exact: true })).toHaveCount(0);
  for (let index = 0; index < 12; index += 1) {
    await page.keyboard.press('Tab');
    const focusBehindMenu = await page.evaluate(() => Boolean(document.activeElement?.closest('.mobile-nav, .academy-content')));
    expect(focusBehindMenu).toBe(false);
  }
  await page.keyboard.press('Escape');
  await expect(toggle).toBeFocused();
  await expect(page.locator('.mobile-nav')).not.toHaveAttribute('inert', '');
});

test('learner menu restores focus on resize and compact sidebar practice links remain reachable', async ({ page }) => {
  await page.setViewportSize({ width: 720, height: 900 });
  await login(page, process.env.NEXUS_E2E_STUDENT_A_USERNAME, process.env.NEXUS_E2E_STUDENT_A_PASSWORD);
  const toggle = page.getByRole('button', { name: 'Toggle menu' });
  await expect(toggle).toBeVisible();
  await toggle.click();
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.locator('#academy-mobile-menu')).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Nexus Academy home' })).toBeFocused();
  await expect(page.getByRole('navigation', { name: 'Primary navigation', exact: true })).toBeVisible();

  await page.setViewportSize({ width: 720, height: 900 });
  await toggle.focus();
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.getByRole('link', { name: 'Nexus Academy home' })).toBeFocused();

  await page.setViewportSize({ width: 1024, height: 900 });
  await page.getByRole('button', { name: 'Extra Practice', exact: true }).click();
  const path = page.locator('#academy-practice').getByRole('link', { name: 'Practice path', exact: true });
  await expect(path).toBeVisible();
  await path.click();
  await expect(page).toHaveURL(new URL('/learning-path', process.env.NEXUS_E2E_BASE_URL).href);
  await expect(page.getByRole('heading', { name: 'Learning Path', exact: true })).toBeVisible();
  await assertNoPageOverflow(page);
});

test('admin header keeps its compact navigation and role boundary at reflow widths', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page, process.env.NEXUS_E2E_ADMIN_USERNAME, process.env.NEXUS_E2E_ADMIN_PASSWORD, true);
  await expect(page.locator('.app-header-admin')).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Primary navigation', exact: true })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Mobile primary navigation', exact: true })).toHaveCount(0);

  for (const width of [1280, 1024, 720, 375, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await assertNoPageOverflow(page);
    await expect(page.getByRole('navigation', { name: 'Primary navigation', exact: true })).toBeHidden();
    await expect(page.getByRole('button', { name: 'Toggle menu' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Toggle dark mode' })).toBeVisible();
  }

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => { document.body.style.zoom = '2'; });
  await expect(page.getByRole('navigation', { name: 'Primary navigation', exact: true })).toBeHidden();
  await assertNoPageOverflow(page);
  await page.getByRole('button', { name: 'Toggle menu' }).click();
  await expect(page.getByRole('navigation', { name: 'All navigation', exact: true }).getByRole('link', { name: /Pending Reviews/ })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'All navigation', exact: true }).getByRole('link', { name: 'Students' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'All navigation', exact: true }).getByRole('link', { name: 'My Course' })).toHaveCount(0);
});
