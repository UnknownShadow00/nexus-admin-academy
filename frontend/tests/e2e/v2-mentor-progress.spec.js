import { expect, test } from "@playwright/test";

test("mentor reviews the five-student V2 cohort and grades Explain work", async ({ page }) => {
  test.setTimeout(90000);
  const username = process.env.NEXUS_E2E_ADMIN_USERNAME;
  const password = process.env.NEXUS_E2E_ADMIN_PASSWORD;
  expect(username).toBeTruthy();
  expect(password).toBeTruthy();

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/admin-login?redirect=%2Fadmin%2Fv2-progress");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/admin\/v2-progress$/);
  await expect(page.getByRole("heading", { name: "V2 Student Progress" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Student B" })).toBeVisible();
  const weakAreas = page.locator('section[aria-labelledby="weak-heading"]');
  await expect(weakAreas).toBeVisible();
  await expect(weakAreas.getByText("DHCP and APIPA", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Suggested Review Topics" })).toBeVisible();

  await page.getByLabel("Module", { exact: true }).selectOption("module.aplus.core1.hardware_support");
  await expect(page.getByLabel("Module", { exact: true })).toHaveValue("module.aplus.core1.hardware_support");
  await expect(page.getByRole("link", { name: "Student B" })).toBeVisible();
  await page.getByLabel("Module", { exact: true }).selectOption("module.aplus.core1.ip_configuration");
  await expect(weakAreas.getByText("DHCP and APIPA", { exact: true })).toBeVisible();

  const focusButton = page.getByRole("button", { name: "Set to this module" });
  if (await focusButton.isEnabled()) await focusButton.click();
  await expect(page.getByText(/CompTIA A\+ → IP Configuration/)).toBeVisible();

  await page.getByRole("link", { name: "Student B" }).click();
  await expect(page.getByRole("heading", { name: "Student B" })).toBeVisible();
  await expect(page.getByText(/Module Quiz/).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Weak Areas" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Missed Questions" })).toBeVisible();
  await expect(page.getByText(/APIPA/).first()).toBeVisible();
  await page.getByRole("article").filter({ hasText: "Explain APIPA" }).getByRole("link", { name: "Grade response" }).click();
  await expect(page.getByRole("heading", { name: "Review Explain response" })).toBeVisible();
  await page.getByLabel("Score (0–1)").fill("0.8");
  await page.getByLabel("Reason / note").fill("Correctly connects APIPA to a missing DHCP response.");
  await page.getByRole("button", { name: "Submit mentor grade" }).click();
  await expect(page.getByText("Correctly connects APIPA to a missing DHCP response.")).toBeVisible();

  await page.goto("/admin/v2-progress");
  await expect(page.getByRole("heading", { name: "V2 Student Progress" })).toBeVisible();
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.reload();
  await expect(page.getByRole("heading", { name: "V2 Student Progress" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
});

test("student credentials cannot access mentor data", async ({ page }) => {
  const username = process.env.NEXUS_E2E_STUDENT_USERNAME;
  const password = process.env.NEXUS_E2E_STUDENT_PASSWORD;
  const apiUrl = process.env.NEXUS_E2E_API_URL;
  expect(username && password && apiUrl).toBeTruthy();
  const login = await page.request.post(`${apiUrl}/auth/login`, { data: { username, password } });
  expect(login.ok()).toBe(true);
  const token = (await login.json()).access_token;
  const response = await page.request.get(`${apiUrl}/api/admin/v2/mentor/cohort/module.aplus.core1.ip_configuration`, { headers: { Authorization: `Bearer ${token}` } });
  expect(response.status()).toBe(403);
  await page.goto("/admin/v2-progress");
  await expect(page).toHaveURL(/\/admin-login/);
});
