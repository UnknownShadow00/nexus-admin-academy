import { expect, test } from "@playwright/test";

const username = process.env.NEXUS_E2E_STUDENT_USERNAME || "browser-training-student";
const password = process.env.NEXUS_E2E_STUDENT_PASSWORD || "BrowserTraining!2026";
const verificationFixture = {
  label: "Simulated device state after action",
  description: "Deterministic training evidence; no real device changed.",
  fields: [{ label: "Install state", value: "Installed" }],
};

async function login(page) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/$/);
}

function labPayload({ role = "practice", guidance, panelCount = 3, status = "not_started", feedback } = {}) {
  const panels = [
    { id: "device", label: "Device", fields: [{ label: "Hostname", value: "NEX-LT-1042" }] },
    { id: "applications", label: "Applications", fields: [{ label: "Detection", value: "Failed" }] },
    { id: "compliance", label: "Compliance", fields: [{ label: "Overall", value: "Compliant" }] },
    { id: "access", label: "Access", fields: [{ label: "Conditional Access", value: "Grant" }] },
    { id: "policies", label: "Policies", fields: [{ label: "Wallpaper", value: "Succeeded" }] },
  ].slice(0, panelCount);
  return {
    id: 9001,
    title: role === "prove" ? "Diagnose the Multi-Signal Ticket" : "Endpoint training case",
    description: "Inspect evidence and resolve the case.",
    lab_type: "structured_endpoint",
    difficulty: 2,
    week_number: 32,
    estimated_minutes: 20,
    setup_instructions: "Inspect, decide, verify, and document.",
    status,
    structured_feedback: feedback,
    success_criteria: {
      endpoint_workbench: {
        guidance_level: role,
        brief: "The assigned application is missing from a managed Windows 11 device.",
        ...(guidance ? { guidance } : {}),
        panels,
        required_inspections: role === "prove" ? ["device", "applications", "compliance", "access"] : ["device", "applications"],
        documentation_required: true,
      },
      questions: [
        {
          id: "diagnosis",
          prompt: "What explains the symptom?",
          type: "single_choice",
          options: [{ id: "a", label: "Detection-rule mismatch" }, { id: "b", label: "Wipe required" }],
        },
        {
          id: "action",
          prompt: "What is the safest next action?",
          type: "single_choice",
          options: [{ id: "a", label: "Correct detection and sync" }, { id: "b", label: "Delete the device" }],
        },
        {
          id: "verify",
          prompt: "What proves resolution?",
          type: "single_choice",
          options: [{ id: "a", label: "Installed after detection evaluation" }, { id: "b", label: "The action button was clicked" }],
        },
      ],
    },
  };
}

async function mockLab(page, initial) {
  let current = initial;
  let submissionBody;
  let verificationBody;
  await page.route("**/api/labs/9001/verify", async (route) => {
    verificationBody = route.request().postDataJSON();
    const answers = verificationBody?.answers || {};
    const inspected = verificationBody?.inspected_panel_ids || [];
    const required = initial.success_criteria.endpoint_workbench.required_inspections;
    const ready = required.every((panelId) => inspected.includes(panelId)) && initial.success_criteria.questions.every((question) => answers[question.id]?.includes("a"));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: ready ? { ready: true, verification: verificationFixture } : { ready: false, message: "The selected path did not produce the expected state. Re-open the evidence and revise the unsupported decision." } }),
    });
  });
  await page.route("**/api/labs/9001/submit", async (route) => {
    submissionBody = route.request().postDataJSON();
    const correct = submissionBody.answers?.diagnosis?.[0] === "a";
    current = labPayload({
      role: initial.success_criteria.endpoint_workbench.guidance_level,
      guidance: initial.success_criteria.endpoint_workbench.guidance,
      panelCount: initial.success_criteria.endpoint_workbench.panels.length,
      status: "submitted",
      feedback: {
        score_pct: correct ? 100 : 67,
        questions: initial.success_criteria.questions.map((question, index) => ({
          id: question.id,
          correct: index ? true : correct,
          explanation: index || correct ? "Supported by the inspected evidence." : "That path does not explain the detection evidence.",
        })),
      },
    });
    current.notes = submissionBody.notes;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data: current }) });
  });
  await page.route("**/api/labs/9001", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data: current }) });
  });
  return { getSubmission: () => submissionBody, getVerification: () => verificationBody };
}

async function inspectRequiredEvidence(page) {
  await page.getByRole("tab", { name: "Device" }).click();
  await page.getByRole("tab", { name: "Applications" }).click();
}

async function answerAll(page, firstAnswer = "Detection-rule mismatch") {
  await page.getByText(firstAnswer, { exact: true }).click();
  await page.getByRole("button", { name: "Continue investigation" }).click();
  await page.getByText("Correct detection and sync", { exact: true }).click();
  await page.getByRole("button", { name: "Continue investigation" }).click();
  await page.getByText("Installed after detection evaluation", { exact: true }).click();
}

