import { expect, test, type Page } from '@playwright/test';

const resolutionNote =
  'Diagnosis confirmed the reported account state, applied the correct repair, and verified the original sign-in path with the requester.';

interface AccountCase {
  contactId: string;
  diagnosis: 'account-locked' | 'password-expired' | 'mfa-factor-unavailable';
  name: string;
  remediation: 'unlock' | 'password' | 'mfa';
  signInAction: string;
  ticketId: string;
}

async function openDirectoryUser(page: Page, name: string) {
  await page.goto('/tools/directory');
  await page
    .getByPlaceholder('Search name, username, or department')
    .fill(name);
  await page.getByRole('button', { name: new RegExp(`^${name}`) }).click();
  await expect(page.getByRole('heading', { name })).toBeVisible();
}

async function runIdentityCheck(page: Page, accountCase: AccountCase) {
  await page.goto(
    `/tools/company-chat?contact=${accountCase.contactId}&ticket=${accountCase.ticketId}`,
  );
  await page
    .getByRole('button', { name: 'Run approved identity check' })
    .click();
  await expect(
    page.getByText('No password, recovery code, security answer', {
      exact: false,
    }),
  ).toHaveCount(2);
}

async function confirmOriginalSymptom(page: Page, accountCase: AccountCase) {
  await page.goto(
    `/tools/company-chat?contact=${accountCase.contactId}&ticket=${accountCase.ticketId}`,
  );
  await page
    .getByRole('button', { name: 'Ask user to retest original symptom' })
    .click();
  await expect(
    page.getByText('It now works and I can continue.', { exact: false }),
  ).toHaveCount(2);
}

async function remediateAccount(page: Page, accountCase: AccountCase) {
  if (accountCase.remediation === 'unlock') {
    await page
      .getByRole('button', { name: 'Unlock account', exact: true })
      .click();
    const dialog = page.getByRole('dialog', { name: 'Unlock account' });
    await dialog
      .getByRole('button', { name: 'Unlock account', exact: true })
      .click();
    await expect(
      page.getByText('Account unlocked.', { exact: false }),
    ).toBeVisible();
    return;
  }

  if (accountCase.remediation === 'password') {
    await page
      .getByRole('button', { name: 'Reset password', exact: true })
      .click();
    const dialog = page.getByRole('dialog', { name: 'Reset password' });
    await expect(dialog.getByRole('checkbox')).toBeChecked();
    await dialog
      .getByRole('button', { name: 'Issue temporary credential' })
      .click();
    await expect(
      page.getByText('Temporary password issued.', { exact: false }),
    ).toBeVisible();
    return;
  }

  await page.getByRole('button', { name: 'Reset MFA', exact: true }).click();
  const dialog = page.getByRole('dialog', { name: 'Reset MFA' });
  await dialog.getByRole('button', { name: 'Reset MFA', exact: true }).click();
  await expect(
    page.getByText('MFA registration cleared.', { exact: false }),
  ).toBeVisible();
}

async function verifySignIn(page: Page, accountCase: AccountCase) {
  await page.getByRole('button', { name: 'Test original sign-in' }).click();
  const dialog = page.getByRole('dialog', { name: 'Simulated sign-in test' });
  await dialog.getByRole('button', { name: accountCase.signInAction }).click();
  await expect(dialog.getByText('Checkpoint reached')).toBeVisible();
  await dialog
    .getByRole('button', { name: 'Record successful sign-in test' })
    .click();
  await expect(
    page.getByText('original sign-in path has been verified', { exact: false }),
  ).toBeVisible();
}

async function documentAndClose(page: Page, accountCase: AccountCase) {
  await page.goto(`/tickets/${accountCase.ticketId}`);
  await page.getByLabel('Add a note').fill(resolutionNote);
  await page.getByRole('button', { name: 'Add internal note' }).click();
  await page.getByRole('button', { name: 'Resolve / close' }).click();
  const dialog = page.getByRole('dialog', { name: 'Resolve or close ticket' });
  await dialog.getByRole('checkbox').check();
  await dialog.getByRole('button', { name: 'Continue to review' }).click();
  await expect(dialog.getByText('Ready to resolve')).toBeVisible();
  await dialog.getByRole('button', { name: 'Resolve ticket' }).click();
  await expect(
    page.getByText('Resolved', { exact: true }).first(),
  ).toBeVisible();
}

async function completeAccountCase(page: Page, accountCase: AccountCase) {
  await openDirectoryUser(page, accountCase.name);
  await page.getByRole('button', { name: 'Review account state' }).click();

  await runIdentityCheck(page, accountCase);
  await openDirectoryUser(page, accountCase.name);
  await page
    .getByRole('button', { name: 'Record verified chat evidence' })
    .click();

  if (accountCase.remediation === 'mfa') {
    await page
      .getByRole('button', { name: 'Test primary password sign-in' })
      .click();
    await expect(
      page.getByText('Primary password authentication succeeds', {
        exact: false,
      }),
    ).toBeVisible();
  }

  await page
    .getByLabel('Account diagnosis')
    .selectOption(accountCase.diagnosis);
  await page.getByRole('button', { name: 'Record diagnosis' }).click();
  await remediateAccount(page, accountCase);
  await verifySignIn(page, accountCase);
  await confirmOriginalSymptom(page, accountCase);
  await documentAndClose(page, accountCase);
}

const cases: readonly AccountCase[] = [
  {
    contactId: 'directory-user-taylor-morgan',
    diagnosis: 'account-locked',
    name: 'Taylor Morgan',
    remediation: 'unlock',
    signInAction: 'Attempt clean account sign-in',
    ticketId: 'INC2511',
  },
  {
    contactId: 'directory-user-jordan-lee',
    diagnosis: 'password-expired',
    name: 'Jordan Lee',
    remediation: 'password',
    signInAction: 'Begin temporary-credential handoff',
    ticketId: 'INC2512',
  },
  {
    contactId: 'directory-user-camille-reyes',
    diagnosis: 'mfa-factor-unavailable',
    name: 'Camille Reyes',
    remediation: 'mfa',
    signInAction: 'Test sign-in through second factor',
    ticketId: 'INC2513',
  },
];

for (const accountCase of cases) {
  test(`completes the ${accountCase.ticketId} ${accountCase.diagnosis} workflow`, async ({
    page,
  }) => {
    const pageErrors: Error[] = [];
    page.on('pageerror', (error) => pageErrors.push(error));

    await completeAccountCase(page, accountCase);
    expect(pageErrors).toEqual([]);
  });
}
