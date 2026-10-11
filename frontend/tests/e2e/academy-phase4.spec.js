import { expect, test } from '@playwright/test';
import { mkdirSync } from 'node:fs';

// Real same-origin Academy + Next.js Service Desk + disposable API stack.
// Run after p1 workspace + pr9b workflow tests, before p0 completes INC2504.
const moduleKey = 'module.aplus.core1.printers_mfds';
const moduleRoute = `/learning-v2/modules/${moduleKey}`;
const captureDir = process.env.NEXUS_ACADEMY_CAPTURE;

async function login(page, role = 'A') {
  const base = process.env.NEXUS_E2E_BASE_URL;
  if (!base || !['127.0.0.1', 'localhost'].includes(new URL(base).hostname)) {
    throw Error('Explicit disposable same-origin loopback stack required');
  }
  await page.goto('/login');
  await page.getByLabel('Username', { exact: true }).fill(process.env[`NEXUS_E2E_STUDENT_${role}_USERNAME`]);
  await page.getByLabel('Password', { exact: true }).fill(process.env[`NEXUS_E2E_STUDENT_${role}_PASSWORD`]);
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
}
async function ready(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map(image => image.decode().catch(() => {})));
  });
}
async function capture(page, name) {
  if (!captureDir) return;
  mkdirSync(captureDir, { recursive: true });
  await ready(page);
  await page.screenshot({ path: `${captureDir}/${name}.png`, fullPage: true });
}
async function theme(page, value) {
  const toggle = page.getByRole('button', { name: 'Toggle dark mode', exact: true });
  if ((await toggle.getAttribute('aria-pressed')) !== String(value === 'dark') || await page.evaluate(() => localStorage.getItem('theme')) !== value) {
    await toggle.click();
    if ((await toggle.getAttribute('aria-pressed')) !== String(value === 'dark')) await toggle.click();
  }
  await expect(page.locator('html')).toHaveAttribute('data-theme', value);
  await expect.poll(() => page.evaluate(() => localStorage.getItem('theme'))).toBe(value);
}
async function launch(page) {
  await page.goto(moduleRoute);
  await page.getByRole('link', { name: 'Troubleshoot a ticket', exact: true }).click();
  await expect.poll(async () =>
    await page.getByTestId('ticket-workspace').isVisible() ||
    await page.getByRole('button', { name: 'Open ticket', exact: true }).isVisible(),
  { timeout: 30_000 }).toBe(true);
  if (await page.getByRole('button', { name: 'Open ticket', exact: true }).isVisible()) {
    await page.getByRole('button', { name: 'Open ticket', exact: true }).click();
  }
  await expect(page.getByTestId('ticket-workspace')).toBeVisible();
}
async function noOverflow(page, width) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width + 1);
}

test('Phase 4 guided presentation uses live ticket, server evidence, persistent theme and responsive navigation', async ({ page }) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await login(page);
  await launch(page);
  await expect(page.locator('.sd-academy')).toBeVisible();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('My drawing packets are not printing');
  await expect(page.getByText('Guided Practice', { exact: true })).toBeVisible();
  const launchUrl = page.url();
  await page.keyboard.press('Control+k');
  const search = page.getByRole('searchbox', { name: 'Search lessons or commands' });
  await expect(search).toBeFocused();
  const response = page.waitForResponse(res => res.url().includes('/api/search/global?q=printer'));
  await search.fill('printer');
  expect((await response).ok()).toBe(true);
  await expect(page.getByRole('region', { name: 'Search results' }).getByRole('link').first()).toBeVisible();
  await search.fill('');
  await page.keyboard.press('Escape');
  for (const width of [1440, 1280, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
    for (const mode of ['light', 'dark']) {
      await theme(page, mode);
      await page.evaluate(() => window.scrollTo(0, 0));
      await noOverflow(page, width);
      await capture(page, `ticket-${mode}-${width}`);
    }
  }
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await page.getByRole('tab', { name: /Evidence/ }).click();
    await expect(page.getByText('Confirmed by your actions', { exact: true })).toBeVisible();
    await expect(page.getByText('Related device', { exact: true })).toBeVisible();
    await noOverflow(page, width);
    await page.getByRole('tab', { name: 'Notes', exact: true }).click();
    const field = page.getByLabel('Add a note');
    await field.fill('Draft observations — the requester reports a printing problem; investigate the destination before any change.');
    await page.getByRole('tab', { name: 'Work', exact: true }).click();
    await page.getByRole('tab', { name: 'Notes', exact: true }).click();
    await expect(field).toHaveValue(/Draft observations/);
    await noOverflow(page, width);
    await field.evaluate(element => element.scrollIntoView({ block: 'center' }));
    expect((await field.boundingBox()).y + (await field.boundingBox()).height).toBeLessThan(844 - 65);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await theme(page, 'light');
  await capture(page, 'ticket-notes-mobile-light');
  await theme(page, 'dark');
  await capture(page, 'ticket-notes-mobile-dark');
  await page.reload();
  await expect(page.getByTestId('ticket-workspace')).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.setViewportSize({ width: 1440, height: 1000 });
  const toggle = page.getByRole('button', { name: 'Toggle dark mode', exact: true });
  await toggle.focus();
  await page.keyboard.press('Space');
  await expect(toggle).toHaveAttribute('aria-pressed', 'false');
  await expect(toggle).toBeFocused();
  await page.goto(launchUrl);
  await expect(page.getByTestId('ticket-workspace')).toBeVisible();
  await page.getByRole('link', { name: 'Back to your module', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`${moduleKey}$`));
  await page.goBack();
  await expect(page.getByTestId('ticket-workspace')).toBeVisible();
});

