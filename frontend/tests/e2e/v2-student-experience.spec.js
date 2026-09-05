import { expect, test } from "@playwright/test";

const moduleTitle = "IP Configuration & Basic Connectivity Troubleshooting";

test("authenticated student can use the live V2 shell and durable activity surfaces", async ({ page }) => {
  test.setTimeout(180000);
  const username = process.env.NEXUS_E2E_STUDENT_USERNAME;
  const password = process.env.NEXUS_E2E_STUDENT_PASSWORD;
  expect(username && password).toBeTruthy();
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/login?next=/learning-v2");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();

  await expect(page).toHaveURL(/\/learning-v2$/);
  await expect(page.getByRole("heading", { name: "CompTIA A+" })).toBeVisible();
  await expect(page.getByRole("heading", { name: moduleTitle }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "PC Components, Power & Safe Upgrades" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Windows Support Tools & Client Configuration" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Windows Performance, Startup & Application Troubleshooting" })).toBeVisible();
  await page.screenshot({ path: "/tmp/nexus-v2-entry-desktop.png", fullPage: true });

  await page.getByRole("link", { name: /PC Components, Power & Safe Upgrades/ }).click();
  await expect(page.getByRole("heading", { name: "PC Components, Power & Safe Upgrades" })).toBeVisible();
  await page.getByRole("link", { name: /Motherboards, Form Factors and Compatibility/ }).click();
  await expect(page.getByRole("heading", { name: "Motherboards, Form Factors and Compatibility", exact: true })).toBeVisible();
  await expect(page.getByText("Required").first()).toBeVisible();
  await page.goto("/learning-v2");

  await page.getByRole("link", { name: /Continue learning/ }).click();
  await expect(page.getByRole("heading", { name: "IPv4 Configuration Basics", exact: true })).toBeVisible();
  await expect(page.getByText("Required").first()).toBeVisible();
  await page.getByRole("link", { name: /Open required resource/ }).click();
  await page.getByRole("button", { name: "I finished this" }).click();
  await page.getByRole("button", { name: "Mark lesson complete" }).click();
  await page.reload();
  await expect(page.getByText("Completed").first()).toBeVisible();
  await expect(page.getByText(/ipconfig/).first()).toBeVisible();
  await page.screenshot({ path: "/tmp/nexus-v2-lesson-desktop.png", fullPage: true });

  await page.getByRole("link", { name: "Start Quick Check" }).click();
  await expect(page).toHaveURL(/\/assessments\//);
  await expect(page.getByText(/Question 1 of \d+/)).toBeVisible();
  const firstQuestion = await page.locator("main > section.panel h2").textContent();
  const firstChoice = page.locator("fieldset input").first();
  if (await firstChoice.isVisible().catch(() => false)) await firstChoice.check();
  else await page.getByLabel("Your answer").fill("saved draft");
  await page.reload();
  await expect(page.getByRole("heading", { name: firstQuestion, exact: true })).toBeVisible();
  await expect(page.getByText("1 answered")).toBeVisible();
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  const countText = await page.getByText(/Question 1 of \d+/).textContent();
  const total = Number(countText.match(/of (\d+)/)?.[1] || 1);
  for (let index = 1; index < total; index += 1) {
    await page.getByRole("button", { name: "Next" }).click();
  }
  await page.getByRole("button", { name: "Submit answers" }).click();
  await page.getByRole("button", { name: "Submit anyway" }).click();
  await expect(page.getByRole("heading", { name: "Not passed yet" })).toBeVisible();
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByText(/Question 1 of \d+/)).toBeVisible();
  await page.getByRole("link", { name: "Back to module" }).click();
  await expect(page.getByRole("heading", { name: moduleTitle }).first()).toBeVisible();

  const secondLesson = page.getByRole("link", { name: /DHCP and APIPA/ });
  await secondLesson.click();
  await expect(page.getByRole("heading", { name: "DHCP and APIPA", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "DHCP and APIPA", exact: true })).toBeVisible();

  await page.goto("/learning-v2/modules/module.aplus.core1.ip_configuration/assessments/assess.aplus.ipcfg.module_quiz");
  await expect(page.getByText(/Question 1 of \d+/)).toBeVisible();
  const quizQuestion = await page.locator("main > section.panel h2").textContent();
  await page.reload();
  await expect(page.getByRole("heading", { name: quizQuestion, exact: true })).toBeVisible();

  await page.goto("/learning-v2/modules/module.aplus.core1.ip_configuration/practical/assess.aplus.ipcfg.practical");
  await expect(page).toHaveURL(/\/labs\/\d+\?v2Module=.*v2Assessment=/);
  await expect(page.getByRole("heading", { name: /Inspect Windows IP Configuration/ })).toBeVisible();

  await page.goto("/learning-v2/modules/module.aplus.core1.ip_configuration/explain/interview.aplus.ipcfg.what_does_dhcp_do");
  await expect(page.getByRole("heading", { name: "Put it in your own words" })).toBeVisible();
  await expect(page.getByLabel("Your response")).toBeVisible();

  await page.goto("/learning-v2/modules/module.aplus.core1.ip_configuration/service-desk/assess.aplus.ipcfg.service_desk");
  await expect(page).toHaveURL(/\/service-desk\/tickets\/INC2503.*v2ModuleKey=.*v2AssessmentKey=/, { timeout: 30000 });
  const orientationButton = page.getByRole("button", { name: "Open ticket" });
  const orientationVisible = await orientationButton
    .waitFor({ state: "visible", timeout: 10000 })
    .then(() => true)
    .catch(() => false);
  if (orientationVisible) await orientationButton.click();
  await expect(page.getByText(/INC2503|network/i).first()).toBeVisible({ timeout: 30000 });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Today" })).toBeVisible();
  await page.getByRole("button", { name: "Browser Training Student" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
  await page.getByRole("link", { name: "Progress" }).click();
  await expect(page.getByRole("heading", { name: "Progress", exact: true })).toBeVisible();

  await page.goto("/learning-v2/modules/module.aplus.core1.ip_configuration");
  await expect(page.getByText("1 / 5")).toBeVisible();
  await expect(page.getByText("Completed").first()).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(page.getByRole("heading", { name: moduleTitle })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
  await page.screenshot({ path: "/tmp/nexus-v2-module-mobile.png", fullPage: true });

  await page.goto("/learning-v2/modules/not-a-module");
  await expect(page.getByRole("heading", { name: "Module unavailable" })).toBeVisible();
});
