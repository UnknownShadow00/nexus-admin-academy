import { expect, test } from "@playwright/test";

function required(name) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required for CLI browser tests.`);
  return value;
}

const username = required("NEXUS_E2E_STUDENT_C_USERNAME");
const password = required("NEXUS_E2E_STUDENT_C_PASSWORD");

async function login(page) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
}

test("beginner CLI lab accepts commands, validates completion, and restarts", async ({ page }) => {
  await login(page);
  await page.goto("/cli-labs/meet-cli-001");
  const input = page.getByLabel("CLI command input");
  await expect(input).toBeVisible();

  for (const command of ["enable", "?", "configure terminal"]) {
    await input.fill(command);
    await input.press("Enter");
  }

  await expect(page.getByText(/Saved with .* XP awarded|Completion saved|Complete locally/)).toBeVisible();
  await page.getByRole("button", { name: "Restart" }).click();
  await expect(page.getByText("In progress.", { exact: true })).toBeVisible();
  await expect(input).toHaveValue("");
});

test("maintained xterm terminal renders, accepts input, and survives mobile resize", async ({ page }) => {
  await login(page);
  await page.goto("/terminal");
  const terminal = page.locator(".xterm");
  await expect(terminal).toBeVisible();
  await terminal.click();
  await page.keyboard.type("ipconfig");
  await page.keyboard.press("Enter");
  await expect(page.locator(".xterm-rows")).toContainText("Windows IP Configuration");

  await page.setViewportSize({ width: 375, height: 812 });
  await expect(terminal).toBeVisible();
  await terminal.click();
  await page.keyboard.type("whoami");
  await page.keyboard.press("Enter");
  await expect(page.locator(".xterm-rows")).toContainText("NEXUS\\student01");
});
