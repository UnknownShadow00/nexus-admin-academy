import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import LabPage from "./LabPage";
import { getLab, getV2Module, submitV2Lab } from "../services/api";
vi.mock("../services/api", async (original) => ({ ...await original(), getLab: vi.fn(), getV2Module: vi.fn(), submitV2Lab: vi.fn() }));
vi.mock("../monitoring/sentry", () => ({ setMonitoringContext: vi.fn() }));
afterEach(cleanup);
beforeEach(() => { vi.resetAllMocks(); localStorage.clear(); getV2Module.mockResolvedValue({ data: { continue: { route: "/learning-v2", label: "Continue learning" } } }); });
const lab = { id: 1, title: "Available lab", lab_type: "guided", status: "not_started", hints: [] };
const locked = { response: { data: { code: "PREREQUISITE_NOT_MET", error: "Finish your current week", data: { next_action_route: "/learning-path" } } } };
function mount(path = "/labs/1") {
  return render(<MemoryRouter initialEntries={[path]}><Link to="/labs/1">First lab</Link><Link to="/labs/2">Second lab</Link><Routes><Route path="/labs/:labId" element={<LabPage />} /></Routes></MemoryRouter>);
}
it("clears an accessible lab before showing a different lab's lock", async () => {
  getLab.mockResolvedValueOnce({ data: lab }).mockRejectedValueOnce(locked);
  mount();
  await screen.findByRole("heading", { name: "Available lab" });
  fireEvent.click(screen.getByRole("link", { name: "Second lab" }));
  await screen.findByRole("heading", { name: "Lab locked" });
  expect(screen.queryByRole("heading", { name: "Available lab" })).not.toBeInTheDocument();
});
it("clears a stale prerequisite lock when returning to an available lab", async () => {
  getLab.mockRejectedValueOnce(locked).mockResolvedValueOnce({ data: lab });
  mount("/labs/2");
  await screen.findByRole("heading", { name: "Lab locked" });
  fireEvent.click(screen.getByRole("link", { name: "First lab" }));
  await screen.findByRole("heading", { name: "Available lab" });
  expect(screen.queryByText("Finish your current week")).not.toBeInTheDocument();
});
it("ignores a prior lab's response after a route change", async () => {
  let finish;
  getLab.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; })).mockRejectedValueOnce(locked);
  mount();
  fireEvent.click(screen.getByRole("link", { name: "Second lab" }));
  await screen.findByRole("heading", { name: "Lab locked" });
  await act(async () => finish({ data: lab }));
  expect(screen.queryByRole("heading", { name: "Available lab" })).not.toBeInTheDocument();
});
it("presents the Stage 4 practice file and redaction requirements", async () => {
  getLab.mockResolvedValueOnce({ data: {
    ...lab, title: "Stage 4 — Windows observation practical", status: "in_progress", run_id: 42,
    success_criteria: { practice_file_url: "/v2-interactions/nexus-stage4-practice.txt", practice_file_name: "nexus-stage4-practice.txt", tasks: ["Observe the file location"] },
    required_evidence: { mentor_review_required: true, min_artifacts: 2, evidence_types: [{ type: "screenshot" }] },
  } });
  mount("/labs/1?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation");
  expect(await screen.findByRole("link", { name: "Download practice file" })).toHaveAttribute("href", "/v2-interactions/nexus-stage4-practice.txt");
  expect(screen.getByText(/Upload at least 2 screenshots/)).toBeVisible();
  expect(screen.getByRole("textbox", { name: "Reported" })).toBeVisible();
  expect(screen.getByRole("textbox", { name: "Verified / Not verified" })).toBeVisible();
});

