import { expect, test } from '@playwright/test';
import traces from '../../packages/shared/src/realism-traces.test.json';
import tracesV2 from '../../packages/shared/src/realism-v2-traces.test.json';

test('authored requester question produces a scoped reply and survives refresh', async ({ page }) => {
  await page.goto('/tools/company-chat?ticket=INC2508');
  await expect(page.getByText('At 10:05 I entered', { exact: false })).toHaveCount(0);
  await page.getByRole('button', { name: 'What exactly did you enter, when, and did you approve MFA?' }).click();
  await expect(page.getByText('At 10:05 I entered', { exact: false })).toBeVisible();
  await page.reload();
  await expect(page.getByText('At 10:05 I entered', { exact: false })).toBeVisible();
  await page.goto('/tools/company-chat?ticket=INC2506');
  await expect(page.getByText('At 10:05 I entered', { exact: false })).toHaveCount(0);
  await page.getByRole('button', { name: 'Who approved this, and what is the approval reference?' }).click();
  await expect(page.getByText("I don't have a reference.", { exact: false })).toBeVisible();
});

for (const [ticket, trace] of Object.entries({ ...traces, ...tracesV2 })) {
  test(`${ticket}: real tools replace wizard and survive refresh`, async ({
    page,
  }) => {
    const assetTag = `NX-${ticket.slice(3)}`;
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(`/tools/remote-desktop?ticket=${ticket}`);
    const workstation = page
      .getByText(assetTag, { exact: true })
      .locator('..')
      .locator('..');
    await workstation
      .getByRole('button', { name: 'Connect', exact: true })
      .click();
    await expect(page.getByText('Remote Login', { exact: true })).toBeVisible();
    await page.locator('input').nth(0).fill('student');
    await page.locator('input').nth(1).fill('password');
    await page.getByRole('button', { name: 'OK', exact: true }).click();
    await page.getByRole('button', { name: 'Open Start menu' }).click();
    await page
      .getByRole('button', { name: 'Command Prompt', exact: true })
      .last()
      .click();
    await expect(
      page.getByText('Case investigation workspace', { exact: true }),
    ).toHaveCount(0);
    for (const command of trace.commands) {
      await page.getByLabel('Terminal command').fill(command);
      await page.getByLabel('Terminal command').press('Enter');
    }
    await expect(
      page.getByText(trace.commands.at(-1)!, { exact: false }).last(),
    ).toBeVisible();
    await page.reload();
    await expect(page.getByLabel('Terminal command')).toBeVisible();
    expect(errors).toEqual([]);
  });
}
