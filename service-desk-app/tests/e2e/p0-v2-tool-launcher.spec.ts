import { expect, test, type Page } from '@playwright/test';

const MODULE_KEY = 'module.aplus.core1.ip_configuration';
const ASSESSMENT_KEY = 'assess.aplus.ipcfg.service_desk';
const RETURN_TO = `/learning-v2/modules/${MODULE_KEY}`;
const V2_LAUNCH_URL =
  `/service-desk/tickets/INC2503?returnTo=${encodeURIComponent(RETURN_TO)}` +
  `&v2ModuleKey=${encodeURIComponent(MODULE_KEY)}` +
  `&v2AssessmentKey=${encodeURIComponent(ASSESSMENT_KEY)}`;

async function useAuthenticatedStudentFixture(page: Page) {
  await page.context().addCookies([
    {
      name: 'student_session',
      value:
        process.env.NEXUS_E2E_STUDENT_SESSION ?? 'p0-authenticated-fixture',
      domain: '127.0.0.1',
      path: '/',
      httpOnly: true,
      sameSite: 'Lax',
    },
  ]);
  // Standalone Playwright has no Backend process. This fixture gives the web
  // session boundary an authenticated student identity; integrated runs may
  // provide NEXUS_E2E_STUDENT_SESSION and use the real endpoint instead.
  if (!process.env.NEXUS_E2E_STUDENT_SESSION) {
    await page.route('**/api/session', (route) =>
      route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          userId: '1000',
          name: 'P0 Characterization Student',
          email: 'p0-student@nexus.test',
          isMentor: false,
          isAdmin: false,
        }),
      }),
    );
  }
}

test('P0 Finding C — V2 launcher preserves the active tool after searchParams change (fixed in Wave 5)', async ({
  page,
}) => {
  test.fail();
  await useAuthenticatedStudentFixture(page);
  await page.goto(V2_LAUNCH_URL);
  await page.evaluate(() =>
    localStorage.setItem('sd:first-guided-orientation-seen', '1'),
  );
  await page.reload();

  await page
    .getByRole('navigation', { name: 'Suggested tools' })
    .getByRole('button', { name: 'Remote Desktop' })
    .click();
  await page.waitForTimeout(750);

  // Today the tool's native searchParams update races the workspace state and
  // clears activeToolSlug. Wave 5 keeps the embedded pane authoritative.
  await expect(page).toHaveURL(/(?:\?|&)tool=remote-desktop(?:&|$)/);
  await expect(
    page.getByRole('heading', { name: 'Remote Desktop', exact: true }),
  ).toBeVisible();
});

test('P0 Finding D — rejected Resolution Note stays visible with feedback (fixed in Wave 6)', async ({
  page,
}) => {
  test.fail();
  await useAuthenticatedStudentFixture(page);
  await page.goto('/service-desk/tickets/INC2511');
  await page.evaluate(() =>
    localStorage.setItem('sd:first-guided-orientation-seen', '1'),
  );
  await page.reload();

  const note = 'Restarted computer and issue resolved.';
  const textarea = page.getByLabel('Add a note');
  await textarea.fill(note);
  await page.getByRole('button', { name: 'Add internal note' }).click();

  // The engine rejects this incomplete account-case note. Today the panel
  // clears it and renders no feedback; Wave 6 preserves it and explains why.
  await expect.soft(textarea).toHaveValue(note);
  await expect.soft(page.getByRole('alert')).toBeVisible();
});

export { V2_LAUNCH_URL };
