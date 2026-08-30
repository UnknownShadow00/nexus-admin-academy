import { expect, test } from "@playwright/test";

const moduleTitle = "IP Configuration & Basic Connectivity Troubleshooting";

async function answerAssessment(page) {
  const countText = await page.getByText(/Question 1 of \d+/).textContent();
  const total = Number(countText.match(/of (\d+)/)?.[1] || 1);
  for (let index = 0; index < total; index += 1) {
    const shortAnswer = page.getByLabel("Your answer");
    if (await shortAnswer.isVisible().catch(() => false)) {
      await shortAnswer.fill("ipconfig");
    } else {
      const choices = page.locator("fieldset input");
      if (await choices.count()) await choices.first().check();
    }
    if (index < total - 1) await page.getByRole("button", { name: "Next" }).click();
  }
  await page.getByRole("button", { name: "Submit answers" }).click();
  await expect(page.getByRole("heading", { name: /You passed|Not passed yet/ })).toBeVisible();
}

test("student completes the first real V2 learning flow", async ({ page }) => {
  test.setTimeout(90000);
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
  await page.getByRole("button", { name: "Mark completed" }).first().click();
  await page.getByRole("button", { name: "Mark lesson complete" }).click();
  await page.reload();
  await expect(page.getByText("Completed").first()).toBeVisible();
  await expect(page.getByText(/ipconfig/).first()).toBeVisible();
  await page.screenshot({ path: "/tmp/nexus-v2-lesson-desktop.png", fullPage: true });

  await page.getByRole("link", { name: "Start Quick Check" }).click();
  await answerAssessment(page);
  await page.getByRole("link", { name: "Continue" }).click();
  await expect(page.getByRole("heading", { name: moduleTitle }).first()).toBeVisible();

  const secondLesson = page.getByRole("link", { name: /DHCP and APIPA/ });
  await secondLesson.click();
  await expect(page.getByRole("heading", { name: "DHCP and APIPA", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "DHCP and APIPA", exact: true })).toBeVisible();

  await page.goto("/learning-v2/modules/module.aplus.core1.ip_configuration");
  await page.getByRole("link", { name: /Take the quiz/ }).click();
  await answerAssessment(page);
  await page.getByRole("link", { name: "Continue" }).click();

  await page.getByRole("link", { name: /Open practical/ }).click();
  await expect(page.getByRole("heading", { name: /Inspect Windows IP Configuration/ })).toBeVisible();
  await page.getByRole("button", { name: "Start Lab" }).click();
  await page.getByLabel("Your evidence and answers").fill("Reviewed ipconfig /all, the gateway, DHCP, DNS, ping results, and nslookup. The connection is healthy.");
  await page.getByRole("button", { name: "Submit Lab" }).click();
  await expect(page.getByRole("button", { name: "Submitted" })).toBeDisabled();

  await page.goto("/learning-v2/modules/module.aplus.core1.ip_configuration");
  await page.getByRole("link", { name: /Troubleshoot a ticket/ }).click();
  await expect(page).toHaveURL(/\/service-desk\/tickets\/INC2503/);
  await expect(page.getByText(/INC2503|network/i).first()).toBeVisible({ timeout: 30000 });

  await page.goto("/learning-v2/modules/module.aplus.core1.ip_configuration");
  await page.getByRole("link", { name: /Open Explain/ }).click();
  await page.getByLabel("Your response").fill("I would investigate the workstation carefully, document the symptoms, and verify the result with the user after the fix.");
  await page.getByRole("button", { name: "Submit response" }).click();
  await expect(page.getByRole("heading", { name: "Waiting for grading" })).toBeVisible();

  const otherJob = await page.request.get("/api/grading/status?source_type=interview_explain&submission_ref=browser-other-submission");
  expect(otherJob.status()).toBe(404);

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
