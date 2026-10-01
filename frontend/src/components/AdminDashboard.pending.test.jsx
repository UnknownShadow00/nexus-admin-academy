import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it, vi } from "vitest";
vi.mock("./CohortPanel", () => ({ default: () => null }));
vi.mock("../services/api", async (original) => ({ ...await original(), getAdminV2PracticalReviews: vi.fn().mockResolvedValue({ data: [{ lab_run_id: 1 }, { lab_run_id: 2 }] }) }));
import AdminDashboard from "./AdminDashboard";

it("shows the pending review count with a direct grading queue link", async () => {
  render(<MemoryRouter><AdminDashboard /></MemoryRouter>);
  expect(await screen.findByLabelText("2 pending reviews")).toBeVisible();
  expect(screen.getByRole("link", { name: /Pending Reviews \/ Grading Queue/ })).toHaveAttribute("href", "/admin/labs#pending-reviews");
});
