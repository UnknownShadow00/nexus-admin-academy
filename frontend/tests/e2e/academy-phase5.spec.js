import { expect, test } from '@playwright/test';
import { mkdirSync } from 'node:fs';

// Actual disposable API + Academy + Service Desk, not browser data fixtures.
const moduleKey = 'module.aplus.core1.printers_mfds';
const moduleRoute = `/learning-v2/modules/${moduleKey}`;
const widths = [1440, 1280, 1024, 768, 390, 320];
async function login(page) {
  const base = process.env.NEXUS_E2E_BASE_URL;
  if (!base || !['localhost', '127.0.0.1'].includes(new URL(base).hostname)) throw Error('Explicit disposable loopback stack required');
  await page.goto('/login');
  await page.getByLabel('Username', { exact: true }).fill(process.env.NEXUS_E2E_STUDENT_A_USERNAME);
  await page.getByLabel('Password', { exact: true }).fill(process.env.NEXUS_E2E_STUDENT_A_PASSWORD);
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
}
async function mode(page, value) {
  const toggle = page.getByRole('button', { name: 'Toggle dark mode', exact: true });
  if ((await toggle.getAttribute('aria-pressed')) !== String(value === 'dark')) await toggle.click();
  if (await page.locator('.academy').count()) await expect(page.locator('.academy')).toHaveClass(new RegExp(value));
  else await expect(page.locator('html')).toHaveAttribute('data-theme', value);
}
async function capture(page, name, width, theme) {
  const dir = process.env.NEXUS_PHASE5_CAPTURE;
  if (!dir || ![1440, 390].includes(width)) return;
  mkdirSync(dir, { recursive: true });
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map(image => image.decode().catch(() => {})));
  });
  await page.screenshot({ path: `${dir}/${name}-${theme}-${width}.png`, fullPage: width === 390, animations: 'disabled' });
}
async function geometry(page, width) {
  await page.evaluate(async () => { await Promise.all([...document.images].map(image => image.decode().catch(() => {}))); });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width + 1);
  await expect(page.locator('main').first()).toBeVisible();
  const images = await page.locator('.scene img').evaluateAll(images => images.map(image => ({ fit: getComputedStyle(image).objectFit, width: image.naturalWidth })));
  expect(images.every(image => image.width > 0 && ['cover', 'contain'].includes(image.fit))).toBe(true);
  // Long real curriculum titles must stay inside their cards, even when the
  // page itself has no horizontal overflow.
  const escapedTitles = await page.locator('.today-dashboard .stage').evaluateAll(cards => cards.filter(card => card.querySelector('strong').getBoundingClientRect().right > card.getBoundingClientRect().right - 7).map(card => card.textContent));
  expect(escapedTitles).toEqual([]);
}

