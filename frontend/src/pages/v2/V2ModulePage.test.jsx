import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ getV2Module: vi.fn() }));
vi.mock("../../services/api", () => api);
import V2ModulePage from "./V2ModulePage";

const data = {
  certification: { name: "Example Cert", version: { exam_codes: ["EX-1"] }, domain: { title: "Support" } },
  module: { key: "module.dynamic", title: "A module from the API", description: "A useful skill promise." },
  lessons: [
    { key: "lesson.dynamic.one", title: "First dynamic lesson", estimated_minutes: 8, importance: "job_critical", progress: { status: "completed" } },
    { key: "lesson.dynamic.two", title: "Second dynamic lesson", estimated_minutes: 9, progress: { status: "not_started" } },
  ],
  assessments: [
    { key: "quiz.dynamic", role: "module_quiz", title: "Module Quiz", question_count: 7, pass_percent: 70, available: true, progress: { status: "not_started" } },
  ],
  explain_prompts: [],
  progress: { lessons: { completed: 1, total: 2 }, quick_checks: { completed: 0, total: 2 }, module_quiz: null, practical: null, service_desk: null, explain_prompts: { completed: 0, total: 0 } },
  continue: { label: "Continue learning", route: "/next-dynamic", title: "Second dynamic lesson" },
};

describe("V2ModulePage", () => {
  beforeEach(() => api.getV2Module.mockResolvedValue({ data }));
  it("renders curriculum and Continue entirely from the API", async () => {
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey" element={<V2ModulePage />} /><Route path="/next-dynamic" element={<p>Next activity</p>} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "A module from the API" })).toBeVisible();
    expect(screen.getByText("First dynamic lesson")).toBeVisible();
    expect(screen.getByText("Second dynamic lesson")).toBeVisible();
    expect(screen.getByRole("link", { name: /Continue learning/ })).toHaveAttribute("href", "/next-dynamic");
    expect(api.getV2Module).toHaveBeenCalledWith("module.dynamic", { suppressToast: true });
  });
  it("shows a readable API error instead of a blank screen", async () => {
    api.getV2Module.mockRejectedValueOnce({ userMessage: "Network unavailable" });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey" element={<V2ModulePage />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("alert")).toHaveTextContent("Network unavailable");
    await waitFor(() => expect(screen.getByRole("button", { name: "Try again" })).toBeVisible());
  });
  it("explains why an unavailable activity is locked and what to do next", async () => {
    api.getV2Module.mockResolvedValueOnce({ data: { ...data, assessments: [{ key: "practical", role: "practical", title: "Hands-on practical", available: false, unavailable: { reason: "This activity has not been prepared for students yet.", required_action: "Choose another available activity in this module." }, progress: { status: "not_started" } }] } });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey" element={<V2ModulePage />} /></Routes></MemoryRouter>);
    expect(await screen.findByLabelText("Hands-on practical unavailable")).toHaveTextContent("This activity has not been prepared for students yet.");
    expect(screen.getByLabelText("Hands-on practical unavailable")).toHaveTextContent("Choose another available activity");
  });
});
