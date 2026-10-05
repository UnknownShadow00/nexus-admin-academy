import { expect, test } from "@playwright/test";

const practicalRoute = "/labs/481?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation";
const title = "Stage 4 — Windows observation practical";
const notes = "Reported: File missing\nChecked: Downloads\nFound: Supplied file visible\nVerified / Not verified: File location verified; application issue not reproduced\nNext step: Ask user to confirm";
const artifacts = [
  { id: 17, artifact_type: "file_path", original_filename: "file-path-redacted.png" },
  { id: 18, artifact_type: "windows_observation", original_filename: "application-view-redacted.png" },
];
const lab = {
  id: 481, title, lab_type: "guided", difficulty: 1, week_number: 0, estimated_minutes: 25,
  description: "A user reports a missing work file and unexpected application behavior.",
  setup_instructions: "Use only an authorized Windows computer. Do not alter files or close unsaved work. Redact private details before upload.",
  success_criteria: { practice_file_url: "/v2-interactions/nexus-stage4-practice.txt", practice_file_name: "nexus-stage4-practice.txt", tasks: ["Locate the supplied file in Downloads.", "Observe one read-only Windows clue."] },
  required_evidence: { mentor_review_required: true, min_artifacts: 2, evidence_types: [{ type: "screenshot" }, { type: "screenshot" }] },
  status: "in_progress", run_id: 951, notes: "", evidence_artifacts: [], review: { status: "in_progress" },
};

async function fixture(page, state, continuation = null) {
  await page.addInitScript(() => {
    localStorage.setItem("selected_profile", JSON.stringify({ id: 42, name: "Taylor", email: "taylor@example.invalid" }));
    localStorage.setItem("theme", "light");
  });
  await page.route("**/auth/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data: { student_id: 42, name: "Taylor" } }) }));
  await page.route("**/api/**", (route) => {
    const url = new URL(route.request().url());
    let data;
    if (url.pathname === "/api/v2/curriculum/access") data = { master_enabled: true, student_enabled: true, mode: "beginner" };
    else if (url.pathname === "/api/labs/481") data = state;
    else if (url.pathname.startsWith("/api/v2/curriculum/modules/")) data = { continue: continuation || { kind: "review_pending", route: "/learning-v2", label: "Back to My Course" } };
    else if (url.pathname === "/api/students/42/stats") data = { name: "Taylor" };
    else if (url.pathname === "/api/training") data = { current_module: { title: "Nexus Orientation", route: "/learning-path" } };
    else if (url.pathname === "/api/students/42/check-in") data = {};
    else return route.fulfill({ status: 404, contentType: "application/json", body: "{}" });
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
  });
}

test("draft practical keeps one send action and five labelled technician fields", async ({ page }) => {
  await fixture(page, lab);
  await page.goto(practicalRoute);
  await expect(page.getByRole("heading", { name: title, level: 1 })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Practical sections" }).getByRole("link", { name: /Brief/ })).toHaveAttribute("aria-current", "location");
  for (const label of ["Reported", "Checked", "Found", "Verified / Not verified", "Next step"]) await expect(page.getByRole("textbox", { name: label })).toBeVisible();
  await expect(page.getByRole("button", { name: "Send to mentor" })).toHaveCount(1);
  await expect(page.getByRole("link", { name: "Download practice file" })).toHaveAttribute("href", "/v2-interactions/nexus-stage4-practice.txt");
  await page.getByRole("button", { name: "Send to mentor" }).click();
  await expect(page.getByText("Complete Reported.")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Reported" })).toBeFocused();
});

test("pending practical is read-only, remains in My Course, and has no false successor", async ({ page }) => {
  await fixture(page, { ...lab, status: "submitted", notes, evidence_artifacts: artifacts, review: { status: "awaiting_mentor_review" } });
  await page.goto(practicalRoute);
  await expect(page.getByRole("heading", { name: "With your mentor" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Reported" })).toHaveAttribute("readonly");
  await expect(page.getByText("file-path-redacted.png")).toBeVisible();
  await expect(page.getByRole("button", { name: "Send to mentor" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /Back to My Course/ })).toHaveAttribute("href", "/learning-v2");
  await expect(page.getByText("Stage mastered")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "My Course", exact: true }).first()).toHaveAttribute("aria-current", "page");
});

test("correction shows mentor feedback and keeps editing and resubmission available on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await fixture(page, { ...lab, notes, evidence_artifacts: artifacts, review: { status: "needs_correction", feedback: "Show the application clue more clearly." } });
  await page.goto(practicalRoute);
  await expect(page.getByRole("heading", { name: "Changes requested" })).toBeVisible();
  await expect(page.getByText("Show the application clue more clearly.")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Next step" })).not.toHaveAttribute("readonly");
  await expect(page.getByRole("button", { name: "Resubmit to mentor" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
});
