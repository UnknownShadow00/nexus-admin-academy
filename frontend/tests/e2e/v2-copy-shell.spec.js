import { expect, test } from "@playwright/test";

const pilotModule = "IP Configuration & Basic Connectivity Troubleshooting";

async function login(page, username, password, next = "/") {
  await page.goto(`/login?next=${encodeURIComponent(next)}`);
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
}

test("copy-backed pilot shell survives logout while non-pilot stays out", async ({ page }) => {
  const pilot = process.env.NEXUS_E2E_STUDENT_USERNAME;
  const pilotPassword = process.env.NEXUS_E2E_STUDENT_PASSWORD;
  const nonpilot = process.env.NEXUS_E2E_NONPILOT_USERNAME;
  const nonpilotPassword = process.env.NEXUS_E2E_NONPILOT_PASSWORD;
  const api = process.env.NEXUS_E2E_API_URL;
  const serviceDesk = process.env.NEXUS_E2E_SERVICE_DESK_URL;
  expect(pilot && pilotPassword && nonpilot && nonpilotPassword && api && serviceDesk).toBeTruthy();

  const backendContract = await page.request.get(`${api}/api/service-desk/contract`);
  const serviceDeskHealth = await page.request.get(`${serviceDesk}/service-desk/api/health`);
  expect(backendContract.ok()).toBe(true);
  expect(serviceDeskHealth.ok()).toBe(true);
  expect(await backendContract.json()).toMatchObject({ contract_version: "2.0" });
  expect(await serviceDeskHealth.json()).toMatchObject({
    status: "ok",
    contract_version: "2.0",
    contract: { actual: "2.0", compatible: true },
  });

  await login(page, pilot, pilotPassword);
  await expect(page.getByRole("heading", { name: "Today" })).toBeVisible();
  await expect(page.getByRole("heading", { name: pilotModule }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "My Course" })).toBeVisible();
  await page.getByRole("link", { name: "My Course" }).click();
  await expect(page.getByRole("heading", { name: "CompTIA A+" })).toBeVisible();
  await expect(page.getByRole("heading", { name: pilotModule }).first()).toBeVisible();
  await page.getByRole("link", { name: new RegExp(pilotModule) }).first().click();
  await expect(page.getByRole("heading", { name: pilotModule }).first()).toBeVisible();

  await page.getByRole("button", { name: /Browser Training Student/ }).click();
  await expect(page).toHaveURL(/\/login$/);
  await login(page, nonpilot, nonpilotPassword);
  await expect(page.getByRole("heading", { name: "Today" })).toBeVisible();
  await expect(page.getByRole("link", { name: "My Course" })).toHaveCount(0);

  await page.getByRole("button", { name: /Qualified Browser Student/ }).click();
  await login(page, pilot, pilotPassword);
  await page.getByRole("link", { name: "My Course" }).click();
  await expect(page).toHaveURL(/\/learning-v2$/);
  await expect(page.getByRole("heading", { name: pilotModule }).first()).toBeVisible();
});
