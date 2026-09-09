import { expect, test } from "@playwright/test";

const screenshotDir =
  process.env.WAVE3_SCREENSHOTS || "../docs/core-wave3/screenshots";

async function login(page, learner) {
  if (new URL(process.env.NEXUS_E2E_BASE_URL).hostname !== "127.0.0.1")
    throw new Error("Loopback fixture required");
  await page.goto("/login");
  await page.getByLabel("Username").fill(`wave3-learner-${learner}`);
  await page.getByLabel("Password").fill(process.env.WAVE3_PASSWORD);
  await page.getByRole("button", { name: /Login|Sign in/i }).click();
  await expect(page).not.toHaveURL(/login/);
}

async function capture(page, name, fullPage = false) {
  await page.screenshot({ path: `${screenshotDir}/${name}.png`, fullPage });
}

async function unlockFirstModule(page) {
  await page
    .getByRole("link", { name: "Continue lesson", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Mark lesson complete", exact: true })
    .click();
  await page.getByRole("link", { name: "Take quiz", exact: true }).click();
  const answers = [
    [
      /initial data collection phase/,
      ["User information", "Device information", "Problem description"],
    ],
    [/recurring problems/, ["Category"]],
    [/memory failure/, ["Escalation level"]],
    [/network printer/, ["Progress notes"]],
  ];
  for (let index = 0; index < answers.length; index += 1) {
    const heading = await page
      .locator("p")
      .filter({ hasText: /^\d+\./ })
      .textContent();
    const match = answers.find(([pattern]) => pattern.test(heading));
    for (const choice of match[1])
      await page
        .locator("label")
        .filter({ hasText: new RegExp(`${choice}$`) })
        .click();
    if (index < answers.length - 1)
      await page.getByRole("button", { name: "Next", exact: true }).click();
  }
  await page.getByRole("button", { name: /Submit/ }).click();
  await expect(page.getByText("Passed", { exact: true })).toBeVisible();
}

async function openTicketLessonFromCourse(page) {
  await page.goto("/");
  await page
    .getByRole("link", { name: "My Course", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "My Course", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: /Start Module|Continue Module/ })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Anatomy of a Good Ticket",
      exact: true,
    }),
  ).toBeVisible();
}

test("beginner lesson teaches, preserves notes, completes explicitly, and returns to its module", async ({
  page,
}) => {
  test.setTimeout(60_000);
  await page.setViewportSize({ width: 1280, height: 900 });
  await login(page, 1);
  await unlockFirstModule(page);
  await openTicketLessonFromCourse(page);

  const objectives = page.getByTestId("lesson-objectives");
  const body = page.getByTestId("lesson-body");
  await expect(objectives).toBeVisible();
  expect(
    await objectives.evaluate(
      (node, other) =>
        Boolean(
          node.compareDocumentPosition(other) &
            Node.DOCUMENT_POSITION_FOLLOWING,
        ),
      await body.elementHandle(),
    ),
  ).toBe(true);
  await expect(
    page.getByRole("heading", { name: "Why this matters" }),
  ).toBeVisible();
  await capture(page, "lesson-top-objectives-purpose");

  await page
    .getByRole("heading", { name: "Core idea / mental model" })
    .scrollIntoViewIfNeeded();
  await expect(
    page.getByText("reported symptom", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Worked example" }),
  ).toBeVisible();
  await capture(page, "mental-model-worked-example", true);

  const note = page.getByLabel("Lesson notes");
  const noteText = `Fast navigation note ${Date.now()}`;
  await note.fill(noteText);
  await expect(page.getByText("Saving…", { exact: true })).toBeVisible();
  await capture(page, "note-saving");
  await page
    .getByRole("link", { name: "Back to Support Workflow Essentials" })
    .click();
  await page
    .locator("article")
    .filter({ hasText: "Anatomy of a Good Ticket" })
    .getByRole("link", { name: "Start" })
    .click();
  await expect(page.getByLabel("Lesson notes")).toHaveValue(noteText);
  await expect(page.getByText("Saved", { exact: true })).toBeVisible();
  await capture(page, "note-saved");

  await page
    .getByRole("heading", { name: "Ready to finish this lesson?" })
    .scrollIntoViewIfNeeded();
  await expect(
    page.getByText(/Quizzes and practical work provide separate evidence/),
  ).toBeVisible();
  await capture(page, "completion-readiness");
  await page
    .getByRole("button", { name: "Mark lesson complete", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Lesson completion saved." }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Meet the Command Line" }),
  ).toBeVisible();
  await capture(page, "completion-success-next-activity");

  await page.getByRole("link", { name: "Meet the Command Line" }).click();
  await expect(page.getByText("terminal", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Mark lesson complete", exact: true })
    .click();
  await expect(
    page.getByRole("link", { name: "Ticket Writing Fundamentals" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Ticket Writing Fundamentals" }).click();
  await expect(page.getByText(/Question 1 of/)).toBeVisible();
  await page
    .getByRole("link", { name: "Back to Support Workflow Essentials" })
    .first()
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Support Workflow Essentials",
      exact: true,
    }),
  ).toBeVisible();
});

test("completion and notes failures are visible and retryable", async ({
  page,
}) => {
  await login(page, 2);
  await unlockFirstModule(page);
  await openTicketLessonFromCourse(page);
  let noteFailures = 1;
  await page.route("**/api/lessons/*/notes", async (route) => {
    if (route.request().method() === "PUT" && noteFailures-- > 0)
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "injected" }),
      });
    else await route.continue();
  });
  await page.getByLabel("Lesson notes").fill("Draft survives a failed save");
  await expect(page.getByText("Couldn’t save", { exact: true })).toBeVisible();
  await capture(page, "note-save-error");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText("Saved", { exact: true })).toBeVisible();

  let completionFailures = 1;
  await page.route("**/api/lessons/*/complete", async (route) => {
    if (completionFailures-- > 0)
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "injected" }),
      });
    else await route.continue();
  });
  await page
    .getByRole("button", { name: "Mark lesson complete", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "We couldn’t save your lesson completion.",
  );
  await expect(
    page.getByRole("button", { name: "Mark lesson complete" }),
  ).toBeEnabled();
  await capture(page, "completion-save-error");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(
    page.getByRole("heading", { name: "Lesson completion saved." }),
  ).toBeVisible();
});

test("390px lesson keeps objectives, notes, and completion usable without overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, 3);
  await unlockFirstModule(page);
  await openTicketLessonFromCourse(page);
  await expect(page.getByTestId("lesson-objectives")).toBeVisible();
  await expect(page.getByLabel("Lesson notes")).toBeEditable();
  await page
    .getByRole("button", { name: "Mark lesson complete" })
    .scrollIntoViewIfNeeded();
  await expect(
    page.getByRole("button", { name: "Mark lesson complete" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await capture(page, "mobile-390-lesson", true);
});
