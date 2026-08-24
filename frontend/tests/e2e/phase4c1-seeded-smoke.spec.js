import { expect, test } from "@playwright/test";

const username = process.env.NEXUS_E2E_STUDENT_USERNAME || "browser-training-student";
const password = process.env.NEXUS_E2E_STUDENT_PASSWORD || "BrowserTraining!2026";

async function login(page) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
}

async function terminalCommand(page, command, expected) {
  await page.locator(".xterm").click();
  await page.keyboard.type(command);
  await page.keyboard.press("Enter");
  await expect(page.locator(".xterm-rows")).toContainText(expected);
}

test("fresh seeded 0059 serves the representative Windows, AD, GPO, and server cases", async ({ page }) => {
  await login(page);

  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/labs/3");
  await expect(page.getByRole("heading", { name: "Windows host evidence case" })).toBeVisible();
  await expect(page.getByText("91% used", { exact: true })).toHaveCount(0);
  await page.getByRole("tab", { name: "Task Manager" }).click();
  await expect(page.getByText("91% used", { exact: true })).toBeVisible();
  const widths = await page.evaluate(() => ({ client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(widths.scroll).toBeLessThanOrEqual(widths.client + 1);

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/labs/8");
  await expect(page.getByRole("heading", { name: "Windows access evidence case" })).toBeVisible();
  await page.getByRole("tab", { name: "Current logon token" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("GG-Finance-Users not present", { exact: true })).toBeVisible();

  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/labs/5");
  await expect(page.getByRole("heading", { name: "Group Policy evidence case" })).toBeVisible();
  await terminalCommand(page, "gpresult /r", "Filtering: Denied (Security)");
  await terminalCommand(page, "gpupdate /force", "remains filtered: Denied (Security)");
  const terminalWidths = await page.evaluate(() => ({ client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(terminalWidths.scroll).toBeLessThanOrEqual(terminalWidths.client + 1);

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/labs/14");
  await expect(page.getByRole("heading", { name: "Windows Server investigation" })).toBeVisible();
  await terminalCommand(page, "Get-NetIPConfiguration", "DNSServer            : 10.20.99.10");
  await terminalCommand(page, "Resolve-DnsName db01.nexus.internal", "timeout period expired");

  await page.goto("/labs/15");
  await expect(page.getByRole("heading", { name: "Windows Server prove case" })).toBeVisible();
  await expect(page.getByText("Prove case", { exact: true })).toBeVisible();
  await terminalCommand(page, "Get-Service -Name NexusDeptSync", "Stopped  NexusDeptSync");
  await terminalCommand(page, "Get-WinEvent -LogName System -MaxEvents 5", "password is incorrect");
  await expect(page.getByRole("textbox", { name: "Escalation / handoff", exact: true })).toBeVisible();
});
