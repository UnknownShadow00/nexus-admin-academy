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

async function capture(page, name) {
  const directory = process.env.NEXUS_PR9B_SCREENSHOTS;
  if (directory) {
    await page.screenshot({ path: `${directory}/${name}.png`, fullPage: true });
  }
}

async function captureResponsive(page, name) {
  if (!process.env.NEXUS_PR9B_SCREENSHOTS) return;
  const sizes = name.includes('document') || name.includes('resolve')
    ? [[1440, 900], [768, 900], [375, 812]]
    : [[1440, 900], [375, 812]];
  for (const [width, height] of sizes) {
    await page.setViewportSize({ width, height });
    for (const theme of ['light', 'dark']) {
      await page.evaluate((value) => {
        localStorage.setItem('theme', value);
        document.documentElement.dataset.theme = value;
      }, theme);
      await capture(page, `${name}-${width}-${theme}`);
    }
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => {
    localStorage.setItem('theme', 'light');
    document.documentElement.dataset.theme = 'light';
  });
}

test('independent INC2501 completes all six stages with server PASS and separate ticket status', async ({ page, browser }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page);
  await page.goto('/service-desk/tickets/INC2501');
  await expect(page.getByText('Independent assessment', { exact: true })).toBeVisible();
  await expect(page.getByText('Hints', { exact: true })).toHaveCount(0);
  await expect(page.getByTestId('ticket-workspace')).toBeVisible();
  await captureResponsive(page, 'independent-understand');

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
  for (const [index, command] of trace.commands.entries()) {
    await commandInput.fill(command);
    const confirmed = page.waitForResponse((response) =>
      /\/api\/service-desk\/attempts\/[^/]+\/actions$/.test(response.url()) &&
      response.request().method() === 'POST',
    );
    await commandInput.press('Enter');
    expect((await confirmed).ok()).toBe(true);
    if ([0, 4, 5, 8, 10].includes(index)) {
      await captureResponsive(page, `independent-command-${index + 1}`);
    }
  }

  await page.getByLabel('Add a note').fill(trace.note);
  await page.getByRole('button', { name: 'Add internal note' }).click();
  await expect(page.getByLabel('Add a note')).toHaveValue('');
  await captureResponsive(page, 'independent-document');
  await page.getByRole('button', { name: 'Resolve', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Resolve or close ticket' });
  await expect(dialog).toContainText(trace.note);
  await dialog.getByRole('checkbox').check();
  await dialog.getByRole('button', { name: 'Continue to review' }).click();
  await expect(dialog.getByText('Requester confirmation selected')).toBeVisible();
  await captureResponsive(page, 'independent-resolve-review');
  await dialog.getByRole('button', { name: 'Resolve ticket' }).click();
  await expect(page.getByRole('heading', { name: /Assessment result: PASS/ })).toBeVisible({ timeout: 30_000 });
  await captureResponsive(page, 'independent-pass');

  await page.reload();
  await expect(page.getByRole('heading', { name: /Assessment result: PASS/ })).toBeVisible();
  await expect(page.getByText('Ticket status').locator('.sd-badge')).toHaveText('Resolved');

  const revisitContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const revisit = await revisitContext.newPage();
  await login(revisit);
  await revisit.goto('/service-desk/tickets/INC2501');
  await expect(revisit.getByRole('heading', { name: /Assessment result: PASS/ })).toBeVisible();
  await expect(revisit.getByText('Ticket status').locator('.sd-badge')).toHaveText('Open');
  await capture(revisit, 'independent-historical-pass-open-1440-light');
  await revisitContext.close();
});

test('INC2509 premature mobile Resolve stays blocked with visible reason', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await login(page);
  await page.goto('/service-desk/tickets/INC2509');
  await expect(page.getByText('Independent assessment', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Resolve', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Resolve or close ticket' });
  await dialog.getByRole('checkbox').check();
  await dialog.getByRole('button', { name: 'Continue to review' }).click();
  await dialog.getByRole('button', { name: 'Resolve ticket' }).click();
  await expect(dialog.getByRole('alert')).toBeVisible();
  await expect(dialog.getByRole('alert')).not.toBeEmpty();
  await expect(page.getByRole('heading', { name: /Assessment result: PASS/ })).toHaveCount(0);
  await expect(page.getByText('Ticket status').locator('.sd-badge')).toHaveText('Open');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await capture(page, 'inc2509-mobile-resolve-validation-light');
  await page.evaluate(() => {
    localStorage.setItem('theme', 'dark');
    document.documentElement.dataset.theme = 'dark';
  });
  await capture(page, 'inc2509-mobile-resolve-validation-dark');
});
