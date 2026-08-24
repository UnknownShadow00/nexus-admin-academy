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

async function expectNoPageOverflow(page) {
  const widths = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(widths.scroll).toBeLessThanOrEqual(widths.client + 1);
}

test("Phase 4C.2 cases are coherent, progressive, and usable at mobile width", async ({ page }) => {
  await login(page);
  await page.setViewportSize({ width: 375, height: 812 });

  await page.goto("/labs/2");
  await expect(page.getByRole("heading", { name: "Client network triage" })).toBeVisible();
  await expect(page.getByText("10.40.8.57", { exact: false })).toHaveCount(0);
  await terminalCommand(page, "ipconfig /all", "DNS Servers");
  await terminalCommand(page, "nslookup intranet.nexus.internal", "Non-existent domain");
  await terminalCommand(page, "get-diagnosis", "unavailable in this focused case");
  await expect(page.getByRole("button", { name: "Submit evidence case" })).toBeDisabled();
  await expectNoPageOverflow(page);

  await page.goto("/labs/10");
  await expect(page.getByRole("heading", { name: "Routing and network-services troubleshoot" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Exam 2: Access Ports/ })).toHaveAttribute("href", "/cli-labs/dev-sw-act-23");
  await page.getByRole("tab", { name: "Client samples" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText(/169\.254\.32\.18/)).toBeVisible();

  await page.goto("/labs/11");
  await expect(page.getByRole("heading", { name: "Secure network administration troubleshoot" })).toBeVisible();
  await expect(page.getByText("Troubleshoot case", { exact: true })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Handoff / escalation", exact: true })).toBeVisible();

  await page.goto("/labs/16");
  await expect(page.getByRole("heading", { name: "Linux fundamentals guided case" })).toBeVisible();
  await expect(page.getByText("Guided practice", { exact: true })).toBeVisible();
  await terminalCommand(page, "ls -l /var/log/nexus/orders.log", "nexusapp support");
  await terminalCommand(page, "id samira", "groups=1104(samira),100(users)");

  await page.goto("/labs/17");
  await expect(page.getByRole("heading", { name: "Linux service troubleshoot" })).toBeVisible();
  await terminalCommand(page, "systemctl status nginx", "Active: failed");
  await terminalCommand(page, "ss -lntp", "python3");
  await expectNoPageOverflow(page);

  await page.goto("/labs/18");
  await expect(page.getByRole("heading", { name: "Linux production prove case" })).toBeVisible();
  await expect(page.getByText("Investigation hint:")).toHaveCount(0);
  await terminalCommand(page, "df -h", "100%");
  await terminalCommand(page, "nginx -t", "syntax is ok");
  await expectNoPageOverflow(page);

  await page.goto("/labs/20");
  await expect(page.getByRole("heading", { name: "Azure VM access troubleshoot" })).toBeVisible();
  await expect(page.getByText("vm-inventory-22 — Running", { exact: true })).toHaveCount(0);
  await page.getByRole("tab", { name: "Resource" }).click();
  await expect(page.getByText("vm-inventory-22 — Running", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Run simulated verification" })).toHaveCount(0);
  await expectNoPageOverflow(page);
});

test("Phase 4C.1 and Phase 4B.2 evidence workbenches still render", async ({ page }) => {
  await login(page);
  for (const [labId, heading] of [
    [5, "Group Policy evidence case"],
    [15, "Windows Server prove case"],
    [26, "Endpoint evidence workbench"],
    [31, "Endpoint evidence workbench"],
  ]) {
    await page.goto(`/labs/${labId}`);
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    await expect(page.getByRole("button", { name: /Submit evidence case/ })).toBeDisabled();
  }
});
