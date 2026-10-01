import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";
import { getV2Module } from "../../services/api";
import V2NextStep from "./V2NextStep";
vi.mock("../../services/api", async (original) => ({ ...await original(), getV2Module: vi.fn() }));
beforeEach(() => vi.clearAllMocks());

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
