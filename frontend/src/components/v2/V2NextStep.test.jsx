import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { getV2Module } from "../../services/api";
import V2NextStep from "./V2NextStep";
vi.mock("../../services/api", async (original) => ({ ...await original(), getV2Module: vi.fn() }));
beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

it("routes directly to the server-selected next activity", async () => {
  getV2Module.mockResolvedValue({ data: { continue: { route: "/learning-v2/modules/stage4/assessments/final", label: "Continue with checkpoint", kind: "module_quiz" } } });
  render(<MemoryRouter><V2NextStep moduleKey="stage4" /></MemoryRouter>);
  expect(await screen.findByRole("link", { name: /Continue with checkpoint/ })).toHaveAttribute("href", "/learning-v2/modules/stage4/assessments/final");
});

it("sends a waiting learner to My Course instead of looping back into the practical", async () => {
  getV2Module.mockResolvedValue({ data: { continue: { route: "/learning-v2/modules/stage4/practical/observation", label: "Awaiting mentor review", kind: "review_pending" } } });
  render(<MemoryRouter><V2NextStep moduleKey="stage4" /></MemoryRouter>);
  expect(await screen.findByRole("link", { name: /Done · My Course/ })).toHaveAttribute("href", "/learning-v2");
});

it("shows saved practical copy without promising a terminal stage successor", async () => {
  getV2Module.mockResolvedValue({ data: { continue: { route: "/learning-v2/modules/stage4/practical/observation", label: "Awaiting mentor review", kind: "review_pending" } } });
  render(<MemoryRouter><V2NextStep moduleKey="stage4" pendingReview /></MemoryRouter>);
  expect(await screen.findByText(/Your practical is saved/)).toBeVisible();
  expect(screen.queryByText(/You can keep learning/)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Done · My Course/ })).toHaveAttribute("href", "/learning-v2");
});

it("offers the server-selected successor while mentor review is pending", async () => {
  getV2Module.mockResolvedValue({ data: { continue: { route: "/learning-v2/modules/stage5", label: "Continue learning", kind: "next_stage" } } });
  render(<MemoryRouter><V2NextStep moduleKey="stage4" pendingReview /></MemoryRouter>);
  expect(await screen.findByText(/You can keep learning/)).toBeVisible();
  expect(screen.getByRole("link", { name: /Continue learning/ })).toHaveAttribute("href", "/learning-v2/modules/stage5");
});
