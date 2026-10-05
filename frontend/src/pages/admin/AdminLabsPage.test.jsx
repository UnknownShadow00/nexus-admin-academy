import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  buildApiUrl: vi.fn((path) => `https://api.example.test${path}`),
  createAdminLabTemplate: vi.fn(), deleteAdminLabTemplate: vi.fn(),
  getAdminLabTemplates: vi.fn(), getAdminV2PracticalReviews: vi.fn(),
  getAdminVmAssignments: vi.fn(), reviewAdminV2Practical: vi.fn(),
  updateAdminLabTemplate: vi.fn(),
}));
vi.mock("../../services/api", () => api);
import AdminLabsPage from "./AdminLabsPage";
import { parseSupportNote } from "./MentorPracticalReview";

const note = "Reported: File was missing\nChecked: Documents folder\nFound: Wrong path\nVerified / Not verified: User confirmed file\nNext step: Record final location";
const review = (id = 7) => ({
  lab_run_id: id, lab_title: `Guided practical ${id}`, student_name: `Student ${id}`,
  stage_title: "Stage 4", submitted_at: "2026-09-30T10:00:00Z", status: "awaiting_mentor_review", notes: note,
  mentor_rubric: { performed_evidence: "Evidence shows the task", safety: "Safe actions" },
  artifacts: [
    { id: id * 10, artifact_type: "file_path", original_filename: "proof.png", mime_type: "image/png", file_size_bytes: 2400, file_url: `/api/admin/evidence/${id * 10}/file` },
    { id: id * 10 + 1, artifact_type: "windows_observation", original_filename: "application-view.png", mime_type: "image/png", file_url: `/api/admin/evidence/${id * 10 + 1}/file` },
  ],
});

beforeEach(() => {
  vi.clearAllMocks();
  api.getAdminLabTemplates.mockResolvedValue({ data: [] });
  api.getAdminVmAssignments.mockResolvedValue({ data: [] });
  api.getAdminV2PracticalReviews.mockResolvedValue({ data: [review()] });
});
afterEach(cleanup);

