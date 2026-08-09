import { expect, test, type Page } from '@playwright/test';

const completionNote =
  'Diagnosis confirmed the reported service fault, applied the approved repair, and verified the service now works.';

async function connectToWorkstation(
  page: Page,
  ticketId: string,
  assetTag: string,
) {
  const pageErrors: Error[] = [];
  page.on('pageerror', (error) => pageErrors.push(error));

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

  return pageErrors;
}

async function openDesktopApp(page: Page, name: string) {
  await page.getByRole('button', { name, exact: true }).first().click();
  await expect(page.getByLabel(`Close ${name}`)).toBeVisible();
}

async function runTerminalCommand(page: Page, command: string) {
  const terminal = page.getByLabel('Terminal command');
  await terminal.fill(command);
  await terminal.press('Enter');
}

async function saveNoteAndClose(page: Page) {
  await page.getByLabel('Student-authored internal note').fill(completionNote);
  await page.getByRole('button', { name: 'Save internal note' }).click();
  const closeTicket = page.getByRole('button', { name: 'Close ticket' });
  await expect(closeTicket).toBeEnabled();
  await closeTicket.click();
  await expect(
    page.getByText('Solution complete', { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Final score:\s*100\/100/)).toBeVisible();
}

test('completes the VPN shared-drive ticket through the desktop', async ({
  page,
}) => {
  const pageErrors = await connectToWorkstation(page, 'INC2406', 'NX-2047');

  await openDesktopApp(page, 'File Explorer');
  await page
    .getByRole('button', { name: 'Open Partner Workspace (Z:)' })
    .click();
  await expect(
    page.getByText('Network path unavailable', { exact: true }),
  ).toBeVisible();

  await openDesktopApp(page, 'VPN Client');
  await page.getByRole('button', { name: 'Connect', exact: true }).click();
  await expect(
    page.getByText('Connected', { exact: true }).last(),
  ).toBeVisible();

  await page.getByRole('button', { name: 'Focus File Explorer' }).click();
  await page.getByRole('button', { name: 'This PC', exact: true }).click();
  await page
    .getByRole('button', { name: 'Open Partner Workspace (Z:)' })
    .click();
  await expect(
    page.getByText('Partner Workspace', { exact: true }),
  ).toBeVisible();

  await saveNoteAndClose(page);
  expect(pageErrors).toEqual([]);
});

test('completes the DNS ticket through the desktop', async ({ page }) => {
  const pageErrors = await connectToWorkstation(page, 'INC2407', 'NX-8892');

  await openDesktopApp(page, 'Terminal');
  await runTerminalCommand(page, 'ipconfig');
  await runTerminalCommand(page, 'ping 10.20.0.10');
  await runTerminalCommand(page, 'nslookup portal.nexus.internal');

  await openDesktopApp(page, 'Settings');
  await page.getByLabel('Primary DNS server').fill('10.20.0.10');
  await page.getByLabel('Secondary DNS server').fill('10.20.0.11');
  await page.getByRole('button', { name: 'Save DNS settings' }).click();

  await page.getByRole('button', { name: 'Focus Terminal' }).click();
  await runTerminalCommand(page, 'nslookup portal.nexus.internal');

  await saveNoteAndClose(page);
  expect(pageErrors).toEqual([]);
});

test('completes the Print Spooler ticket through the desktop', async ({
  page,
}) => {
  const pageErrors = await connectToWorkstation(page, 'INC2408', 'NX-4419');

  await openDesktopApp(page, 'System Tools');
  await page.getByRole('button', { name: 'Print simulated test page' }).click();
  await expect(page.getByText('The simulated test page')).toContainText(
    'failed',
  );

  await openDesktopApp(page, 'Services');
  await page.getByRole('button', { name: 'Print Spooler', exact: true }).click();
  await page.getByRole('button', { name: 'Start', exact: true }).click();

  await page.getByRole('button', { name: 'Focus System Tools' }).click();
  await page.getByRole('button', { name: 'Print simulated test page' }).click();
  await expect(page.getByText('The simulated test page')).toContainText(
    'successfully',
  );

  await saveNoteAndClose(page);
  expect(pageErrors).toEqual([]);
});
