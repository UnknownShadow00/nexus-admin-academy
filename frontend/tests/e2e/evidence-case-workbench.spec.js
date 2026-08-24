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

function question(id, prompt) {
  return {
    id,
    prompt,
    type: "single_choice",
    options: [
      { id: "supported", label: `${prompt} — supported by the evidence` },
      { id: "shortcut", label: `${prompt} — broad unsupported shortcut` },
    ],
  };
}

function casePayload({ week, domain, title, complaint, panels, required, terminal, prove = false, handoff = false, scenarios = [] }) {
  return {
    id: 9100 + week,
    title,
    description: "Inspect incident-specific evidence before acting.",
    lab_type: "structured_evidence_case",
    difficulty: prove ? 3 : 2,
    week_number: week,
    estimated_minutes: 30,
    setup_instructions: "Inspect, diagnose, choose a safe action, verify, and document.",
    status: "not_started",
    success_criteria: {
      evidence_case_workbench: {
        title: `${domain} evidence case`,
        domain,
        guidance_level: prove ? "prove" : week === 3 ? "practice" : "troubleshoot",
        complaint,
        panels,
        required_inspections: required,
        documentation_required: true,
        ...(terminal ? { terminal_profile: terminal } : {}),
        ...(handoff ? { additional_note_fields: [{ id: "handoff", label: "Escalation / handoff", placeholder: "Record the owner and follow-up." }] } : {}),
        ...(scenarios.length ? { reinforcement_scenarios: scenarios } : {}),
      },
      questions: [question("diagnosis", "Diagnosis"), question("action", "Safe action"), question("verify", "Verification")],
    },
  };
}

async function mockCase(page, initial) {
  let current = initial;
  let lastVerification;
  let lastSubmission;
  const labId = initial.id;
  await page.route(`**/api/labs/${labId}/verify`, async (route) => {
    lastVerification = route.request().postDataJSON();
    const required = initial.success_criteria.evidence_case_workbench.required_inspections;
    const inspected = lastVerification.inspected_panel_ids || [];
    const answers = lastVerification.answers || {};
    const ready = required.every((id) => inspected.includes(id)) && Object.values(answers).every((answer) => answer[0] === "supported") && Object.keys(answers).length === 3;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ success: true, data: ready ? { ready: true, verification: { label: "Incident-specific state verified", description: "Server accepted the exact supported plan.", fields: [{ label: "Outcome", value: "Expected service restored" }] } } : { ready: false, message: "The selected path did not produce the expected state." } }),
    });
  });
  await page.route(`**/api/labs/${labId}/submit`, async (route) => {
    lastSubmission = route.request().postDataJSON();
    current = {
      ...initial,
      status: "submitted",
      notes: lastSubmission.notes,
      structured_feedback: {
        score_pct: 100,
        questions: initial.success_criteria.questions.map((item) => ({ id: item.id, correct: true, explanation: "Supported by the inspected incident evidence." })),
      },
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data: current }) });
  });
  await page.route(`**/api/labs/${labId}`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data: current }) });
  });
  return { labId, verification: () => lastVerification, submission: () => lastSubmission };
}

async function answerSupported(page) {
  await page.getByText("Diagnosis — supported by the evidence", { exact: true }).click();
  await page.getByRole("button", { name: "Continue investigation" }).click();
  await page.getByText("Safe action — supported by the evidence", { exact: true }).click();
  await page.getByRole("button", { name: "Continue investigation" }).click();
  await page.getByText("Verification — supported by the evidence", { exact: true }).click();
}

async function documentCase(page, includeHandoff = false) {
  await page.getByRole("textbox", { name: "Issue", exact: true }).fill("Recorded the user-facing symptom.");
  await page.getByRole("textbox", { name: "Evidence", exact: true }).fill("Captured the incident-specific state.");
  await page.getByRole("textbox", { name: "Action", exact: true }).fill("Used the narrow approved response.");
  await page.getByRole("textbox", { name: "Verification", exact: true }).fill("Confirmed the expected user outcome.");
  if (includeHandoff) await page.getByRole("textbox", { name: "Escalation / handoff", exact: true }).fill("Owning team received the evidence and next step.");
}

async function runTerminalCommand(page, command) {
  const terminal = page.locator(".xterm");
  await terminal.click();
  await page.keyboard.type(command);
  await page.keyboard.press("Enter");
}