describe("mentor practical review workspace", () => {
  it("keeps existing lab template and VM assignment statuses visible", async () => {
    api.getAdminLabTemplates.mockResolvedValue({ data: [{ id: 1, title: "Windows support lab", is_published: true }] });
    api.getAdminVmAssignments.mockResolvedValue({ data: [{ id: 2, student_name: "Student 7", lab_title: "Windows support lab", status: "in_progress" }] });
    render(<AdminLabsPage />);
    expect(await screen.findAllByText("Windows support lab")).toHaveLength(2);
    expect(screen.getByText("Published")).toBeVisible();
    expect(screen.getByText("In progress")).toBeVisible();
  });

  it("shows queue, actual submission data, evidence, structured note and separate decision", async () => {
    render(<AdminLabsPage />);
    expect(await screen.findByRole("heading", { name: "Guided practical 7" })).toBeVisible();
    expect(screen.getByRole("navigation", { name: "Pending practical submissions" })).toBeVisible();
    expect(screen.getByRole("button", { name: /Student 7/ })).toHaveAttribute("aria-current", "true");
    expect(screen.getByText("File was missing")).toBeVisible();
    expect(screen.getByText("User confirmed file")).toBeVisible();
    expect(screen.getByRole("button", { name: "Preview proof.png" })).toBeVisible();
    expect(screen.getAllByRole("link", { name: "Open file" })[0]).toHaveAttribute("href", "https://api.example.test/api/admin/evidence/70/file");
    expect(screen.getByRole("button", { name: "Preview application-view.png" })).toBeVisible();
    expect(screen.getByText("Pending review", { exact: true })).toBeVisible();
    expect(screen.getByRole("button", { name: "Approve practical" })).toBeDisabled();
  });

  it("keeps old free-text notes readable", async () => {
    expect(parseSupportNote(note)).toHaveLength(5);
    expect(parseSupportNote("Old free text")).toBeNull();
    api.getAdminV2PracticalReviews.mockResolvedValue({ data: [{ ...review(), notes: "Old free text" }] });
    render(<AdminLabsPage />);
    expect(await screen.findByText("Old free text")).toBeVisible();
  });

  it("keeps an authorized file action when an image thumbnail fails", async () => {
    render(<AdminLabsPage />);
    await screen.findByRole("heading", { name: "Guided practical 7" });
    fireEvent.error(screen.getByRole("button", { name: "Preview proof.png" }).querySelector("img"));
    expect(screen.queryByRole("button", { name: "Preview proof.png" })).not.toBeInTheDocument();
    expect(screen.getByText("NO PREVIEW")).toBeVisible();
    expect(screen.getAllByRole("link", { name: "Open file" })[0]).toHaveAttribute("href", "https://api.example.test/api/admin/evidence/70/file");
  });

  it("explains an empty evidence response without inventing a file", async () => {
    api.getAdminV2PracticalReviews.mockResolvedValue({ data: [{ ...review(), artifacts: [] }] });
    render(<AdminLabsPage />);
    expect(await screen.findByText("No uploaded evidence appears with this submission.")).toBeVisible();
  });

  it("distinguishes loading, empty, and failed queue fetch", async () => {
    api.getAdminV2PracticalReviews.mockImplementationOnce(() => new Promise(() => {}));
    const pending = render(<AdminLabsPage />);
    expect(screen.getByText("Loading pending reviews…")).toBeVisible();
    pending.unmount();
    api.getAdminV2PracticalReviews.mockResolvedValueOnce({ data: [] });
    const empty = render(<AdminLabsPage />);
    expect(await screen.findByText("No practicals are waiting for review.")).toBeVisible();
    empty.unmount();
    api.getAdminV2PracticalReviews.mockRejectedValueOnce(new Error("Unavailable"));
    render(<AdminLabsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Pending reviews could not be loaded");
    expect(screen.queryByText("No practicals are waiting for review.")).not.toBeInTheDocument();
  });

  it("selects another learner without carrying note or rubric decisions across", async () => {
    api.getAdminV2PracticalReviews.mockResolvedValue({ data: [review(7), review(8)] });
    render(<AdminLabsPage />);
    await screen.findByRole("heading", { name: "Guided practical 7" });
    fireEvent.change(screen.getByRole("textbox", { name: "Mentor feedback" }), { target: { value: "Feedback for seven" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /performed evidence/ }));
    fireEvent.click(screen.getByRole("button", { name: /Student 8/ }));
    expect(screen.getByRole("heading", { name: "Guided practical 8" })).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Mentor feedback" })).toHaveValue("");
    expect(screen.getByRole("checkbox", { name: /performed evidence/ })).not.toBeChecked();
  });

  it("requests changes with feedback using the existing reject API value", async () => {
    api.reviewAdminV2Practical.mockResolvedValue({ data: { status: "failed" } });
    api.getAdminV2PracticalReviews.mockResolvedValueOnce({ data: [review()] }).mockResolvedValueOnce({ data: [] });
    render(<AdminLabsPage />);
    await screen.findByRole("heading", { name: "Guided practical 7" });
    fireEvent.click(screen.getByRole("button", { name: "Request changes" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Write mentor feedback");
    fireEvent.change(screen.getByRole("textbox", { name: "Mentor feedback" }), { target: { value: "Show the application window" } });
    fireEvent.click(screen.getByRole("button", { name: "Request changes" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm decision" }));
    await waitFor(() => expect(api.reviewAdminV2Practical).toHaveBeenCalledWith(7, { decision: "reject", feedback: "Show the application window", rubric_results: {} }));
    expect(await screen.findByText("No practicals are waiting for review.")).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("Changes requested");
    expect(screen.getByRole("status")).toHaveClass("notice-correction");
  });

  it("requires each server rubric criterion for approval and does not claim mastery", async () => {
    api.reviewAdminV2Practical.mockResolvedValue({ data: { status: "passed" } });
    api.getAdminV2PracticalReviews.mockResolvedValueOnce({ data: [review()] }).mockResolvedValueOnce({ data: [] });
    render(<AdminLabsPage />);
    await screen.findByRole("heading", { name: "Guided practical 7" });
    fireEvent.change(screen.getByRole("textbox", { name: "Mentor feedback" }), { target: { value: "Evidence is clear" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /performed evidence/ }));
    expect(screen.getByRole("button", { name: "Approve practical" })).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: /safety/ }));
    fireEvent.click(screen.getByRole("button", { name: "Approve practical" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm decision" }));
    await waitFor(() => expect(api.reviewAdminV2Practical).toHaveBeenCalledWith(7, { decision: "approve", feedback: "Evidence is clear", rubric_results: { performed_evidence: true, safety: true } }));
    expect(await screen.findByRole("status")).toHaveTextContent("Approved Student 7’s Guided practical 7");
    expect(screen.getByRole("status")).toHaveClass("notice-success");
    expect(screen.queryByText(/Mastered/)).not.toBeInTheDocument();
  });

  it("preserves feedback if the API rejects a decision", async () => {
    api.reviewAdminV2Practical.mockRejectedValue({ userMessage: "Review conflict", response: { status: 409 } });
    render(<AdminLabsPage />);
    await screen.findByRole("heading", { name: "Guided practical 7" });
    fireEvent.change(screen.getByRole("textbox", { name: "Mentor feedback" }), { target: { value: "Please revise" } });
    fireEvent.click(screen.getByRole("button", { name: "Request changes" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm decision" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("changed during review");
    expect(screen.getByRole("textbox", { name: "Mentor feedback" })).toHaveValue("Please revise");
  });
});