test('Phase 5 real learner pages preserve geometry, themes and section history at six widths', async ({ page }) => {
  test.setTimeout(180_000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await login(page);
  const response = await page.request.get(`/api/v2/curriculum/modules/${moduleKey}`);
  expect(response.ok()).toBe(true);
  const module = (await response.json()).data;
  const lesson = module.lessons[0];
  const lessonRoute = `${moduleRoute}/lessons/${lesson.key}`;
  const quizRoute = `${moduleRoute}/assessments/${lesson.quick_check.key}`;
  for (const [name, route, ready] of [
    ['today', '/', '.today-dashboard'],
    ['learning-path', '/learning-v2', 'main'],
    ['lesson', lessonRoute, '.academy-lesson'],
    ['quiz', quizRoute, '.academy-quiz'],
  ]) {
    await page.goto(route);
    await expect(page.locator(ready).first()).toBeVisible();
    if (name === 'lesson') await expect(page.getByRole('heading', { level: 1, name: lesson.title, exact: true })).toBeVisible();
    for (const width of widths) {
      await page.setViewportSize({ width, height: width < 768 ? 844 : 1000 });
      for (const theme of ['light', 'dark']) {
        await mode(page, theme);
        await page.evaluate(() => scrollTo(0, 0));
        await geometry(page, width);
        await capture(page, name, width, theme);
      }
    }
  }
  await page.goto(lessonRoute);
  await page.setViewportSize({ width: 320, height: 844 });
  const skip = page.getByRole('link', { name: 'Skip to content', exact: true });
  expect((await skip.boundingBox()).y + (await skip.boundingBox()).height).toBeLessThan(0);
  await skip.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#learner-content')).toBeFocused();
  expect((await skip.boundingBox()).y + (await skip.boundingBox()).height).toBeLessThan(0);
  const tabs = page.getByRole('navigation', { name: 'Lesson sections', exact: true });
  await tabs.getByRole('link', { name: 'Learn', exact: true }).click();
  await expect(tabs.getByRole('link', { name: 'Learn', exact: true })).toHaveAttribute('aria-current', 'location');
  await expect(page.locator('.lesson-steps a[href="#lesson-understand"]')).toHaveAttribute('aria-current', 'location');
  await tabs.getByRole('link', { name: 'Resources', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#lesson-resources')).toBeFocused();
  await page.reload();
  await expect(tabs.getByRole('link', { name: 'Resources', exact: true })).toHaveAttribute('aria-current', 'location');
  await page.goBack();
  await expect(tabs.getByRole('link', { name: 'Learn', exact: true })).toHaveAttribute('aria-current', 'location');
  await expect(page.locator('#lesson-understand')).toBeFocused();
  await page.getByRole('link', { name: 'Your next step', exact: true }).click();
  await expect(page.locator('.lesson-steps a[href="#lesson-completion"]')).toHaveAttribute('aria-current', 'location');
  await page.locator('.lesson-bottom .btn').last().scrollIntoViewIfNeeded();
  const action = await page.locator('.lesson-bottom .btn').last().boundingBox();
  const nav = await page.locator('.mobile-nav').boundingBox();
  expect(action.y + action.height).toBeLessThanOrEqual(nav.y);
  expect(errors).toEqual([]);
});

test('Phase 5 Service Desk queue and real workspace reflow without obscuring notes', async ({ page }) => {
  test.setTimeout(180_000);
  await login(page);
  await page.goto('/service-desk');
  await expect(page.getByRole('heading', { name: 'Ticket queue', exact: true })).toBeVisible();
  for (const width of widths) {
    await page.setViewportSize({ width, height: width < 768 ? 844 : 1000 });
    for (const theme of ['light', 'dark']) { await mode(page, theme); await geometry(page, width); await capture(page, 'ticket-queue', width, theme); }
  }
  await page.goto(moduleRoute);
  await page.getByRole('link', { name: 'Troubleshoot a ticket', exact: true }).click();
  await expect.poll(async () => await page.getByTestId('ticket-workspace').isVisible() || await page.getByRole('button', { name: 'Open ticket', exact: true }).isVisible()).toBe(true);
  if (await page.getByRole('button', { name: 'Open ticket', exact: true }).isVisible()) await page.getByRole('button', { name: 'Open ticket', exact: true }).click();
  await expect(page.getByTestId('ticket-workspace')).toBeVisible();
  for (const width of widths) {
    await page.setViewportSize({ width, height: width < 768 ? 844 : 1000 });
    for (const theme of ['light', 'dark']) {
      await mode(page, theme); await page.evaluate(() => scrollTo(0, 0));
      await geometry(page, width); await capture(page, 'ticket', width, theme);
    }
    if (width < 768) {
      await page.getByRole('tab', { name: 'Notes', exact: true }).click();
      const input = page.getByLabel('Add a note');
      await input.focus();
      await input.evaluate(element => element.scrollIntoView({ block: 'center' }));
      expect((await input.boundingBox()).y + (await input.boundingBox()).height).toBeLessThan(844 - 65);
      await page.getByRole('tab', { name: 'Work', exact: true }).click();
    }
  }
});

test('real written submission survives disabled worker and unauthorized review without provisional credit', async ({ page, browser }) => {
  await login(page);
  const apiPath = '/api/v2/curriculum/modules/module.aplus.core1.hardware_support/assessments/assess.aplus.hardware.qc.platform';
  let loaded = await page.request.get(apiPath);
  expect(loaded.ok()).toBe(true);
  let data = (await loaded.json()).data;
  if (data.result?.grading_state === 'graded') {
    loaded = await page.request.post(`${apiPath}/attempts`, { headers: { Origin: process.env.NEXUS_E2E_BASE_URL } });
    expect(loaded.ok()).toBe(true);
    data = (await loaded.json()).data;
  }
  const written = data.questions.find(question => question.type === 'short_answer');
  expect(written).toBeTruthy();
  const original = '  I would investigate how this platform connects its components.\nThen verify those connections.  ';
  const summary = async () => (await (await page.request.get('/api/service-desk/progress-summary')).json());
  const before = await summary();
  const me = await page.request.get(`${process.env.NEXUS_E2E_API_URL}/auth/me`);
  expect(me.ok()).toBe(true);
  const studentId = (await me.json()).data.student_id;
  expect(studentId).toBeTruthy();
  const stats = async () => {
    const response = await page.request.get(`/api/students/${studentId}/stats`);
    expect(response.ok()).toBe(true);
    const body = await response.json();
    const value = body.data ?? body;
    expect(typeof value.total_xp).toBe('number');
    return value;
  };
  const beforeStats = await stats();
  const submitted = await page.request.post(`${apiPath}/submit`, {
    headers: { Origin: process.env.NEXUS_E2E_BASE_URL },
    data: { attempt_id: data.attempt.id, answers: { [written.id]: original } },
  });
  expect(submitted.ok()).toBe(true);
  const result = (await submitted.json()).data;
  expect(result.grading_state).toBe('pending');
  expect(result.score).toBeNull();
  expect(result.passed).not.toBe(true);
  expect(result.results.every(item => !item.correct_answer?.length && !item.explanation)).toBe(true);
  const denied = await page.request.get('/api/admin/grading/queue');
  expect(denied.status()).toBe(403);
  await page.goto(apiPath.replace('/api/v2/curriculum', '/learning-v2'));
  await expect(page.getByRole('heading', { name: 'Grading pending', exact: true })).toBeVisible();
  await expect(page.locator('.result-review')).toContainText(original.trim());
  await expect(page.getByRole('button', { name: 'Try again', exact: true })).toHaveCount(0);
  for (const theme of ['light', 'dark']) {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await mode(page, theme); await capture(page, 'written-pending', 1440, theme);
  }

  const admin = await browser.newContext({ baseURL: process.env.NEXUS_E2E_BASE_URL });
  try {
    const signedIn = await admin.request.post('/api/admin/session/login', { data: { username: process.env.NEXUS_E2E_ADMIN_USERNAME, password: process.env.NEXUS_E2E_ADMIN_PASSWORD } });
    expect(signedIn.ok()).toBe(true);
    const config = await admin.request.get('/api/admin/grading/config');
    expect((await config.json()).data.enabled).toBe(false); // No paid/automatic provider is enabled by this test.
    const queue = await admin.request.get('/api/admin/grading/queue');
    const job = (await queue.json()).data.find(item => item.source_key === 'assess.aplus.hardware.qc.platform' && item.student_id === studentId);
    expect(job).toBeTruthy();
    const run = await admin.request.post('/api/admin/grading/run', { headers: { Origin: process.env.NEXUS_E2E_BASE_URL }, data: { limit: 200 } });
    expect(run.ok()).toBe(true);
    const detail = await admin.request.get(`/api/admin/grading/${job.pending_grade_id}`);
    const history = (await detail.json()).data;
    expect(history.status).toBe('needs_review');
    expect(history.submitted_answer).toBe(original);
  } finally { await admin.close(); }
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Grading pending', exact: true })).toBeVisible();
  const persisted = (await (await page.request.get(apiPath)).json()).data.result;
  expect(persisted.grading_state).toBe('pending');
  expect(persisted.score).toBeNull();
  expect(persisted.results.find(item => item.question_id === written.id).student_answer).toBe(original);
  expect((await summary()).total_xp).toBe(before.total_xp);
  expect((await stats()).total_xp).toBe(beforeStats.total_xp);
});