test("Week 3 Windows case keeps evidence collapsed and works at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await login(page);
  const mock = await mockCase(page, casePayload({
    week: 3,
    domain: "Windows host",
    title: "Windows Command-Line Diagnostics",
    complaint: "My computer is extremely slow and one application keeps failing.",
    panels: [
      { id: "processes", label: "Task Manager", fields: [{ label: "Memory", value: "91% used" }] },
      { id: "events", label: "Event Viewer", fields: [{ label: "Event", value: "Allocation failure" }] },
      { id: "storage", label: "Storage", fields: [{ label: "Free", value: "184 GB" }] },
      { id: "usb", label: "Device history", fields: [{ label: "Signal", value: "Irrelevant headset event" }] },
    ],
    required: ["processes", "events", "storage"],
  }));
  await page.goto(`/labs/${mock.labId}`);
  await expect(page.getByText("91% used", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Diagnosis — supported by the evidence", { exact: true })).toHaveCount(0);
  for (const name of ["Task Manager", "Event Viewer", "Storage"]) await page.getByRole("tab", { name }).click();
  await expect(page.getByText("Diagnosis — supported by the evidence", { exact: true })).toBeVisible();
  const widths = await page.evaluate(() => ({ client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(widths.scroll).toBeLessThanOrEqual(widths.client + 1);
});

test("Week 6 access case requires the user-group-token-permission evidence chain", async ({ page }) => {
  await login(page);
  const mock = await mockCase(page, casePayload({
    week: 6,
    domain: "Directory",
    title: "Make the Safe Access Decision",
    complaint: "A new employee can sign in but cannot open the department share.",
    panels: ["User object", "Directory groups", "Current token", "Resource permissions"].map((label, index) => ({ id: ["user", "groups", "token", "permissions"][index], label, fields: [{ label: "State", value: `${label} evidence` }] })),
    required: ["user", "groups", "token", "permissions"],
    scenarios: [{ key: "inc2505", ticket_id: "INC2505", label: "Shared-drive access ticket", note: "Existing optional assessment." }],
  }));
  await page.goto(`/labs/${mock.labId}`);
  for (const name of ["User object", "Directory groups", "Current token", "Resource permissions"]) await page.getByRole("tab", { name }).click();
  await expect(page.getByRole("link", { name: /INC2505: Shared-drive access ticket/ })).toHaveAttribute("href", "/service-desk/tickets/INC2505");
  await answerSupported(page);
  await page.getByRole("button", { name: "Run simulated verification" }).click();
  expect(mock.verification().inspected_panel_ids.sort()).toEqual(["groups", "permissions", "token", "user"]);
});

test("Week 15 GPO terminal reports filtering and does not treat refresh as healthy", async ({ page }) => {
  await login(page);
  const terminal = {
    id: "gpo-case",
    prompt: "PS C:\\Support> ",
    intro: "Focused GPO case.",
    help_topics: ["Resultant policy", "Directory placement"],
    commands: [
      { command: "gpupdate /force", output: ["User Policy update completed successfully.", "Finance Drive Map remains filtered: Denied (Security)."] },
      { command: "gpresult /r", inspection_id: "terminal:gpresult", output: ["Finance Drive Map", "Filtering: Denied (Security)"] },
    ],
  };
  const mock = await mockCase(page, casePayload({
    week: 15,
    domain: "Group Policy",
    title: "Diagnose the Group Policy Result",
    complaint: "A Finance employee is missing an expected mapped drive.",
    panels: [{ id: "directory", label: "Directory placement", fields: [{ label: "OU", value: "Finance Users" }] }, { id: "gpo", label: "GPO scope", fields: [{ label: "Filter", value: "Finance eligibility" }] }],
    required: ["directory", "gpo", "terminal:gpresult"],
    terminal,
  }));
  await page.goto(`/labs/${mock.labId}`);
  await page.getByRole("tab", { name: "Directory placement" }).click();
  await page.getByRole("tab", { name: "GPO scope" }).click();
  await runTerminalCommand(page, "gpupdate /force");
  await expect(page.locator(".xterm-rows")).toContainText("remains filtered: Denied (Security)");
  await expect(page.getByText("Diagnosis — supported by the evidence", { exact: true })).toHaveCount(0);
  await runTerminalCommand(page, "gpresult /r");
  await expect(page.locator(".xterm-rows")).toContainText("Filtering: Denied (Security)");
  await expect(page.getByText("Diagnosis — supported by the evidence", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("Incident-specific state verified")).toHaveCount(0);
  await expect(page.getByText("Diagnosis — supported by the evidence", { exact: true })).toHaveCount(0);
});

test("Week 16 PowerShell case depends on incident state and rejects the wrong plan", async ({ page }) => {
  await login(page);
  const mock = await mockCase(page, casePayload({
    week: 16,
    domain: "Windows Server",
    title: "Investigate with PowerShell First",
    complaint: "The payroll application cannot connect to its database after maintenance.",
    panels: [{ id: "change", label: "Maintenance record", fields: [{ label: "Retired DNS", value: "10.20.99.10" }] }],
    required: ["change", "terminal:net-ip", "terminal:dns"],
    terminal: {
      id: "dns-case",
      intro: "Focused server DNS case.",
      help_topics: ["IP and resolver state", "Name resolution", "Port reachability"],
      commands: [
        { command: "Get-NetIPConfiguration", inspection_id: "terminal:net-ip", output: ["DNSServer : 10.20.99.10"] },
        { command: "Resolve-DnsName db01.nexus.internal", inspection_id: "terminal:dns", output: ["Server: 10.20.99.10", "Query timed out."] },
      ],
    },
  }));
  await page.goto(`/labs/${mock.labId}`);
  await page.getByRole("tab", { name: "Maintenance record" }).click();
  await runTerminalCommand(page, "Get-Service");
  await expect(page.locator(".xterm-rows")).toContainText("unavailable in this focused case");
  await expect(page.getByText("Diagnosis — supported by the evidence", { exact: true })).toHaveCount(0);
  await runTerminalCommand(page, "Get-NetIPConfiguration");
  await runTerminalCommand(page, "Resolve-DnsName db01.nexus.internal");
  await expect(page.locator(".xterm-rows")).toContainText("Query timed out");
  await page.getByText("Diagnosis — supported by the evidence", { exact: true }).click();
  await page.getByRole("button", { name: "Continue investigation" }).click();
  await page.getByText("Safe action — broad unsupported shortcut", { exact: true }).click();
  await page.getByRole("button", { name: "Continue investigation" }).click();
  await page.getByText("Verification — supported by the evidence", { exact: true }).click();
  await page.getByRole("button", { name: "Run simulated verification" }).click();
  await expect(page.getByRole("alert")).toContainText("did not produce the expected state");
  await expect(page.getByText("Incident-specific state verified")).toHaveCount(0);
});

test("Week 17 prove case requires layered verification notes and a handoff", async ({ page }) => {
  await login(page);
  const mock = await mockCase(page, casePayload({
    week: 17,
    domain: "Windows Server",
    title: "Verify the Server Recovery Plan",
    complaint: "A department synchronization service stopped updating records overnight.",
    prove: true,
    handoff: true,
    panels: [{ id: "change", label: "Change record", fields: [{ label: "Change", value: "Service password rotated" }] }, { id: "backup", label: "Recovery readiness", fields: [{ label: "Backup", value: "Successful" }] }],
    required: ["change", "backup", "terminal:service", "terminal:event"],
    terminal: {
      id: "service-case",
      intro: "Focused service case.",
      help_topics: ["Service state", "Relevant event log"],
      commands: [
        { command: "Get-Service NexusDeptSync", inspection_id: "terminal:service", output: ["Stopped NexusDeptSync"] },
        { command: "Get-WinEvent -MaxEvents 5", inspection_id: "terminal:event", output: ["The user name or password is incorrect."] },
      ],
    },
  }));
  await page.goto(`/labs/${mock.labId}`);
  await expect(page.getByText("Prove case", { exact: true })).toBeVisible();
  await expect(page.getByText("Investigation hint:")).toHaveCount(0);
  await page.getByRole("tab", { name: "Change record" }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("tab", { name: "Recovery readiness" }).click();
  await runTerminalCommand(page, "Get-Service NexusDeptSync");
  await runTerminalCommand(page, "Get-WinEvent -MaxEvents 5");
  await answerSupported(page);
  await page.getByRole("button", { name: "Run simulated verification" }).click();
  await documentCase(page);
  await expect(page.getByRole("button", { name: "Submit evidence case" })).toBeDisabled();
  await page.getByRole("textbox", { name: "Escalation / handoff", exact: true }).fill("Identity Operations owns the credential update and received the event evidence.");
  await page.getByRole("button", { name: "Submit evidence case" }).click();
  await expect(page.getByText("Server-graded result: 100%")).toBeVisible();
  const notes = JSON.parse(mock.submission().notes);
  expect(Object.keys(notes).sort()).toEqual(["action", "evidence", "handoff", "issue", "verification"]);
});
