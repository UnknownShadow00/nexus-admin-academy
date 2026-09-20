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
  await page.getByRole('button', { name: 'Open Start menu' }).click();
  await page.getByRole('button', { name, exact: true }).last().click();
  await expect(page.getByLabel(`Close ${name}`)).toBeVisible();
}

async function runTerminalCommand(page: Page, command: string) {
  const terminal = page.getByLabel('Terminal command');
  await terminal.fill(command);
  await terminal.press('Enter');
}

async function saveNoteAndClose(
  page: Page,
  ticketId: string,
  screenshotPath?: string,
) {
  // Documentation lives only in the unified ticket workspace. Resolve reads
  // that note and must never render a second editable note control.
  await page.goto(`/tickets/${ticketId}`);
  const noteInput = page.getByLabel('Add a note');
  await expect(noteInput).toHaveCount(1);
  await noteInput.fill(completionNote);
  await page.getByRole('button', { name: 'Add internal note' }).click();

  await page.getByRole('button', { name: 'Resolve', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Resolve or close ticket' });
  await expect(dialog.getByRole('textbox')).toHaveCount(0);
  await expect(dialog.getByText(completionNote, { exact: true })).toBeVisible();
  await dialog.getByRole('checkbox').check();
  await dialog.getByRole('button', { name: 'Continue to review' }).click();
  await expect(dialog.getByText('Ready to resolve')).toBeVisible();
  await dialog.getByRole('button', { name: 'Resolve ticket' }).click();
  await expect(
    page
      .getByText(ticketId, { exact: true })
      .locator('..')
      .getByText('Resolved', { exact: true }),
  ).toBeVisible();
  if (screenshotPath) {
    await page.screenshot({ fullPage: true, path: screenshotPath });
  }
}

async function confirmResolutionWithRequester(
  page: Page,
  contactId: string,
  ticketId: string,
  assetTag: string,
) {
  await page.goto(
    `/tools/company-chat?contact=${contactId}&ticket=${ticketId}`,
  );
  await page
    .getByRole('button', { name: 'Ask user to retest original symptom' })
    .click();
  await expect(
    page.getByText('It now works and I can continue.', { exact: false }),
  ).toHaveCount(2);
  await page.goBack();
  await expect(page).toHaveURL(
    new RegExp(
      `/tools/remote-desktop\\?.*ticket=${ticketId}.*computer=${assetTag}`,
    ),
  );
  await expect(
    page.getByRole('button', { name: 'Disconnect' }).first(),
  ).toBeVisible();
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

  await openDesktopApp(page, 'Command Prompt');
  await runTerminalCommand(page, 'ipconfig /all');
  await runTerminalCommand(page, 'ping partner.nexus.internal');
  await expect(
    page.getByText('Ping request could not find host partner.nexus.internal.', {
      exact: false,
    }),
  ).toBeVisible();

  await openDesktopApp(page, 'VPN Client');
  await page.getByRole('button', { name: 'Connect', exact: true }).click();
  await expect(
    page.getByText('Connected', { exact: true }).last(),
  ).toBeVisible();

  await page.getByRole('button', { name: 'Focus Command Prompt' }).click();
  await runTerminalCommand(page, 'ping partner.nexus.internal');
  await expect(
    page.getByText(/Reply from 10\.90\.20\.15/).last(),
  ).toBeVisible();

  await page.getByRole('button', { name: 'Focus File Explorer' }).click();
  await expect(page.getByLabel('File Explorer window')).toBeVisible();
  await page.getByRole('button', { name: 'This PC', exact: true }).click();
  await page
    .getByRole('button', { name: 'Open Partner Workspace (Z:)' })
    .click();
  await expect(
    page.getByText('Network path unavailable', { exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Open Map Network Drive' }).click();
  const mapDialog = page.getByRole('dialog', { name: 'Map Network Drive' });
  await mapDialog.getByRole('combobox').first().selectOption('Z:');
  await mapDialog
    .getByRole('textbox')
    .fill('\\\\partner.nexus.internal\\workspace');
  await mapDialog.getByRole('button', { name: 'Finish', exact: true }).click();
  await expect(
    page.getByText('Partner Workspace', { exact: true }),
  ).toBeVisible();

  await confirmResolutionWithRequester(
    page,
    'directory-user-harper-kim',
    'INC2406',
    'NX-2047',
  );
  await saveNoteAndClose(
    page,
    'INC2406',
    'docs/visual-qa/service-desk-workstation/desktop-grading-complete.png',
  );
  expect(pageErrors).toEqual([]);
});

test('maps the Facilities calendar with an exact persistent UNC configuration', async ({
  page,
}) => {
  const pageErrors = await connectToWorkstation(page, 'INC2405', 'NX-6128');

  await openDesktopApp(page, 'Command Prompt');
  await runTerminalCommand(page, 'net use');

  await openDesktopApp(page, 'File Explorer');
  await page
    .getByRole('button', { name: /Open Facilities Calendar \(Y:\)/ })
    .click();
  await expect(
    page.getByText('Network path unavailable', { exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Open Map Network Drive' }).click();
  const mapDialog = page.getByRole('dialog', { name: 'Map Network Drive' });
  await mapDialog.getByRole('combobox').first().selectOption('Y:');
  await mapDialog
    .getByRole('textbox')
    .fill('\\\\facilities.nexus.internal\\calendar');
  await expect(mapDialog.getByRole('checkbox')).toBeChecked();
  await mapDialog.getByRole('button', { name: 'Finish', exact: true }).click();

  await page.getByRole('button', { name: 'This PC', exact: true }).click();
  await page
    .getByRole('button', { name: /Open Facilities Calendar \(Y:\)/ })
    .click();
  await expect(
    page.getByText('Facilities Calendar', { exact: true }),
  ).toBeVisible();

  await confirmResolutionWithRequester(
    page,
    'directory-user-sloane-rivera',
    'INC2405',
    'NX-6128',
  );
  await saveNoteAndClose(page, 'INC2405');
  expect(pageErrors).toEqual([]);
});

test('completes the DNS ticket through the desktop', async ({ page }) => {
  const pageErrors = await connectToWorkstation(page, 'INC2407', 'NX-8892');

  await openDesktopApp(page, 'Command Prompt');
  await runTerminalCommand(page, 'ipconfig');
  await runTerminalCommand(page, 'ping 10.20.0.10');
  await runTerminalCommand(page, 'nslookup portal.nexus.internal');

  await openDesktopApp(page, 'Settings');
  await page.getByLabel('Primary DNS server').fill('10.20.0.10');
  await page.getByLabel('Secondary DNS server').fill('10.20.0.11');
  await page.getByRole('button', { name: 'Save DNS settings' }).click();

  await page.getByRole('button', { name: 'Focus Command Prompt' }).click();
  await runTerminalCommand(page, 'nslookup portal.nexus.internal');

  await saveNoteAndClose(page, 'INC2407');
  expect(pageErrors).toEqual([]);
});

test('completes the Print Spooler ticket through the desktop', async ({
  page,
}) => {
  const pageErrors = await connectToWorkstation(page, 'INC2408', 'NX-4419');

  await openDesktopApp(page, 'System Information');
  await page.getByRole('button', { name: 'Print simulated test page' }).click();
  await expect(page.getByText('The simulated test page')).toContainText(
    'failed',
  );

  await openDesktopApp(page, 'Services');
  await page
    .getByRole('button', { name: 'Print Spooler', exact: true })
    .click();
  await page.getByRole('button', { name: 'Start', exact: true }).click();

  await page.getByRole('button', { name: 'Focus System Information' }).click();
  await page.getByRole('button', { name: 'Print simulated test page' }).click();
  await expect(page.getByText('The simulated test page')).toContainText(
    'successfully',
  );

  await saveNoteAndClose(page, 'INC2408');
  expect(pageErrors).toEqual([]);
});
