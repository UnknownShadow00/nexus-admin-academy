import { expect, test } from "@playwright/test";
import fs from "node:fs";

const weekTwoQuiz = JSON.parse(fs.readFileSync(new URL("../../../backend/app/data/training_reference_content.json", import.meta.url))).quizzes.find((item) => item.id === 78);
const caseRoute = (id) => new RegExp(`/service-desk/tickets/${id}\\?`);

async function login(page, username, password) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
}

async function openAndReturn(page, link, ticketId, modulePath) {
  await link.click();
  await expect(page).toHaveURL(caseRoute(ticketId));
  expect(new URL(page.url()).searchParams.get("returnTo")).toBe(modulePath);
  await expect(page.getByRole("heading", { name: ticketId === "INC2404" ? "USB headset develops static during longer calls" : "Can't sign in after lunch" })).toBeVisible();
  await page.reload();
  await expect(page.getByText(ticketId).first()).toBeVisible();
  await page.getByRole("link", { name: "Back to your module" }).first().click();
  await expect(page).toHaveURL(new RegExp(`${modulePath.replaceAll(".", "\\.")}$`));
}

test("INC2511 opens from Today, Progress, and module with a safe return", async ({ page }) => {
  test.setTimeout(90_000);
  if (!process.env.NEXUS_E2E_PHASE0A_W1_USERNAME) test.skip();
  await login(page, process.env.NEXUS_E2E_PHASE0A_W1_USERNAME, process.env.NEXUS_E2E_PHASE0A_W1_PASSWORD);
  const modulePath = "/training/module/module.endpoint.support_workflow";
  await openAndReturn(page, page.getByRole("link", { name: "Continue Training" }), "INC2511", modulePath);
  await page.goto("/skills");
  await openAndReturn(page, page.locator('a[href*="/service-desk/tickets/INC2511"]'), "INC2511", modulePath);
  await openAndReturn(page, page.locator('article[data-activity-type="service_desk_scenario"] a[href*="INC2511"]'), "INC2511", modulePath);
  await page.goto(`/service-desk/tickets/INC2511?returnTo=${encodeURIComponent("https://evil.example")}`);
  expect(await page.locator('a[href^="https://evil.example"]').count()).toBe(0);
  await page.goto(`/service-desk/tickets/NOT-AVAILABLE?returnTo=${encodeURIComponent(modulePath)}`);
  await expect(page.getByRole("heading", { name: "Case unavailable" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Back to queue" })).toBeVisible();
});

test("Week 2 quiz presentation and truthful INC2404 repair unlock Week 3", async ({ page }) => {
  test.setTimeout(180_000);
  if (!process.env.NEXUS_E2E_PHASE0A_W2_USERNAME) test.skip();
  await login(page, process.env.NEXUS_E2E_PHASE0A_W2_USERNAME, process.env.NEXUS_E2E_PHASE0A_W2_PASSWORD);
  const modulePath = "/training/module/module.endpoint.pc_hardware";
  await page.getByRole("link", { name: "Continue Training" }).click();
  await expect(page).toHaveURL(/\/quizzes\/78$/);
  let fifthPrompt;
  let fifthOptions;
  for (let number = 1; number <= weekTwoQuiz.questions.length; number += 1) {
    await expect(page.getByText(`Question ${number} of 19`, { exact: true })).toBeVisible();
    const panel = page.locator("fieldset.panel");
    const heading = await panel.getByRole("heading").innerText();
    const authored = weekTwoQuiz.questions.find((item) => heading.includes(item.question_text));
    expect(authored, `authored question shown at position ${number}`).toBeTruthy();
    const optionTexts = await panel.locator("label span:last-child").allTextContents();
    const correctLetters = (authored.correct_answers || authored.correct_answer).split(",").map((letter) => letter.trim());
    const correctTexts = correctLetters.map((letter) => authored[`option_${letter.toLowerCase()}`]);
    for (const correctText of correctTexts) expect(optionTexts).toContain(correctText);
    if (number === 5) { fifthPrompt = authored.question_text; fifthOptions = optionTexts; }
    for (const correctText of correctTexts) await panel.getByText(correctText, { exact: true }).click();
    await page.getByRole("button", { name: number === 19 ? "Submit Quiz" : "Next", exact: true }).click();
  }
  await expect(page.getByText("19 / 19", { exact: false })).toBeVisible();
  const fifthReview = page.locator("article", { hasText: fifthPrompt });
  await expect(fifthReview.getByRole("heading", { level: 3 })).toContainText("Q5.");
  for (const option of fifthOptions) await expect(fifthReview.getByText(option, { exact: true })).toBeVisible();
  await page.goto("/");
  await expect(page.locator("#continue-learning")).toBeVisible();
  await openAndReturn(page, page.getByRole("link", { name: "Continue Training" }), "INC2404", modulePath);
  await expect(page.getByText("11 of 12 required", { exact: false }).first()).toBeVisible();
  await page.goto("/skills");
  await openAndReturn(page, page.locator('a[href*="/service-desk/tickets/INC2404"]'), "INC2404", modulePath);
  await openAndReturn(page, page.locator('article[data-activity-type="service_desk_scenario"] a[href*="INC2404"]'), "INC2404", modulePath);

  await page.goto("/service-desk/tools/asset-management");
  await page.getByPlaceholder("Search assets").fill("NX-9052");
  await page.getByText("NX-9052", { exact: true }).first().click();
  await page.getByRole("button", { name: "Test affected headset on known-good workstation" }).click();
  await page.getByRole("button", { name: "Test known-good headset on affected workstation" }).click();
  await page.locator("#status-NX-9052").selectOption("damaged");
  await page.getByRole("button", { name: "Update status" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Mark damaged" }).click();
  await page.goto("/service-desk/tools/shipping-manager");
  await page.getByLabel("Recipient name").fill("Elliot Ward");
  await page.getByRole("checkbox", { name: "Headset", exact: true }).check();
  await page.getByRole("radio", { name: /Express/ }).check();
  await page.getByRole("button", { name: "Ship", exact: true }).click();
  await page.goto("/service-desk/tools/asset-management");
  await page.getByPlaceholder("Search assets").fill("NX-9052");
  await page.getByText("NX-9052", { exact: true }).first().click();
  await page.getByRole("button", { name: "Confirm clean audio with replacement" }).click();
  await page.goto("/service-desk/tools/company-chat?contact=directory-user-elliot-ward&ticket=INC2404");
  await page.getByRole("button", { name: "Ask user to retest original symptom" }).click();
  await expect(page.getByText("The static did not return", { exact: false }).first()).toBeVisible();
  await page.goto("/service-desk/tickets/INC2404");
  await page.getByLabel("Add a note").fill("Confirmed static followed the headset, marked NX-9052 damaged, shipped Elliot a replacement, and verified clean audio and his longer-call retest.");
  await page.getByRole("button", { name: "Add internal note" }).click();
  await page.getByRole("button", { name: "Resolve", exact: true }).click();
  await page.getByRole("checkbox", { name: /verified the requester/i }).check();
  await page.getByRole("button", { name: "Continue to review" }).click();
  await page.getByRole("button", { name: "Resolve ticket" }).click();
  await expect(page.getByRole("region", { name: "Ticket debrief" })).toBeVisible();
  await page.goto(modulePath);
  await expect(page.getByText("12 of 12 required", { exact: false }).first()).toBeVisible();
  await page.goto("/learning-path");
  await expect(page.getByRole("heading", { name: "Windows Fundamentals & Diagnostics" }).first()).toBeVisible();
  const training = await (await page.request.get("/api/training")).json();
  expect(training.data.current_week.week_number).toBe(3);
});
