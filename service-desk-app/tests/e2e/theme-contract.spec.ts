import { expect, test } from '@playwright/test';

test('current theme contract defaults dark and honors an explicit saved choice', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');

  await page.evaluate(() => localStorage.setItem('theme', 'light'));
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
});
