import { expect, test, type Page } from '@playwright/test';

const visualRoot = 'docs/visual-qa/service-desk-workstation';

async function connect(page: Page, ticketId: string, assetTag: string) {
  await page.goto(`/tools/remote-desktop?ticket=${ticketId}`);
  const workstation = page
    .getByText(assetTag, { exact: true })
    .locator('..')
    .locator('..');
  await workstation
    .getByRole('button', { name: 'Connect', exact: true })
    .click();
  await expect(page.getByText('Remote Login', { exact: true })).toBeVisible();
  const credentials = page.locator('input');
  await credentials.nth(0).fill('student');
  await credentials.nth(1).fill('password');
  await page.getByRole('button', { name: 'OK', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Open Start menu' }),
  ).toBeVisible();
}

async function openApp(page: Page, name: string) {
  await page.getByRole('button', { name: 'Open Start menu' }).click();
  await page.getByRole('button', { name, exact: true }).last().click();
  await expect(page.getByLabel(`${name} window`)).toBeVisible();
}

test('captures the desktop mapped-drive workflow', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await connect(page, 'INC2405', 'NX-6128');
  await openApp(page, 'File Explorer');
  await page
    .getByRole('button', { name: /Open Facilities Calendar \(Y:\)/ })
    .click();
  await page.getByRole('button', { name: 'Open Map Network Drive' }).click();
  await expect(
    page.getByRole('dialog', { name: 'Map Network Drive' }),
  ).toBeVisible();
  await page.screenshot({
    fullPage: true,
    path: `${visualRoot}/desktop-mapped-drive-dialog.png`,
  });
});

test('captures terminal and VPN state on the Windows-inspired desktop', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await connect(page, 'INC2406', 'NX-2047');
  await openApp(page, 'Command Prompt');
  const terminal = page.getByLabel('Terminal command');
  await terminal.fill('ipconfig /all');
  await terminal.press('Enter');
  await openApp(page, 'VPN Client');
  await page.getByRole('button', { name: 'Connect', exact: true }).click();
  await expect(
    page.getByText('Connected', { exact: true }).last(),
  ).toBeVisible();
  await page.screenshot({
    fullPage: true,
    path: `${visualRoot}/desktop-vpn-terminal.png`,
  });
});

test('captures Directory evidence and the training-safe password reset', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/tools/directory');
  await page
    .getByPlaceholder('Search name, username, or department')
    .fill('Jordan Lee');
  await page.getByRole('button', { name: /^Jordan Lee/ }).click();
  await page.getByRole('button', { name: 'Review account state' }).click();
  await page.goto(
    '/tools/company-chat?contact=directory-user-jordan-lee&ticket=INC2512',
  );
  await page
    .getByRole('button', { name: 'Run approved identity check' })
    .click();
  await page.goto('/tools/directory');
  await page
    .getByPlaceholder('Search name, username, or department')
    .fill('Jordan Lee');
  await page.getByRole('button', { name: /^Jordan Lee/ }).click();
  await page
    .getByRole('button', { name: 'Record verified chat evidence' })
    .click();
  await page.getByLabel('Account diagnosis').selectOption('password-expired');
  await page.getByRole('button', { name: 'Record diagnosis' }).click();
  await page.getByRole('button', { name: 'Reset password' }).click();
  await expect(
    page.getByRole('dialog', { name: 'Reset password' }),
  ).toBeVisible();
  await page.screenshot({
    fullPage: true,
    path: `${visualRoot}/desktop-directory-password-reset.png`,
  });
});

test('captures and validates the 375 by 812 workstation fallback', async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await connect(page, 'INC2406', 'NX-2047');
  await openApp(page, 'File Explorer');
  await expect(page.getByLabel('File Explorer window')).toBeVisible();
  await page.getByRole('button', { name: 'Ticket workspace' }).click();
  expect(await page.evaluate(() => window.innerWidth)).toBe(375);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    fullPage: true,
    path: `${visualRoot}/mobile-file-explorer-375x812.png`,
  });
});
