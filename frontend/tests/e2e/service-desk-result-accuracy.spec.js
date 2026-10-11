import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';

const trace = JSON.parse(
  readFileSync(
    new URL(
      '../../../service-desk-app/packages/shared/src/realism-traces.test.json',
      import.meta.url,
    ),
    'utf8',
  ),
).INC2501;

async function login(page) {
  const base = process.env.NEXUS_E2E_BASE_URL;
  if (!base || !['localhost', '127.0.0.1'].includes(new URL(base).hostname)) {
    throw new Error('A disposable loopback stack is required');
  }
  await page.goto('/login');
  await page.getByLabel('Username').fill(process.env.NEXUS_E2E_STUDENT_A_USERNAME);
  await page.getByLabel('Password').fill(process.env.NEXUS_E2E_STUDENT_A_PASSWORD);
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
}

async function summary(page) {
  const response = await page.request.get('/api/service-desk/progress-summary');
  expect(response.ok()).toBe(true);
  return response.json();
}
async function captureResults(page, prefix) {
  for (const mode of ['light', 'dark']) {
    const toggle = page.getByRole('button', { name: 'Toggle dark mode', exact: true });
    if ((await toggle.getAttribute('aria-pressed')) !== String(mode === 'dark')) await toggle.click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', mode);
    const captureDir = process.env.NEXUS_RESULT_CAPTURE || process.env.NEXUS_PHASE5_CAPTURE;
    if (captureDir) {
      await page.evaluate(async () => {
        await document.fonts.ready;
        await Promise.all([...document.images].map(image => image.decode().catch(() => {})));
      });
      await page.screenshot({ path: `${captureDir}/${prefix}-${mode}.png`, fullPage: !process.env.NEXUS_PHASE5_CAPTURE });
    }
  }
}

test('historical assessment and real practice report server-owned modes without new rewards', async ({ page }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await login(page);
  const before = await summary(page);
  const listed = await page.request.get('/api/service-desk/assignments');
  expect(listed.ok()).toBe(true);
  const assignment = (await listed.json()).find(row => row.scenario.stable_key === 'inc2501' && row.mode === 'simulation');
  expect(assignment.experience_mode).toBe('practice');
  expect(assignment.most_recent_attempt.experience_mode).toBe('assessment');
  await page.goto('/service-desk/tickets/INC2501');
  await expect(page.getByRole('heading', { name: 'Assessment result: PASS — check Academy for awarded credit.' })).toBeVisible();
  await expect(page.locator('.sd-ticket-heading').getByText('Independent assessment', { exact: true })).toBeVisible();
  await expect(page.locator('.sd-ticket-debrief')).not.toContainText('module credit earned');
  await expect(page.getByText('Ticket status').locator('.sd-badge')).toHaveText('Resolved');
  await captureResults(page, 'ticket-result');
  expect((await summary(page)).total_xp).toBe(before.total_xp);
  // Start an actual optional replay through the existing authenticated API;
  // every diagnostic, note and closure still uses the real simulator UI.
  const started = await page.request.post(`/api/service-desk/assignments/${assignment.id}/attempts`, {
    headers: { 'X-Nexus-Service-Desk-Contract': '2.0', Origin: process.env.NEXUS_E2E_BASE_URL },
  });
  expect(started.status(), await started.text()).toBe(201);
  const practiceId = (await started.json()).id;
  await page.reload();
  await expect(page.getByTestId('ticket-workspace')).toBeVisible();
  await expect(page.locator('.sd-ticket-heading').getByText('Practice', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'All tools', exact: true }).click();
  await page
    .getByRole('navigation', { name: 'Workspace tools' })
    .getByRole('button', { name: 'Remote Desktop', exact: true })
    .click();
  await page.getByPlaceholder('Search by asset tag, hostname, or owner').fill('NX-2501');
  await page.getByRole('button', { name: 'Connect', exact: true }).click();
  const start = page.getByRole('button', { name: 'Open Start menu' });
  const username = page.getByPlaceholder('e.g. jdoe');
  await expect(username.or(start)).toBeVisible();
  if (await username.isVisible()) {
    await username.fill('support.admin');
    await page.getByPlaceholder('Domain password').fill('simulation-only');
    await page.getByRole('button', { name: 'OK', exact: true }).click();
  }
  await start.click();
  await page.getByRole('button', { name: 'Command Prompt', exact: true }).last().click();
  const commandInput = page.getByLabel('Terminal command');
  for (const command of trace.commands) {
    await commandInput.fill(command);
    const confirmed = page.waitForResponse((response) =>
      /\/api\/service-desk\/attempts\/[^/]+\/actions$/.test(response.url()) &&
      response.request().method() === 'POST',
    );
    await commandInput.press('Enter');
    expect((await confirmed).ok()).toBe(true);
  }

  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByRole('tab', { name: /Evidence/ }).click();
  await expect(page.getByText('Confirmed by your actions')).toBeVisible();
  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByRole('tab', { name: 'Notes', exact: true }).click();
  await expect(page.getByLabel('Add a note')).toBeVisible();

  await page.getByLabel('Add a note').fill(trace.note);
  await page.getByRole('button', { name: 'Add internal note' }).click();
  await expect(page.getByLabel('Add a note')).toHaveValue('');
  await page.getByRole('button', { name: 'Resolve', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Resolve or close ticket' });
  await expect(dialog).toContainText(trace.note);
  await dialog.getByRole('checkbox').check();
  await dialog.getByRole('button', { name: 'Continue to review' }).click();
  await expect(dialog.getByText('Requester confirmation selected')).toBeVisible();
  await dialog.getByRole('button', { name: 'Resolve ticket' }).click();
  await expect(page.getByRole('heading', { name: /Practice result: PASS/ })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText('Ticket status').locator('.sd-badge')).toHaveText('Resolved');
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Practice result: PASS — no assessment credit or mastery XP.' })).toBeVisible();
  await expect(page.locator('.sd-ticket-heading').getByText('Practice', { exact: true })).toBeVisible();
  const attemptResponse = await page.request.get(`/api/service-desk/attempts/${practiceId}`);
  expect(attemptResponse.ok()).toBe(true);
  const attempt = await attemptResponse.json();
  expect(attempt.experience_mode).toBe('practice');
  expect(attempt.grade.passed).toBe(true);
  await expect(page.getByText('Ticket status').locator('.sd-badge')).toHaveText('Resolved');
  const after = await summary(page);
  expect(after.total_xp).toBe(before.total_xp);
  expect(after.tickets_completed).toBe(before.tickets_completed);
  await captureResults(page, 'ticket-practice-result');
  const afterRender = await summary(page);
  expect(afterRender.total_xp).toBe(after.total_xp);
  expect(afterRender.tickets_completed).toBe(after.tickets_completed);
});
