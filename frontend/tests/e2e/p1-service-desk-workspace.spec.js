import { expect, test } from "@playwright/test";

// Requires the fresh disposable fixture, BEFORE p0-service-desk-beginner
// completes this shared curriculum assignment (the CI steps enforce order).

const moduleKey = "module.aplus.core1.printers_mfds";
const returnTo = `/learning-v2/modules/${moduleKey}`;
const screenshots = process.env.NEXUS_P1_SCREENSHOTS;

async function launch(page) {
  const base = process.env.NEXUS_E2E_BASE_URL;
  if (!base || !["localhost", "127.0.0.1"].includes(new URL(base).hostname)) {
    throw new Error("A disposable loopback stack is required");
  }
  await page.goto("/login");
  await page
    .getByLabel("Username")
    .fill(process.env.NEXUS_E2E_STUDENT_A_USERNAME);
  await page
    .getByLabel("Password")
    .fill(process.env.NEXUS_E2E_STUDENT_A_PASSWORD);
  await page.getByRole("button", { name: "Login", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto(returnTo);
  await page.getByRole("link", { name: "Troubleshoot a ticket" }).click();
  await expect
    .poll(
      async () =>
        (await page
          .getByRole("button", { name: "Open ticket", exact: true })
          .isVisible()) ||
        (await page.getByTestId("ticket-workspace").isVisible()),
    )
    .toBe(true);
  if (
    await page
      .getByRole("button", { name: "Open ticket", exact: true })
      .isVisible()
  ) {
    await page
      .getByRole("button", { name: "Open ticket", exact: true })
      .click();
  }
}

async function openRemote(page) {
  const suggested = page
    .getByRole("navigation", { name: "Suggested tools" })
    .getByRole("button", { name: "Remote Desktop", exact: true });
  if (await suggested.isVisible()) await suggested.click();
  else {
    await page.getByRole("button", { name: "All tools", exact: true }).click();
    await page
      .getByRole("navigation", { name: "Workspace tools" })
      .getByRole("button", { name: "Remote Desktop", exact: true })
      .click();
  }
}

async function capture(page, name) {
  if (screenshots)
    await page.screenshot({
      path: `${screenshots}/${name}.png`,
      fullPage: true,
    });
}

test("P1 desktop curriculum shell retains note, evidence and return context across tools", async ({
  page,
}) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await launch(page);
  await capture(page, "desktop-initial");
  await expect(
    page.getByRole("navigation", { name: "Workspace tools" }),
  ).toBeHidden();
  await expect(
    page.getByText("Confirmed by your actions", { exact: true }),
  ).toBeInViewport();
  await expect(page.getByLabel("Add a note")).toBeInViewport();
  const draft =
    "Working draft: investigating printer destination before making changes.";
  await page.getByLabel("Add a note").fill(draft);
  await openRemote(page);
  await expect(
    page.getByRole("heading", { name: "Remote Desktop", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("combobox", { name: "Choose a ticket" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Connect", exact: true }),
  ).toHaveCount(1);
  await capture(page, "desktop-tool");
  await page.getByRole("button", { name: "Connect", exact: true }).click();
  await expect
    .poll(
      async () =>
        (await page.getByText("Remote Login", { exact: true }).isVisible()) ||
        (await page
          .getByRole("button", { name: "Open Start menu" })
          .isVisible()),
    )
    .toBe(true);
  if (await page.getByText("Remote Login", { exact: true }).isVisible()) {
    await page
      .locator("input")
      .filter({ visible: true })
      .nth(0)
      .fill("student");
    await page
      .locator("input")
      .filter({ visible: true })
      .nth(1)
      .fill("password");
    await page.getByRole("button", { name: "OK", exact: true }).click();
  }
  await page.getByRole("button", { name: "Open Start menu" }).click();
  await page
    .getByRole("button", { name: "Command Prompt", exact: true })
    .last()
    .click();
  await page.getByLabel("Terminal command").fill('sc query "Print Spooler"');
  await page.getByLabel("Terminal command").press("Enter");
  await expect(page.getByLabel("Ticket workspace rail")).toContainText(
    "Spooler",
  );
  const allTools = page.getByRole("button", { name: "All tools", exact: true });
  await allTools.focus();
  await page.keyboard.press("Enter");
  await expect(allTools).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Escape");
  await expect(allTools).toBeFocused();
  await expect(allTools).toHaveAttribute("aria-expanded", "false");
  await page.keyboard.press("Enter");
  await page.keyboard.press("Tab");
  await expect(
    page
      .getByRole("navigation", { name: "Workspace tools" })
      .getByRole("button", { name: "Directory", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(allTools).toBeFocused();
  await expect(
    page.getByRole("heading", { name: /Directory/ }).first(),
  ).toBeVisible();
  await expect(page.getByLabel("Add a note")).toHaveValue(draft);
  await expect(page.getByLabel("Ticket workspace rail")).toContainText(
    "Spooler",
  );
  await page
    .getByRole("button", { name: "Back to ticket INC2504", exact: true })
    .click();
  await expect(page.getByLabel("Add a note")).toHaveValue(draft);
  await capture(page, "desktop-evidence-notes");
  const url = new URL(page.url());
  expect(url.searchParams.get("ticket")).toBe("INC2504");
  expect(url.searchParams.get("tool")).toBeNull();
  expect(url.searchParams.get("returnTo")).toBe(returnTo);
  expect(url.searchParams.get("v2ModuleKey")).toBe(moduleKey);
  expect(url.searchParams.get("v2AssessmentKey")).toBe(
    "assess.aplus-core1-printers-mfds.service_desk",
  );
  await page
    .getByRole("link", { name: "Back to your module", exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp(`${returnTo}$`));
});

test("P1 mobile Work Evidence Notes retain drafts and fit 390px", async ({
  page,
}) => {
  test.setTimeout(120_000);
  await page.setViewportSize({ width: 390, height: 844 });
  await launch(page);
  const noOverflow = async () =>
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  await expect(
    page.getByRole("tab", { name: "Work", exact: true }),
  ).toBeVisible();
  await noOverflow();
  await capture(page, "mobile-initial");
  await page.getByRole("tab", { name: "Notes", exact: true }).click();
  await page
    .getByLabel("Add a note")
    .fill("Mobile draft retained while changing workspace sections.");
  await page.getByRole("tab", { name: /^Evidence/ }).click();
  await expect(
    page.getByText("Confirmed by your actions", { exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Work", exact: true }).click();
  await openRemote(page);
  await expect(
    page.getByRole("heading", { name: "Remote Desktop", exact: true }),
  ).toBeVisible();
  await noOverflow();
  await page.getByRole("button", { name: "Connect", exact: true }).click();
  await expect
    .poll(
      async () =>
        (await page.getByText("Remote Login", { exact: true }).isVisible()) ||
        (await page
          .getByRole("button", { name: "Open Start menu" })
          .isVisible()),
    )
    .toBe(true);
  if (await page.getByText("Remote Login", { exact: true }).isVisible()) {
    await page
      .locator("input")
      .filter({ visible: true })
      .nth(0)
      .fill("student");
    await page
      .locator("input")
      .filter({ visible: true })
      .nth(1)
      .fill("password");
    await page.getByRole("button", { name: "OK", exact: true }).click();
  }
  if (!(await page.getByLabel("Terminal command").isVisible())) {
    await page.getByRole("button", { name: "Open Start menu" }).click();
    await page
      .getByRole("button", { name: "Command Prompt", exact: true })
      .last()
      .click();
  }
  await page.getByLabel("Terminal command").fill('sc query "Print Spooler"');
  await page.getByLabel("Terminal command").press("Enter");
  await expect(page.getByLabel("Terminal command")).toBeVisible();
  await noOverflow();
  await capture(page, "mobile-tool");
  expect(
    (await page.getByTestId("remote-session-surface").boundingBox()).height,
  ).toBeLessThan(650);
  await page.getByRole("tab", { name: "Notes", exact: true }).click();
  await expect(page.getByLabel("Add a note")).toHaveValue(
    "Mobile draft retained while changing workspace sections.",
  );
  await noOverflow();
});
