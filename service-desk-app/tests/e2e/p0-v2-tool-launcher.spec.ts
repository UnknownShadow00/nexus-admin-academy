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
  await useAuthenticatedStudentFixture(page);
  // This standalone server has no mount prefix. The authenticated frontend
  // beginner spec exercises the complete /service-desk curriculum URL.
  await page.goto(V2_LAUNCH_URL.replace('/service-desk', ''));
  await page.evaluate(() =>
    localStorage.setItem('sd:first-guided-orientation-seen', '1'),
  );
  await page.reload();

  await page
    .getByRole('navigation', { name: 'Suggested tools' })
    .getByRole('button', { name: 'Remote Desktop' })
    .click();
  await expect(
    page.getByRole('combobox', { name: 'Choose a ticket' }),
  ).toHaveCount(0);
  const url = new URL(page.url());
  expect(url.searchParams.get('returnTo')).toBe(RETURN_TO);
  expect(url.searchParams.get('v2ModuleKey')).toBe(MODULE_KEY);
  expect(url.searchParams.get('v2AssessmentKey')).toBe(ASSESSMENT_KEY);
  expect(url.searchParams.get('ticket')).toBe('INC2503');

  // The tool updates its own query context after opening. The embedded pane,
  // rather than the transient `tool=` query value, remains authoritative.
  await expect(
    page.getByRole('heading', { name: 'Remote Desktop', exact: true }),
  ).toBeVisible();
});

test('P0 Finding D — rejected Resolution Note stays visible with feedback (fixed in Wave 6)', async ({
  page,
}) => {
  await useAuthenticatedStudentFixture(page);
  await page.goto('/tickets/INC2511');
  await page.evaluate(() =>
    localStorage.setItem('sd:first-guided-orientation-seen', '1'),
  );
  await page.reload();

  const note = 'Restarted computer and issue resolved.';
  const textarea = page.getByLabel('Add a note');
  await textarea.fill(note);
  await page.getByRole('button', { name: 'Add internal note' }).click();

  // The engine rejects this incomplete account-case note. The panel preserves
  // the learner's exact text and explains what evidence is still missing.
  await expect.soft(textarea).toHaveValue(note);
  await expect
    .soft(
      page
        .getByRole('alert')
        .filter({ hasText: 'Your note needs enough detail' }),
    )
    .toBeVisible();
});

export { V2_LAUNCH_URL };
