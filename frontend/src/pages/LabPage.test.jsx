import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import LabPage from "./LabPage";
import { getLab, getV2Module, startV2Lab, submitV2Lab, uploadLabEvidence } from "../services/api";
vi.mock("../services/api", async (original) => ({ ...await original(), getLab: vi.fn(), getV2Module: vi.fn(), startV2Lab: vi.fn(), submitV2Lab: vi.fn(), uploadLabEvidence: vi.fn() }));
vi.mock("../monitoring/sentry", () => ({ setMonitoringContext: vi.fn() }));
afterEach(cleanup);
beforeEach(() => { vi.resetAllMocks(); localStorage.clear(); getV2Module.mockResolvedValue({ data: { continue: { route: "/learning-v2", label: "Continue learning" } } }); });
const lab = { id: 1, title: "Available lab", lab_type: "guided", status: "not_started", hints: [] };
const stage4Lab = { ...lab, title: "Stage 4 — Windows observation practical", description: "Observe the approved Windows device.", setup_instructions: "Use only an authorized account." };
const practicalPath = "/labs/1?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation";
const bothScreenshots = [{ id: 1, artifact_type: "file_path", original_filename: "file-path.png" }, { id: 2, artifact_type: "windows_observation", original_filename: "windows-view.png" }];
const completeNotes = "Reported: File missing\nChecked: Downloads\nFound: File visible\nVerified / Not verified: Application not reproduced\nNext step: Ask user to retry";
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
    ...stage4Lab, status: "in_progress", run_id: 42,
    success_criteria: { practice_file_url: "/v2-interactions/nexus-stage4-practice.txt", practice_file_name: "nexus-stage4-practice.txt", tasks: ["Observe the file location"] },
    required_evidence: { mentor_review_required: true, min_artifacts: 2, evidence_types: [{ type: "screenshot" }] },
  } });
  mount("/labs/1?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation");
  expect(await screen.findByRole("link", { name: "Download practice file" })).toHaveAttribute("href", "/v2-interactions/nexus-stage4-practice.txt");
  expect(screen.getByText(/Upload a redacted screenshot of the file and path/)).toBeVisible();
  expect(screen.getByRole("textbox", { name: "Reported" })).toBeVisible();
  expect(screen.getByRole("textbox", { name: "Verified / Not verified" })).toBeVisible();
  const sectionNav = screen.getByRole("navigation", { name: "Practical sections" });
  expect(sectionNav.getElementsByTagName("a")[0]).toHaveAttribute("aria-current", "location");
  fireEvent.click(screen.getByRole("link", { name: /Capture evidence/ }));
  expect(screen.getByRole("link", { name: /Capture evidence/ })).toHaveAttribute("aria-current", "location");
});

