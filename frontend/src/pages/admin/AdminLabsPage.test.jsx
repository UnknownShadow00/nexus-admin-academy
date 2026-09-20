import { cleanup, render, screen } from "@testing-library/react";
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
});
