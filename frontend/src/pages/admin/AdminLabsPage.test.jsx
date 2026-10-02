import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  buildApiUrl: vi.fn((path) => `https://api.example.test${path}`),
  createAdminLabTemplate: vi.fn(),
  deleteAdminLabTemplate: vi.fn(),
  getAdminLabTemplates: vi.fn(),
  getAdminV2PracticalReviews: vi.fn(),
  getAdminVmAssignments: vi.fn(),
  reviewAdminV2Practical: vi.fn(),
  updateAdminLabTemplate: vi.fn(),
}));
vi.mock("../../services/api", () => api);
import AdminLabsPage from "./AdminLabsPage";

describe("AdminLabsPage", () => {
  afterEach(cleanup);
  beforeEach(() => {
    api.getAdminLabTemplates.mockResolvedValue({ data: [] });
    api.getAdminVmAssignments.mockResolvedValue({ data: [] });
    api.getAdminV2PracticalReviews.mockResolvedValue({ data: [{
      lab_run_id: 7,
      lab_title: "Guided practical",
      student_name: "Student A",
      stage_title: "Stage 4",
      submitted_at: "2026-09-30T10:00:00Z",
      status: "awaiting_mentor_review",
      notes: "Collected output",
      artifacts: [{
        id: 12,
        artifact_type: "screenshot",
        original_filename: "proof.png",
        file_url: "/api/admin/evidence/12/file",
      }],
    }] });
  });

  it("uses the configured API origin for practical evidence links", async () => {
    render(<AdminLabsPage />);
    expect(await screen.findByRole("link", { name: "proof.png" })).toHaveAttribute(
      "href", "https://api.example.test/api/admin/evidence/12/file",
    );
    expect(api.buildApiUrl).toHaveBeenCalledWith("/api/admin/evidence/12/file");
  });

  it("puts pending reviews first and collects rejection feedback in the page", async () => {
    api.reviewAdminV2Practical.mockResolvedValue({ data: {} });
    render(<AdminLabsPage />);
    expect(await screen.findByRole("heading", { name: /Pending Reviews \/ Grading Queue \(1\)/ })).toBeVisible();
    expect(screen.getByText(/Stage 4 · Awaiting mentor review/)).toBeVisible();
    expect(screen.getByText(/Submitted/)).toBeVisible();
    fireEvent.change(screen.getByRole("textbox", { name: "Mentor feedback" }), { target: { value: "Show the application window" } });
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(api.reviewAdminV2Practical).toHaveBeenCalledWith(7, { decision: "reject", feedback: "Show the application window", rubric_results: {} });
  });
});