it("validates each Stage 4 field, sends structured values, and clears errors after submission", async () => {
  const practical = { ...lab, status: "in_progress", run_id: 42, review: { status: "in_progress" }, required_evidence: { mentor_review_required: true, min_artifacts: 2 }, evidence_artifacts: [{ id: 1, artifact_type: "file_path" }, { id: 2, artifact_type: "windows_observation" }] };
  getLab.mockResolvedValue({ data: practical });
  submitV2Lab.mockRejectedValueOnce({ userMessage: "Temporary submission error" }).mockResolvedValueOnce({ data: { ...practical, status: "submitted", review: { status: "awaiting_mentor_review" } } });
  mount("/labs/1?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation");
  await screen.findByRole("heading", { name: "Stage 4 practical" });
  fireEvent.click(screen.getByRole("button", { name: "Submit practical" }));
  for (const label of ["Reported", "Checked", "Found", "Verified / Not verified", "Next step"]) expect(screen.getByText(`Complete ${label}.`)).toBeVisible();
  const fields = { Reported: "User reports missing file", Checked: "Downloads path", Found: "File visible", "Verified / Not verified": "App issue not reproduced", "Next step": "Ask user to retry" };
  for (const [label, value] of Object.entries(fields)) fireEvent.change(screen.getByRole("textbox", { name: label }), { target: { value } });
  fireEvent.click(screen.getByRole("button", { name: "Submit practical" }));
  expect(await screen.findByText("Temporary submission error")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Submit practical" }));
  expect(await screen.findByRole("heading", { name: "Awaiting mentor review" })).toBeVisible();
  expect(screen.getByText(/You can keep learning/)).toBeVisible();
  expect(screen.queryByText("Temporary submission error")).not.toBeInTheDocument();
  expect(screen.queryByText(/Complete Reported/)).not.toBeInTheDocument();
  expect(submitV2Lab).toHaveBeenLastCalledWith("1", "module.nexus.beginner.stage4", "assess.nexus.beginner.s4.windows_observation", { guided_note: { reported: fields.Reported, checked: fields.Checked, found: fields.Found, verified_or_not_verified: fields["Verified / Not verified"], next_step: fields["Next step"] }, answers: {} });
});

it.each([
  [[], "Upload a File/path evidence screenshot before submitting"],
  [[{ id: 1, artifact_type: "file_path" }], "Upload a Windows/application observation screenshot before submitting"],
])("shows the missing Stage 4 screenshot type for %j", async (evidenceArtifacts, message) => {
  getLab.mockResolvedValue({ data: { ...lab, status: "in_progress", run_id: 42, required_evidence: { mentor_review_required: true, min_artifacts: 2 }, evidence_artifacts: evidenceArtifacts } });
  mount("/labs/1?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation");
  await screen.findByRole("heading", { name: "Stage 4 practical" });
  for (const label of ["Reported", "Checked", "Found", "Verified / Not verified", "Next step"]) fireEvent.change(screen.getByRole("textbox", { name: label }), { target: { value: "Observed safely" } });
  fireEvent.click(screen.getByRole("button", { name: "Submit practical" }));
  expect(screen.getByText(message)).toBeVisible();
  expect(submitV2Lab).not.toHaveBeenCalled();
});

it("shows mentor correction feedback and resubmission action", async () => {
  getLab.mockResolvedValue({ data: { ...lab, status: "in_progress", run_id: 42, review: { status: "needs_correction", feedback: "Show the application view" } } });
  mount("/labs/1?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation");
  expect(await screen.findByText("Mentor feedback: Show the application view")).toBeVisible();
  expect(screen.getByRole("link", { name: "Fix & resubmit" })).toHaveAttribute("href", "#stage4-form");
});

it("keeps Stage 4 field drafts through a page remount", async () => {
  const practical = { ...lab, status: "in_progress", run_id: 42 };
  getLab.mockResolvedValue({ data: practical });
  const path = "/labs/1?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation";
  const view = mount(path);
  fireEvent.change(await screen.findByRole("textbox", { name: "Reported" }), { target: { value: "The file was reported missing" } });
  view.unmount();
  mount(path);
  expect(await screen.findByRole("textbox", { name: "Reported" })).toHaveValue("The file was reported missing");
});

it("restores the five submitted note values for correction", async () => {
  getLab.mockResolvedValue({ data: { ...lab, status: "in_progress", run_id: 42, review: { status: "needs_correction", feedback: "Add the Windows view" }, notes: "Reported: File missing\nChecked: Downloads\nFound: File visible\nVerified / Not verified: Application not reproduced\nNext step: Ask user to retry" } });
  mount("/labs/1?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation");
  expect(await screen.findByRole("textbox", { name: "Reported" })).toHaveValue("File missing");
  expect(screen.getByRole("textbox", { name: "Verified / Not verified" })).toHaveValue("Application not reproduced");
  expect(screen.getByRole("button", { name: "Resubmit practical" })).toBeVisible();
});