test('Phase 4 queue and completed result show actual server outcome', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await login(page);
  await page.goto('/service-desk');
  await expect(page.getByRole('heading', { name: 'Ticket queue', exact: true })).toBeVisible();
  for (const mode of ['light', 'dark']) {
    await theme(page, mode);
    await capture(page, `ticket-queue-${mode}`);
  }
  await page.goto('/service-desk/tickets/INC2501');
  await expect(page.getByRole('heading', { name: /Assessment result: PASS/ })).toBeVisible();
  // The pr9b real UI workflow earned this grade; answering or saving text cannot create it.
  for (const mode of ['light', 'dark']) {
    await theme(page, mode);
    await capture(page, `ticket-result-${mode}`);
  }
  await page.setViewportSize({ width: 320, height: 844 });
  await noOverflow(page, 320);
});


test('Phase 4 general notes preserve natural language without awarding credit and survive reload', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await login(page, 'D');
  const assignmentsResponse = await page.request.get('/api/service-desk/assignments');
  expect(assignmentsResponse.ok()).toBe(true);
  const assignments = await assignmentsResponse.json();
  const assignment = assignments.find(row => row.workspace_view?.documentation_target === 'ticket' && /^inc[0-9]+$/i.test(row.scenario.stable_key) && row.most_recent_attempt?.status !== 'completed');
  expect(assignment, 'An actual available general-note assignment is required').toBeTruthy();
  await page.goto(`/service-desk/tickets/${assignment.scenario.stable_key.toUpperCase()}`);
  if (await page.getByRole('button', { name: 'Open ticket', exact: true }).isVisible()) await page.getByRole('button', { name: 'Open ticket', exact: true }).click();
  await expect(page.getByTestId('ticket-workspace')).toBeVisible();
  const summary = async () => {
    const response = await page.request.get('/api/service-desk/progress-summary');
    expect(response.ok()).toBe(true);
    return response.json();
  };
  const before = await summary();
  const issue = assignment.latest_published_version.definition_json.description.issue;
  const wording = `I recorded the requester’s report: ${issue} I still need to investigate before drawing a conclusion.`;
  await page.getByLabel('Add a note').fill(wording);
  const saved = page.waitForResponse(response => /\/api\/service-desk\/attempts\/\d+\/actions$/.test(response.url()) && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Add internal note', exact: true }).click();
  expect((await saved).status()).toBe(201);
  await expect(page.getByLabel('Add a note')).toHaveValue('');
  await expect(page.locator('.sd-note-panel')).toContainText(wording);
  await page.reload();
  await expect(page.locator('.sd-note-panel')).toContainText(wording);
  const after = await summary();
  expect(after.total_xp).toBe(before.total_xp);
  expect(after.tickets_completed).toBe(before.tickets_completed);
  await expect(page.getByTestId('ticket-workspace')).toBeVisible();
  for (const mode of ['light', 'dark']) {
    await theme(page, mode);
    await capture(page, `ticket-note-saved-${mode}`);
  }
});


test('Phase 4 missing session returns to login and denies ticket API access', async ({ page, context }) => {
  await login(page);
  await page.goto('/service-desk');
  await expect(page.getByRole('heading', { name: 'Ticket queue', exact: true })).toBeVisible();
  await context.clearCookies();
  await page.reload();
  await expect(page).toHaveURL(/\/login\?next=/);
  const response = await page.request.get('/api/service-desk/assignments');
  expect(response.status()).toBe(401);
  await expect(page.locator('.sd-academy')).toHaveCount(0);
});