it("validates each Stage 4 field, sends structured values, and clears errors after submission", async () => {
  const practical = { ...stage4Lab, status: "in_progress", run_id: 42, review: { status: "in_progress" }, required_evidence: { mentor_review_required: true, min_artifacts: 2 }, evidence_artifacts: [{ id: 1, artifact_type: "file_path" }, { id: 2, artifact_type: "windows_observation" }] };
  getLab.mockResolvedValue({ data: practical });
  submitV2Lab.mockRejectedValueOnce({ userMessage: "Temporary submission error" }).mockResolvedValueOnce({ data: { ...practical, status: "submitted", notes: "Reported: User reports missing file\nChecked: Downloads path\nFound: File visible\nVerified / Not verified: App issue not reproduced\nNext step: Ask user to retry", review: { status: "awaiting_mentor_review" } } });
  mount("/labs/1?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation");
  await screen.findByRole("heading", { name: "Stage 4 — Windows observation practical" });
  fireEvent.click(screen.getByRole("button", { name: "Send to mentor" }));
  for (const label of ["Reported", "Checked", "Found", "Verified / Not verified", "Next step"]) expect(screen.getByText(`Complete ${label}.`)).toBeVisible();
  const fields = { Reported: "User reports missing file", Checked: "Downloads path", Found: "File visible", "Verified / Not verified": "App issue not reproduced", "Next step": "Ask user to retry" };
  for (const [label, value] of Object.entries(fields)) fireEvent.change(screen.getByRole("textbox", { name: label }), { target: { value } });
  fireEvent.click(screen.getByRole("button", { name: "Send to mentor" }));
  expect(await screen.findByText("Temporary submission error")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Send to mentor" }));
  expect(await screen.findByRole("heading", { name: "With your mentor" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Submitted for review" })).toBeVisible();
  expect(screen.queryByRole("heading", { name: "Review & send" })).not.toBeInTheDocument();
  expect(screen.getByText(/Your practical was sent to your mentor/)).toBeVisible();
  expect(screen.queryByText(/You can keep learning/)).not.toBeInTheDocument();
  expect(await screen.findByRole("link", { name: /Back to My Course/ })).toHaveAttribute("href", "/learning-v2");
  expect(screen.queryByText(/Done · My Course/)).not.toBeInTheDocument();
  expect(screen.getByRole("textbox", { name: "Reported" })).toHaveAttribute("readonly");
  expect(screen.getByRole("textbox", { name: "Reported" })).toHaveValue(fields.Reported);
  expect(screen.queryByRole("button", { name: "Send to mentor" })).not.toBeInTheDocument();
  expect(screen.queryByText("Temporary submission error")).not.toBeInTheDocument();
  expect(screen.queryByText(/Complete Reported/)).not.toBeInTheDocument();
  expect(submitV2Lab).toHaveBeenLastCalledWith("1", "module.nexus.beginner.stage4", "assess.nexus.beginner.s4.windows_observation", { guided_note: { reported: fields.Reported, checked: fields.Checked, found: fields.Found, verified_or_not_verified: fields["Verified / Not verified"], next_step: fields["Next step"] }, answers: {} });
});

it.each([
  [[], "Upload a File/path evidence screenshot before submitting"],
  [[{ id: 1, artifact_type: "file_path" }], "Upload a Windows/application observation screenshot before submitting"],
])("shows the missing Stage 4 screenshot type for %j", async (evidenceArtifacts, message) => {
  getLab.mockResolvedValue({ data: { ...stage4Lab, status: "in_progress", run_id: 42, required_evidence: { mentor_review_required: true, min_artifacts: 2 }, evidence_artifacts: evidenceArtifacts } });
  mount("/labs/1?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation");
  await screen.findByRole("heading", { name: "Stage 4 — Windows observation practical" });
  for (const label of ["Reported", "Checked", "Found", "Verified / Not verified", "Next step"]) fireEvent.change(screen.getByRole("textbox", { name: label }), { target: { value: "Observed safely" } });
  fireEvent.click(screen.getByRole("button", { name: "Send to mentor" }));
  expect(screen.getByText(message)).toBeVisible();
  expect(submitV2Lab).not.toHaveBeenCalled();
});

it("shows mentor correction feedback and resubmission action", async () => {
  getLab.mockResolvedValue({ data: { ...stage4Lab, status: "in_progress", run_id: 42, review: { status: "needs_correction", feedback: "Show the application view" } } });
  mount("/labs/1?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation");
  expect(await screen.findByRole("heading", { name: "Changes requested" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Review & resubmit" })).toBeVisible();
  expect(screen.getByText("Show the application view")).toBeVisible();
  expect(screen.getByRole("link", { name: "Update your practical" })).toHaveAttribute("href", "#practical-support-note");
});

it("calls an approved practical Approved without claiming stage mastery", async () => {
  getLab.mockResolvedValue({ data: { ...stage4Lab, status: "submitted", review: { status: "passed" } } });
  mount("/labs/1?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation");
  expect(await screen.findByRole("heading", { name: "Approved" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Approved submission" })).toBeVisible();
  expect(screen.getByText(/stage is mastered only when the remaining requirements are complete/)).toBeVisible();
  expect(screen.queryByText("Stage mastered")).not.toBeInTheDocument();
});

it("keeps Stage 4 field drafts through a page remount", async () => {
  const practical = { ...stage4Lab, status: "in_progress", run_id: 42 };
  getLab.mockResolvedValue({ data: practical });
  const path = "/labs/1?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation";
  const view = mount(path);
  fireEvent.change(await screen.findByRole("textbox", { name: "Reported" }), { target: { value: "The file was reported missing" } });
  view.unmount();
  mount(path);
  expect(await screen.findByRole("textbox", { name: "Reported" })).toHaveValue("The file was reported missing");
});

it("restores the five submitted note values for correction", async () => {
  getLab.mockResolvedValue({ data: { ...stage4Lab, status: "in_progress", run_id: 42, review: { status: "needs_correction", feedback: "Add the Windows view" }, notes: "Reported: File missing\nChecked: Downloads\nFound: File visible\nVerified / Not verified: Application not reproduced\nNext step: Ask user to retry" } });
  mount("/labs/1?v2Module=module.nexus.beginner.stage4&v2Assessment=assess.nexus.beginner.s4.windows_observation");
  expect(await screen.findByRole("textbox", { name: "Reported" })).toHaveValue("File missing");
  expect(screen.getByRole("textbox", { name: "Verified / Not verified" })).toHaveValue("Application not reproduced");
  expect(screen.getByRole("button", { name: "Resubmit to mentor" })).toBeVisible();
});

it("starts an empty practical without discarding the browser draft", async () => {
  getLab.mockResolvedValue({ data: stage4Lab });
  startV2Lab.mockResolvedValue({ data: { ...stage4Lab, status: "in_progress", run_id: 42 } });
  mount(practicalPath);
  fireEvent.change(await screen.findByRole("textbox", { name: "Reported" }), { target: { value: "User cannot find the file" } });
  fireEvent.click(screen.getByRole("button", { name: "Start practical" }));
  await waitFor(() => expect(startV2Lab).toHaveBeenCalledWith("1", "module.nexus.beginner.stage4", "assess.nexus.beginner.s4.windows_observation"));
  expect(screen.getByRole("textbox", { name: "Reported" })).toHaveValue("User cannot find the file");
  expect(screen.getByRole("button", { name: "Send to mentor" })).toBeEnabled();
});

it("shows the uploaded evidence types and filenames without pretending to offer a server preview or delete", async () => {
  getLab.mockResolvedValue({ data: { ...stage4Lab, status: "in_progress", run_id: 42, evidence_artifacts: bothScreenshots } });
  mount(practicalPath);
  expect(await screen.findByText("file-path.png")).toBeVisible();
  expect(screen.getByText("windows-view.png")).toBeVisible();
  expect(screen.getByText("Both screenshot types uploaded")).toBeVisible();
  expect(screen.queryByRole("button", { name: /remove uploaded/i })).not.toBeInTheDocument();
});

it("uploads the selected screenshot under its actual evidence type and advances to the other type", async () => {
  getLab.mockResolvedValue({ data: { ...stage4Lab, status: "in_progress", run_id: 42, required_evidence: { evidence_types: [{ type: "screenshot" }] } } });
  uploadLabEvidence.mockResolvedValue({ data: { artifact_id: 7, storage_key: "generated.png" } });
  mount(practicalPath);
  const file = new File(["image"], "path.png", { type: "image/png" });
  fireEvent.change(await screen.findByLabelText("Choose a screenshot"), { target: { files: [file] } });
  fireEvent.click(screen.getByRole("button", { name: "Upload screenshot" }));
  await waitFor(() => expect(uploadLabEvidence).toHaveBeenCalledWith(42, file, "file_path"));
  expect(await screen.findByText("path.png")).toBeVisible();
  expect(screen.getByRole("combobox", { name: "Evidence shown in this screenshot" })).toHaveValue("windows_observation");
  expect(screen.getByText("Screenshot uploaded")).toBeVisible();
});

it("keeps the selected file and shows an error when upload fails", async () => {
  getLab.mockResolvedValue({ data: { ...stage4Lab, status: "in_progress", run_id: 42, required_evidence: { evidence_types: [{ type: "screenshot" }] } } });
  uploadLabEvidence.mockRejectedValue({ userMessage: "Upload temporarily unavailable" });
  mount(practicalPath);
  fireEvent.change(await screen.findByLabelText("Choose a screenshot"), { target: { files: [new File(["image"], "path.png", { type: "image/png" })] } });
  fireEvent.click(screen.getByRole("button", { name: "Upload screenshot" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Upload temporarily unavailable");
  expect(screen.getByRole("button", { name: "Upload screenshot" })).toBeEnabled();
  expect(screen.getByText("No screenshots uploaded yet.")).toBeVisible();
});

it("shows the actual submitted note read-only while with the mentor", async () => {
  getLab.mockResolvedValue({ data: { ...stage4Lab, status: "submitted", run_id: 42, review: { status: "awaiting_mentor_review" }, notes: completeNotes, evidence_artifacts: bothScreenshots } });
  mount(practicalPath);
  expect(await screen.findByRole("heading", { name: "With your mentor" })).toBeVisible();
  expect(screen.getByRole("textbox", { name: "Found" })).toHaveValue("File visible");
  expect(screen.getByRole("textbox", { name: "Found" })).toHaveAttribute("readonly");
  expect(screen.getByText("file-path.png")).toBeVisible();
  expect(screen.queryByRole("button", { name: "Upload screenshot" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Send to mentor" })).not.toBeInTheDocument();
  expect(screen.queryByText("Stage mastered")).not.toBeInTheDocument();
});

it("only offers continuing learning during mentor review when the server supplies a successor", async () => {
  getLab.mockResolvedValue({ data: { ...stage4Lab, status: "submitted", run_id: 42, review: { status: "awaiting_mentor_review" }, notes: completeNotes } });
  getV2Module.mockResolvedValue({ data: { continue: { kind: "next_stage", label: "Continue Stage 4", route: "/learning-v2/modules/module.nexus.beginner.stage4" } } });
  mount(practicalPath);
  expect(await screen.findByText(/You can keep learning while your mentor reviews it/)).toBeVisible();
  expect(screen.getByRole("link", { name: /Continue Stage 4/ })).toHaveAttribute("href", "/learning-v2/modules/module.nexus.beginner.stage4");
});

it("resubmits edited correction values without changing the five-field serialization", async () => {
  const correction = { ...stage4Lab, status: "in_progress", run_id: 42, review: { status: "needs_correction", feedback: "Add the Windows view" }, notes: completeNotes, evidence_artifacts: bothScreenshots };
  getLab.mockResolvedValue({ data: correction });
  submitV2Lab.mockResolvedValue({ data: { ...correction, status: "submitted", review: { status: "awaiting_mentor_review" }, notes: completeNotes.replace("Ask user to retry", "Ask user to confirm") } });
  mount(practicalPath);
  fireEvent.change(await screen.findByRole("textbox", { name: "Next step" }), { target: { value: "Ask user to confirm" } });
  fireEvent.click(screen.getByRole("button", { name: "Resubmit to mentor" }));
  expect(await screen.findByRole("heading", { name: "With your mentor" })).toBeVisible();
  expect(submitV2Lab).toHaveBeenCalledWith("1", "module.nexus.beginner.stage4", "assess.nexus.beginner.s4.windows_observation", { guided_note: { reported: "File missing", checked: "Downloads", found: "File visible", verified_or_not_verified: "Application not reproduced", next_step: "Ask user to confirm" }, answers: {} });
  expect(screen.getByRole("textbox", { name: "Next step" })).toHaveValue("Ask user to confirm");
});

it("shows an approved practical as read-only and leaves mastery to the course", async () => {
  getLab.mockResolvedValue({ data: { ...stage4Lab, status: "submitted", run_id: 42, review: { status: "passed" }, notes: completeNotes, evidence_artifacts: bothScreenshots } });
  mount(practicalPath);
  expect(await screen.findByRole("heading", { name: "Approved" })).toBeVisible();
  expect(screen.getByText(/Stage mastery is shown separately in My Course/)).toBeVisible();
  expect(screen.getByRole("textbox", { name: "Reported" })).toHaveAttribute("readonly");
  expect(screen.queryByRole("button", { name: "Send to mentor" })).not.toBeInTheDocument();
  expect(screen.queryByText("Stage mastered")).not.toBeInTheDocument();
});