async function documentCase(page) {
  await page.getByRole("textbox", { name: "Issue", exact: true }).fill("Assigned app is missing.");
  await page.getByRole("textbox", { name: "Evidence", exact: true }).fill("Install succeeded but detection failed.");
  await page.getByRole("textbox", { name: "Action", exact: true }).fill("Corrected the detection rule and synced.");
  await page.getByRole("textbox", { name: "Verification", exact: true }).fill("App reports Installed after evaluation.");
}

test("Practice workbench requires inspect, decide, verify, and documentation on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await login(page);
  const requests = await mockLab(page, labPayload({ guidance: "Compare the app install and detection fields." }));
  await page.goto("/labs/9001");

  await expect(page.getByText("Investigation hint:")).toBeVisible();
  await expect(page.getByText("What explains the symptom?")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Submit evidence case" })).toBeDisabled();
  await inspectRequiredEvidence(page);
  await expect(page.getByText("What explains the symptom?")).toBeVisible();
  await answerAll(page);
  await expect(page.getByText("Simulated device state after action")).toHaveCount(0);
  await page.getByRole("button", { name: "Run simulated verification" }).click();
  await expect(page.getByText("Simulated device state after action")).toBeVisible();
  await documentCase(page);
  await page.getByRole("button", { name: "Submit evidence case" }).click();
  await expect(page.getByText("Server-graded result: 100%")).toBeVisible();

  expect(requests.getVerification().inspected_panel_ids.sort()).toEqual(["applications", "device"]);
  const notes = JSON.parse(requests.getSubmission().notes);
  expect(Object.keys(notes).sort()).toEqual(["action", "evidence", "issue", "verification"]);
  const widths = await page.evaluate(() => ({ client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(widths.scroll).toBeLessThanOrEqual(widths.client + 1);
});

test("Troubleshoot workbench blocks immediate completion and gives scoped wrong-path feedback", async ({ page }) => {
  await login(page);
  await mockLab(page, labPayload({ role: "troubleshoot" }));
  await page.goto("/labs/9001");

  await expect(page.getByText("Investigation hint:")).toHaveCount(0);
  await expect(page.getByText("What explains the symptom?")).toHaveCount(0);
  await inspectRequiredEvidence(page);
  await answerAll(page, "Wipe required");
  await page.getByRole("button", { name: "Run simulated verification" }).click();
  await expect(page.getByRole("alert")).toContainText("did not produce the expected state");
  await expect(page.getByText("Simulated device state after action")).toHaveCount(0);
  await page.getByRole("button", { name: "Review previous decision" }).click();
  await page.getByRole("button", { name: "Review previous decision" }).click();
  await page.getByText("Detection-rule mismatch", { exact: true }).click();
  await page.getByRole("button", { name: "Continue investigation" }).click();
  await page.getByRole("button", { name: "Continue investigation" }).click();
  await page.getByRole("button", { name: "Run simulated verification" }).click();
  await documentCase(page);
  await page.getByRole("button", { name: "Submit evidence case" }).click();
  await expect(page.getByText("Server-graded result: 100%")).toBeVisible();
});

test("Prove workbench supplies distractors but no walkthrough", async ({ page }) => {
  await login(page);
  await mockLab(page, labPayload({ role: "prove", panelCount: 5 }));
  await page.goto("/labs/9001");

  await expect(page.getByText("Prove case", { exact: true })).toBeVisible();
  await expect(page.getByText("Investigation hint:")).toHaveCount(0);
  await expect(page.getByRole("tab")).toHaveCount(5);
  await expect(page.getByRole("tab", { name: "Policies" })).toBeVisible();
  await page.getByRole("tab", { name: "Device" }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("tab", { name: "Applications" }).click();
  await page.getByRole("tab", { name: "Compliance" }).click();
  await page.getByRole("tab", { name: "Access" }).click();
  await expect(page.getByRole("tab", { name: "Policies" })).not.toHaveAccessibleName(/✓/);
  await answerAll(page);
  await expect(page.getByRole("button", { name: "Submit evidence case" })).toBeDisabled();
  await page.getByRole("button", { name: "Run simulated verification" }).click();
  await documentCase(page);
  await page.getByRole("button", { name: "Submit evidence case" }).click();
  await expect(page.getByText("Server-graded result: 100%")).toBeVisible();
});

test("Persisted structured support notes are restored after reload", async ({ page }) => {
  await login(page);
  const saved = JSON.stringify({ issue: "Saved issue", evidence: "Saved evidence", action: "Saved action", verification: "Saved verification" });
  const initial = labPayload({ status: "submitted", feedback: { score_pct: 100, questions: [] } });
  initial.notes = saved;
  await mockLab(page, initial);
  await page.goto("/labs/9001");

  await expect(page.getByRole("textbox", { name: "Issue", exact: true })).toHaveValue("Saved issue");
  await expect(page.getByRole("textbox", { name: "Verification", exact: true })).toHaveValue("Saved verification");
});
