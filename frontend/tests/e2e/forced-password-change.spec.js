import { expect, test } from "@playwright/test";

const existingUsername = process.env.NEXUS_E2E_STUDENT_USERNAME || "browser-training-student";
const existingPassword = process.env.NEXUS_E2E_STUDENT_PASSWORD || "BrowserTraining!2026";
const adminUsername = process.env.NEXUS_E2E_ADMIN_USERNAME || "browser-admin";
const adminPassword = process.env.NEXUS_E2E_ADMIN_PASSWORD || "BrowserAdmin!2026";
const apiBaseUrl = process.env.NEXUS_E2E_API_URL || "http://127.0.0.1:8011";
const browserBaseUrl = process.env.NEXUS_E2E_BASE_URL || "http://127.0.0.1:5173";

async function login(page, username, password) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
}

async function adminLogin(page) {
  await page.goto("/admin-login");
  await page.getByLabel("Username").fill(adminUsername);
  await page.getByLabel("Password").fill(adminPassword);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/admin$/);
}

async function changePassword(page, password) {
  await page.getByLabel("New password", { exact: true }).fill(password);
  await page.getByLabel("Confirm new password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Today", exact: true })).toBeVisible();
}

test("forced first-login rotation and admin reset preserve beginner progress", async ({ page, browser }) => {
  test.setTimeout(180_000);
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  const username = `browser-password-${suffix}`;
  const temporaryPassword = "TemporaryBrowserPass!2026";
  const permanentPassword = "PermanentBrowserPass!2026";
  const resetPassword = "ResetBrowserPass!2026";
  const finalPassword = "FinalBrowserPass!2026";
  let studentId;

  // A returning student that was not reset must retain normal access.
  const existingContext = await browser.newContext({ baseURL: browserBaseUrl });
  const existingPage = await existingContext.newPage();
  await login(existingPage, existingUsername, existingPassword);
  await expect(existingPage).toHaveURL(/\/$/);
  await expect(existingPage.getByRole("heading", { name: "Today", exact: true })).toBeVisible();
  await expect(existingPage).not.toHaveURL(/\/change-password$/);
  await existingContext.close();

  try {
    await adminLogin(page);
    const createResponse = await page.request.post(`${apiBaseUrl}/api/admin/students`, {
      headers: { Origin: browserBaseUrl, Referer: `${browserBaseUrl}/admin/students` },
      data: {
        name: "Disposable Password Rotation Student",
        email: `${username}@example.invalid`,
        username,
        password: temporaryPassword,
      },
    });
    const createBody = await createResponse.json();
    expect(createResponse.ok(), JSON.stringify(createBody)).toBeTruthy();
    studentId = createBody.data.student_id;
    await page.getByRole("button", { name: "Admin Sign Out" }).click();

    await login(page, username, temporaryPassword);
    await expect(page).toHaveURL(/\/change-password$/);
    await expect(page.getByRole("heading", { name: "Choose your password" })).toBeVisible();

    // Direct frontend and backend bypasses remain blocked.
    await page.goto("/learning-path");
    await expect(page).toHaveURL(/\/change-password$/);
    await expect(page.getByRole("heading", { name: "Learning Path", exact: true })).toHaveCount(0);
    const blockedApi = await page.request.get(`${apiBaseUrl}/api/students/me/week-plan?week=0`);
    expect(blockedApi.status()).toBe(403);
    expect((await blockedApi.json()).code).toBe("PASSWORD_CHANGE_REQUIRED");

    // Logout is still available while the gate is active.
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login$/);
    await login(page, username, temporaryPassword);
    await expect(page).toHaveURL(/\/change-password$/);

    // Confirmation, policy, and temporary-password reuse are rejected.
    await page.getByLabel("New password", { exact: true }).fill("MismatchPassword!2026");
    await page.getByLabel("Confirm new password", { exact: true }).fill("DifferentPassword!2026");
    await page.getByRole("button", { name: "Change password" }).click();
    await expect(page.getByRole("alert")).toContainText("Passwords do not match");

    const requestHeaders = { Origin: browserBaseUrl, Referer: `${browserBaseUrl}/change-password` };
    const shortResponse = await page.request.post(`${apiBaseUrl}/auth/change-password`, {
      headers: requestHeaders,
      data: { new_password: "too-short", confirm_password: "too-short" },
    });
    expect(shortResponse.status()).toBe(400);
    const sameResponse = await page.request.post(`${apiBaseUrl}/auth/change-password`, {
      headers: requestHeaders,
      data: { new_password: temporaryPassword, confirm_password: temporaryPassword },
    });
    expect(sameResponse.status()).toBe(400);

    await changePassword(page, permanentPassword);
    await expect(page.getByRole("link", { name: "Progress", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Service Desk", exact: true })).toBeVisible();

    // Complete one real beginner lesson so reset preservation is visible in UI.
    await page.getByRole("link", { name: "Start Training" }).first().click();
    await expect(page).toHaveURL(/\/lessons\/\d+$/);
    const orientationPath = new URL(page.url()).pathname;
    await expect(page.getByRole("heading", { name: "Welcome to Nexus", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Mark lesson complete", exact: true }).click();
    await expect(page.getByRole("button", { name: "Orientation complete", exact: true })).toBeVisible();

    await page.getByRole("button", { name: "Disposable Password Rotation Student" }).click();
    await expect(page).toHaveURL(/\/login$/);

    // The temporary credential is dead; the chosen password works.
    await login(page, username, temporaryPassword);
    await expect(page.getByRole("alert")).toContainText("Invalid credentials");
    await login(page, username, permanentPassword);
    await expect(page).toHaveURL(/\/$/);
    await page.getByRole("button", { name: "Disposable Password Rotation Student" }).click();

    // An admin reset forces another rotation without deleting progress.
    await adminLogin(page);
    const resetResponse = await page.request.put(`${apiBaseUrl}/api/admin/students/${studentId}`, {
      headers: { Origin: browserBaseUrl, Referer: `${browserBaseUrl}/admin/students` },
      data: { password: resetPassword },
    });
    expect(resetResponse.ok(), await resetResponse.text()).toBeTruthy();
    await page.getByRole("button", { name: "Admin Sign Out" }).click();

    await login(page, username, resetPassword);
    await expect(page).toHaveURL(/\/change-password$/);
    await changePassword(page, finalPassword);
    await page.goto(orientationPath);
    await expect(page.getByRole("button", { name: "Orientation complete", exact: true })).toBeVisible();
  } finally {
    if (studentId) {
      await page.context().clearCookies();
      await adminLogin(page);
      const deleteResponse = await page.request.delete(`${apiBaseUrl}/api/admin/students/${studentId}`, {
        headers: { Origin: browserBaseUrl, Referer: `${browserBaseUrl}/admin/students` },
      });
      expect(deleteResponse.ok()).toBeTruthy();
    }
  }
});
