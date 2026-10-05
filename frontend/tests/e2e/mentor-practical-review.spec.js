import { expect, test } from "@playwright/test";

const note = "Reported: A work file was missing\nChecked: Authorized Documents folder\nFound: The file had a different name\nVerified / Not verified: Learner located the file; user confirmation pending\nNext step: Ask the user to confirm";
const item = (id) => ({
  lab_run_id: id, student_id: id + 40, student_name: `Learner ${id}`,
  lab_title: "Stage 4 Windows observation practical", stage_title: "Stage 4 — Everyday Windows Support",
  module_key: "module.nexus.beginner.stage4", assessment_key: "assess.nexus.beginner.s4.windows_observation",
  status: "awaiting_mentor_review", submitted_at: "2026-10-05T01:00:00Z", notes: note,
  mentor_rubric: { performed_evidence: "Evidence shows the task", safety: "Actions were safe" },
  artifacts: [{ id: id * 10, artifact_type: "file_path", original_filename: "redacted-file-view.png", mime_type: "image/png", file_size_bytes: 2000, file_url: `/api/admin/evidence/${id * 10}/file` }],
});

async function fixture(page, { authorized = true, initial = [item(7), item(8)] } = {}) {
  let queue = initial;
  await page.addInitScript(() => localStorage.setItem("theme", "light"));
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/admin/session/status") return route.fulfill({ status: 200, json: { success: true, data: { authenticated: authorized } } });
    if (!authorized) return route.fulfill({ status: 403, json: { detail: "Forbidden" } });
    if (path === "/api/admin/labs/runs/review" && route.request().method() === "GET") return route.fulfill({ status: 200, json: { success: true, data: queue } });
    if (path === "/api/admin/labs/templates") return route.fulfill({ status: 200, json: { success: true, data: [] } });
    if (path === "/api/admin/vms/assignments") return route.fulfill({ status: 200, json: { success: true, data: [] } });
    if (/^\/api\/admin\/labs\/runs\/\d+\/v2-review$/.test(path) && route.request().method() === "POST") {
      const id = Number(path.split("/")[5]);
      const decision = route.request().postDataJSON().decision;
      queue = queue.filter((row) => row.lab_run_id !== id);
      return route.fulfill({ status: 200, json: { success: true, data: { lab_run_id: id, status: decision === "approve" ? "passed" : "failed" } } });
    }
    if (path.startsWith("/api/admin/evidence/")) return route.fulfill({ status: 200, contentType: "image/png", body: Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/GYoAAAAASUVORK5CYII=", "base64") });
    return route.fulfill({ status: 404, json: {} });
  });
}

test("admin reviews a selected learner and requests changes without a false stage decision", async ({ page }) => {
  await fixture(page);
  await page.goto("/admin/labs#pending-reviews");
  await expect(page.getByRole("heading", { name: "Pending practical reviews" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Stage 4 Windows observation practical" })).toBeVisible();
  await expect(page.getByText("A work file was missing")).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve practical" })).toBeDisabled();
  await page.getByRole("button", { name: "Preview redacted-file-view.png" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Preview redacted-file-view.png" })).toBeFocused();
  await page.getByRole("textbox", { name: "Mentor feedback" }).fill("Please include the application window.");
  await page.getByRole("button", { name: "Request changes" }).click();
  await expect(page.getByText("Request changes to Learner 7’s practical?")).toBeVisible();
  await page.getByRole("button", { name: "Confirm decision" }).click();
  await expect(page.getByRole("status")).toContainText("Changes requested for Learner 7");
  await expect(page.getByRole("button", { name: /Learner 7/ })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Learner 8/ })).toBeVisible();
});

test("ordinary learner cannot open mentor review", async ({ page }) => {
  await fixture(page, { authorized: false });
  await page.goto("/admin/labs#pending-reviews");
  await expect(page).toHaveURL(/\/admin-login\?redirect=/);
  await expect(page.getByRole("heading", { name: "Pending practical reviews" })).toHaveCount(0);
});
