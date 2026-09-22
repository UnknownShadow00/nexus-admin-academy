import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import LabPage from "./LabPage";
import { getLab } from "../services/api";
vi.mock("../services/api", async (original) => ({ ...await original(), getLab: vi.fn() }));
vi.mock("../monitoring/sentry", () => ({ setMonitoringContext: vi.fn() }));
afterEach(cleanup);
beforeEach(() => vi.resetAllMocks());
const lab = { id: 1, title: "Available lab", lab_type: "guided", status: "not_started", hints: [] };
const locked = { response: { data: { code: "PREREQUISITE_NOT_MET", error: "Finish your current week", data: { next_action_route: "/learning-path" } } } };
function mount(path = "/labs/1") {
  render(<MemoryRouter initialEntries={[path]}><Link to="/labs/1">First lab</Link><Link to="/labs/2">Second lab</Link><Routes><Route path="/labs/:labId" element={<LabPage />} /></Routes></MemoryRouter>);
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
