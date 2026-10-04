import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
  afterEach(cleanup);
  it("renders curriculum and Continue entirely from the API", async () => {
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey" element={<V2ModulePage />} /><Route path="/next-dynamic" element={<p>Next activity</p>} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "A module from the API" })).toBeVisible();
    expect(screen.getByText("First dynamic lesson")).toBeVisible();
    expect(screen.getByText("Second dynamic lesson")).toBeVisible();
    expect(screen.getByText("Completed")).toBeVisible();
    expect(screen.queryByText("Mastered")).not.toBeInTheDocument();
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
  it("shows mentor review separately from the next learning stage and lists every practical", async () => {
    api.getV2Module.mockResolvedValueOnce({ data: {
      ...data,
      certification: { ...data.certification, version: { key: "nexus_beginner_aplus_v1", label: "Beginner", exam_codes: [] } },
      assessments: [
        { key: "first", role: "practical", title: "First practical", available: true, progress: { status: "needs_review" } },
        { key: "second", role: "practical", title: "Second practical", available: true, progress: { status: "passed" } },
      ],
      progress: { ...data.progress, status: "awaiting_mentor_review", continuation_granted: true },
      continue: { kind: "next_stage", label: "Continue learning", title: "Next stage", route: "/learning-v2/modules/module.nexus.beginner.stage2" },
    } });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey" element={<V2ModulePage />} /></Routes></MemoryRouter>);
    expect(await screen.findByText("Awaiting mentor review. You can keep learning.")).toBeVisible();
    expect(screen.getByRole("link", { name: /Continue learning/ })).toHaveAttribute("href", "/learning-v2/modules/module.nexus.beginner.stage2");
    expect(screen.getAllByText("First practical").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Second practical").length).toBeGreaterThan(0);
  });
  it("does not claim later stage access before a continuation grant exists", async () => {
    api.getV2Module.mockResolvedValueOnce({ data: {
      ...data,
      certification: { ...data.certification, version: { key: "nexus_beginner_aplus_v1", exam_codes: [] } },
      progress: { ...data.progress, status: "awaiting_mentor_review", continuation_granted: false },
    } });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey" element={<V2ModulePage />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "A module from the API" })).toBeVisible();
    expect(screen.queryByText("Awaiting mentor review. You can keep learning.")).not.toBeInTheDocument();
  });
  it("does not claim later stage access at the terminal stage even with a grant", async () => {
    api.getV2Module.mockResolvedValueOnce({ data: {
      ...data,
      certification: { ...data.certification, version: { key: "nexus_beginner_aplus_v1", exam_codes: [] } },
      progress: { ...data.progress, status: "awaiting_mentor_review", continuation_granted: true },
      continue: { kind: "review_pending", label: "Awaiting mentor review", route: "/learning-v2/modules/module.dynamic/practical/observation" },
    } });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey" element={<V2ModulePage />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "A module from the API" })).toBeVisible();
    expect(screen.queryByText("Awaiting mentor review. You can keep learning.")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Continue learning" })).not.toBeInTheDocument();
  });
  it("keeps correction feedback and resubmit action while a rejected practical is being edited", async () => {
    api.getV2Module.mockResolvedValueOnce({ data: {
      ...data,
      certification: { ...data.certification, version: { key: "nexus_beginner_aplus_v1", exam_codes: [] } },
      assessments: [{ key: "correction", role: "practical", title: "Correct this practical", available: true,
        progress: { status: "in_progress", detail: { review_decision: "reject", review_feedback: "Show the application view" } } }],
      progress: { ...data.progress, status: "needs_correction", continuation_granted: true },
      continue: { kind: "next_stage", label: "Continue learning", route: "/learning-v2/modules/next" },
    } });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey" element={<V2ModulePage />} /></Routes></MemoryRouter>);
    expect(await screen.findByText("Needs correction. Show the application view")).toBeVisible();
    expect(screen.getByRole("link", { name: /Fix & resubmit/ })).toHaveAttribute("href", "/learning-v2/modules/module.dynamic/practical/correction");
    expect(screen.getByRole("link", { name: /Continue learning/ })).toHaveAttribute("href", "/learning-v2/modules/next");
  });
});
