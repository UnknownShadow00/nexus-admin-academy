import { test, expect } from "@playwright/test";
async function login(page) {
  if (new URL(process.env.NEXUS_E2E_BASE_URL).hostname !== "127.0.0.1")
    throw new Error("Loopback fixture required");
  await page.goto("/login");
  await page.getByLabel("Username").fill("wave2-learner");
  await page.getByLabel("Password").fill(process.env.WAVE2_PASSWORD);
  await page.getByRole("button", { name: /Login|Sign in/i }).click();
  await expect(page).not.toHaveURL(/login/);
}
test("fresh Today exposes My Course with V2 OFF", async ({ page }) => {
  await login(page);
  await expect(
    page.getByRole("link", { name: "My Course", exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByText(/After this:/)).toBeVisible();
});
test("Progress remains active on its canonical route", async ({ page }) => {
  await login(page);
  await page.goto("/progress");
  await expect(
    page.getByRole("link", { name: "Progress", exact: true }).first(),
  ).toHaveAttribute("aria-current", "page");
});
test("direct first quiz has missing-lesson recovery", async ({ page }) => {
  await login(page);
  await page.goto("/quizzes/42");
  await expect(
    page.getByRole("heading", { name: "Quiz locked" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Go to.*Welcome to Nexus/ }),
  ).toBeVisible();
});

async function screenshot(page, name) {
  await page.screenshot({
    path: `${process.env.WAVE2_SCREENSHOTS || "../docs/core-wave2/screenshots"}/${name}.png`,
    fullPage: true,
  });
}
test("first session teaches before the check and preserves named return on desktop and mobile", async ({
  page,
}) => {
  await login(page);
  await expect(
    page.getByRole("heading", {
      name: "Welcome to Nexus: Your First Week",
      exact: true,
    }),
  ).toBeVisible();
  await screenshot(page, "fresh-today");
  await page
    .getByRole("link", { name: "My Course", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "My Course", exact: true }),
  ).toBeVisible();
  await screenshot(page, "my-course");
  await page.goto("/training/module/module.endpoint.support_workflow");
  await expect(
    page.getByRole("heading", { name: "Module locked" }),
  ).toBeVisible();
  await screenshot(page, "locked-prerequisite");
  await page.goto("/");
  await page
    .getByRole("link", { name: "Continue lesson", exact: true })
    .click();
  await expect(
    page.getByText("What is a support ticket?", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Take quiz", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Mark lesson complete", exact: true })
    .click();
  await expect(
    page.getByText("Orientation complete", { exact: true }).first(),
  ).toBeVisible();
  await page.getByRole("link", { name: "Take quiz", exact: true }).click();
  await expect(
    page.getByText("Question 1 of 4", { exact: true }),
  ).toBeVisible();
  await screenshot(page, "first-quiz-entry");
  const answers = [
    [
      /initial data collection phase/,
      ["User information", "Device information", "Problem description"],
    ],
    [/recurring problems/, ["Category"]],
    [/memory failure/, ["Escalation level"]],
    [/network printer/, ["Progress notes"]],
  ];
  for (let i = 0; i < 4; i++) {
    await expect(
      page.getByText(`Question ${i + 1} of 4`, { exact: true }),
    ).toBeVisible();
    const heading = await page
      .locator("p")
      .filter({ hasText: /^\d+\./ })
      .textContent();
    const match = answers.find(([pattern]) => pattern.test(heading));
    expect(match, heading).toBeTruthy();
    for (const choice of match[1])
      await page
        .locator("label")
        .filter({ hasText: new RegExp(`${choice}$`) })
        .click();
    if (i < 3)
      await page.getByRole("button", { name: "Next", exact: true }).click();
  }
  await page.getByRole("button", { name: /Submit/ }).click();
  await expect(page.getByText("100%", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Passed", { exact: true })).toBeVisible();
  await page
    .getByRole("link", { name: "Saved review of this attempt" })
    .click();
  await page.reload();
  await page
    .getByRole("link", { name: "Back to Nexus Orientation" })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Nexus Orientation", exact: true }),
  ).toBeVisible();
  await screenshot(page, "return-to-module");
  await page.goto("/training/module/module.endpoint.support_workflow");
  await expect(
    page.getByRole("heading", {
      name: "Support Workflow Essentials",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.getByText(/Required \(3\):/)).toBeVisible();
  await screenshot(page, "first-required-module");
  await page
    .getByText("Optional practice (1)", { exact: false })
    .last()
    .click();
  await screenshot(page, "required-optional");
  await page.goto("/quizzes/1");
  await expect(
    page.getByRole("heading", { name: "Quiz locked" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Go to Anatomy of a Good Ticket" }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Go to Anatomy of a Good Ticket" })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Anatomy of a Good Ticket",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Mark lesson complete", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Lesson complete", exact: true }),
  ).toBeVisible();
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Meet the Command Line", exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await screenshot(page, "mobile-today");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.goto("/training/module/module.endpoint.support_workflow");
  await expect(
    page.getByRole("heading", {
      name: "Support Workflow Essentials",
      exact: true,
    }),
  ).toBeVisible();
  await screenshot(page, "mobile-module");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
