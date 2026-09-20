// Run only on the disposable stack from scripts/e2e/start_local_stack.sh.
// All investigation and repair actions go through the browser simulator UI.
import { expect, test } from '@playwright/test';
import fs from 'node:fs';

const moduleKey = 'module.aplus.core1.printers_mfds';
const assessmentKey = 'assess.aplus-core1-printers-mfds.service_desk';
const returnTo = `/learning-v2/modules/${moduleKey}`;
const trace = JSON.parse(fs.readFileSync(new URL('../../../service-desk-app/packages/shared/src/realism-traces.test.json', import.meta.url))).INC2504;

test('P0 authenticated beginner: curriculum launcher, trusted work, note rejection and V2 credit', async ({ page }) => {
  test.setTimeout(180_000);
  const base = process.env.NEXUS_E2E_BASE_URL;
  if (!base || !['127.0.0.1', 'localhost'].includes(new URL(base).hostname)) throw new Error('A disposable loopback E2E stack is required');
  await page.goto('/login');
  await page.getByLabel('Username').fill(process.env.NEXUS_E2E_STUDENT_A_USERNAME);
  await page.getByLabel('Password').fill(process.env.NEXUS_E2E_STUDENT_A_PASSWORD);
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto(returnTo);
  await page.getByRole('link', { name: 'Troubleshoot a ticket' }).click();
  await expect(page).toHaveURL(/\/service-desk\/tickets\/INC2504\?/);
  const assertContext = () => {
    const url = new URL(page.url());
    expect(url.searchParams.get('returnTo')).toBe(returnTo);
    expect(url.searchParams.get('v2ModuleKey')).toBe(moduleKey);
    expect(url.searchParams.get('v2AssessmentKey')).toBe(assessmentKey);
  };
  assertContext();
  await expect(page.getByRole('heading', { name: 'Before you open the ticket' })).toBeVisible();
  await page.getByRole('button', { name: 'Open ticket', exact: true }).click();
  await expect(page.getByRole('combobox', { name: /status/i })).toHaveCount(0);
  await page.getByRole('navigation', { name: 'Suggested tools' }).getByRole('button', { name: 'Remote Desktop', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Remote Desktop', exact: true })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Choose a ticket' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Connect', exact: true })).toHaveCount(1);
  expect(new URL(page.url()).searchParams.get('ticket')).toBe('INC2504');
  assertContext();
  await page.getByRole('button', { name: 'Connect', exact: true }).click();
  await expect.poll(async () => (await page.getByText('Remote Login', { exact: true }).isVisible()) || (await page.getByRole('button', { name: 'Open Start menu' }).isVisible())).toBe(true);
  if (await page.getByText('Remote Login', { exact: true }).isVisible()) {
    // Simulator credentials are educational input, not an external account.
    await page.locator('input').filter({ visible: true }).nth(0).fill('student');
    await page.locator('input').filter({ visible: true }).nth(1).fill('password');
    await page.getByRole('button', { name: 'OK', exact: true }).click();
  }
  if (!await page.getByLabel('Terminal command').isVisible()) {
    await page.getByRole('button', { name: 'Open Start menu' }).click();
    await page.getByRole('button', { name: 'Command Prompt', exact: true }).last().click();
  }
  await page.getByLabel('Terminal command').fill(trace.commands[0]);
  await page.getByLabel('Terminal command').press('Enter');
  await expect(page.getByText('Confirmed by your actions', { exact: true })).toBeVisible();
  await expect(page.locator('[aria-label="Ticket workspace rail"]')).toContainText('Spooler');
  await page.getByRole('button', { name: 'Back to ticket INC2504', exact: true }).click();
  assertContext();
  const incomplete = '  Restarted computer and issue resolved.  ';
  await page.getByLabel('Add a note').fill(incomplete);
  await page.getByRole('button', { name: 'Add internal note', exact: true }).click();
  await expect(page.getByLabel('Add a note')).toHaveValue(incomplete);
  await expect(page.locator('[aria-label="Ticket workspace rail"]').getByRole('alert')).toContainText('what you tested and what happened');
  await page.getByRole('navigation', { name: 'Suggested tools' }).getByRole('button', { name: 'Remote Desktop', exact: true }).click();
  // The remote session survives returning to the ticket; reopen its desktop.
  const connect = page.getByRole('button', { name: 'Connect', exact: true });
  if (await connect.isVisible()) await connect.click();
  if (!await page.getByLabel('Terminal command').isVisible()) {
    await page.getByRole('button', { name: 'Open Start menu' }).click();
    await page.getByRole('button', { name: 'Command Prompt', exact: true }).last().click();
  }
  await expect(page.getByLabel('Terminal command')).toBeVisible();
  for (const command of trace.commands.slice(1)) {
    await page.getByLabel('Terminal command').fill(command);
    await page.getByLabel('Terminal command').press('Enter');
  }
  await page.getByRole('button', { name: 'Back to ticket INC2504', exact: true }).click();
  await page.getByLabel('Add a note').fill(trace.note);
  await page.getByRole('button', { name: 'Add internal note', exact: true }).click();
  await expect(page.getByLabel('Add a note')).toHaveValue('');
  await page.getByRole('button', { name: 'Resolve', exact: true }).click();
  await page.getByLabel('I verified the requester has a working outcome').check();
  await page.getByRole('button', { name: 'Continue to review' }).click();
  await page.getByRole('button', { name: 'Resolve ticket', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Assessment result: PASS — module credit earned.', exact: true })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText('Attempts remaining:', { exact: false })).toHaveCount(0);
  await expect(page.getByText('2 attempts remaining', { exact: true })).toBeVisible();
  assertContext();
  const response = await page.request.get(`/api/v2/curriculum/modules/${moduleKey}`);
  expect(response.ok()).toBeTruthy();
  const { data: module } = await response.json();
  expect(module.progress.service_desk.activity.status).toBe('passed');
  expect(module.progress.service_desk.activity.passed).toBe(true);
  expect(module.assessments.find(a => a.key === assessmentKey).progress.status).toBe('passed');
  // The ticket earns its activity credit; it cannot complete untouched lessons.
  expect(module.progress.module_complete).toBe(false);
  await page.getByRole('link', { name: 'Back to your module', exact: true }).last().click();
  await expect(page).toHaveURL(new RegExp(`/learning-v2/modules/${moduleKey}$`));
});
