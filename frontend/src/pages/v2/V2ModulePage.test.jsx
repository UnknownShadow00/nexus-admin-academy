import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ getV2Module: vi.fn() }));
vi.mock("../../services/api", () => api);
import V2ModulePage from "./V2ModulePage";

const beginner = { key: "beginner-aplus", name: "Beginner A+ Foundation", version: { key: "nexus_beginner_aplus_v1", label: "Beginner A+" } };
const base = (overrides = {}) => ({
  certification: beginner,
  module: { key: "module.dynamic", title: "Stage 4 — Everyday Windows Support", description: "Practice everyday support work." },
  lessons: [{ key: "lesson.one", title: "Find and protect work", group_status: "in_progress", progress: { status: "not_started" },
    resources: [{ key: "resource.one", title: "Picture — Find without moving", required: true, status: "viewed" }],
    quick_check: { key: "check.one", title: "Checkpoint — Find and protect work", available: true, progress: { status: "passed" } } }],
  interactions: [{ interaction: { key: "practice.one", title: "Locate the supplied file safely", lesson_key: "lesson.one", required: true }, progress: { status: "passed", passed: true } }],
  assessments: [
    { key: "final", role: "module_quiz", title: "Checkpoint — Applications and Windows clues", available: true, progress: { status: "not_started" } },
    { key: "support", role: "practical", title: "Guided practical — Locate, observe, and document", available: true, progress: { status: "not_started" } },
  ],
  module_resources: [], explain_prompts: [],
  progress: { module_complete: false, status: "in_progress", review_due: false },
  continue: { kind: "lesson", label: "Continue learning", title: "Find and protect work", route: "/learning-v2/modules/module.dynamic/lessons/lesson.one" },
  ...overrides,
});
const show = (data = base()) => {
  api.getV2Module.mockResolvedValue({ data });
  return render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic"]}><Routes>
    <Route path="/learning-v2/modules/:moduleKey" element={<V2ModulePage />} />
  </Routes></MemoryRouter>);
};

describe("Stage work plan", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);

  it("follows the authored learning sequence and exposes only one primary next action", async () => {
    show();
    expect(await screen.findByRole("heading", { name: "Stage 4 — Everyday Windows Support" })).toBeVisible();
    const list = screen.getByRole("list", { name: "Stage learning sequence" });
    expect(within(list).getAllByRole("link").map((link) => link.textContent)).toEqual([
      "Find and protect work", "Picture — Find without moving", "Locate the supplied file safely",
      "Checkpoint — Find and protect work", "Checkpoint — Applications and Windows clues", "Guided practical — Locate, observe, and document",
    ]);
    expect(screen.getByRole("link", { name: "Continue learning" })).toHaveAttribute("href", "/learning-v2/modules/module.dynamic/lessons/lesson.one");
    expect(within(list).getByText("Opened")).toBeVisible();
    expect(screen.getByRole("link", { name: "My Course" })).toHaveAttribute("href", "/learning-v2");
    expect(api.getV2Module).toHaveBeenCalledWith("module.dynamic", { suppressToast: true });
  });

  it("uses a learner-facing label for an internal Service Desk reference and keeps its route", async () => {
    const data = base({ assessments: [{ key: "assess.printers.service_desk", role: "service_desk",
      title: "Service Desk — service_desk.aplus.printers.hr_queue", available: true, progress: { status: "not_started" } }],
      continue: { kind: "service_desk", label: "Troubleshoot a ticket",
        title: "Service Desk — service_desk.aplus.printers.hr_queue",
        route: "/learning-v2/modules/module.dynamic/service-desk/assess.printers.service_desk" } });
    show(data);
    const link = await within(await screen.findByRole("list", { name: "Stage learning sequence" })).findByRole("link", { name: "Work a support ticket" });
    expect(link).toHaveAttribute("href", "/learning-v2/modules/module.dynamic/service-desk/assess.printers.service_desk");
    expect(link.closest("li")).toHaveAttribute("aria-current", "step");
    expect(screen.getAllByRole("link", { name: "Troubleshoot a ticket" })).toHaveLength(1);
    expect(screen.queryByText(/service_desk\.aplus\.printers\.hr_queue/)).not.toBeInTheDocument();
  });

  it("keeps the available Service Desk launch link when another activity is up next", async () => {
    const data = base({ assessments: [{ key: "assess.printers.service_desk", role: "service_desk",
      title: "Service Desk — service_desk.aplus.printers.hr_queue", available: true, progress: { status: "not_started" } }] });
    show(data);
    const link = await screen.findByRole("link", { name: "Troubleshoot a ticket" });
    expect(link).toHaveAttribute("href", "/learning-v2/modules/module.dynamic/service-desk/assess.printers.service_desk");
    expect(screen.queryByText(/service_desk\.aplus\.printers\.hr_queue/)).not.toBeInTheDocument();
  });

  it("shows a server-unavailable activity without offering its route", async () => {
    const data = base({ assessments: [{ key: "support", role: "practical", title: "Support practical", available: false,
      unavailable: { reason: "This activity has not been prepared for students yet.", required_action: "Choose another available activity in this module." }, progress: { status: "not_started" } }] });
    show(data);
    const unavailable = await screen.findByLabelText("Support practical unavailable");
    expect(unavailable).toHaveTextContent("This activity has not been prepared for students yet.");
    expect(unavailable).toHaveTextContent("Choose another available activity");
    expect(within(unavailable).queryByRole("link", { name: "Support practical" })).not.toBeInTheDocument();
  });

  it("keeps pending practical follow-up separate from stage mastery and continuation", async () => {
    const data = base({ assessments: [{ key: "support", role: "practical", title: "Support practical", available: true, progress: { status: "needs_review" } }],
      progress: { module_complete: false, status: "awaiting_mentor_review", continuation_granted: true },
      continue: { kind: "next_stage", label: "Continue learning", title: "Next available stage", route: "/learning-v2/modules/real-next" } });
    show(data);
    const followUp = await screen.findByRole("heading", { name: "Mentor follow-up" });
    expect(followUp).toBeVisible();
    expect(screen.getAllByText("With your mentor").length).toBeGreaterThan(0);
    expect(screen.getByText("Not yet mastered")).toBeVisible();
    expect(screen.getByRole("link", { name: "Continue learning" })).toHaveAttribute("href", "/learning-v2/modules/real-next");
  });

  it("shows correction feedback in amber and preserves the practical route", async () => {
    const data = base({ assessments: [{ key: "support", role: "practical", title: "Support practical", available: true,
      progress: { status: "in_progress", detail: { review_decision: "reject", review_feedback: "Show the verified result" } } }],
      progress: { module_complete: false, status: "needs_correction", continuation_granted: true },
      continue: { kind: "next_stage", label: "Continue learning", title: "Next stage", route: "/learning-v2/modules/next" } });
    show(data);
    expect(await screen.findByText("Show the verified result")).toBeVisible();
    expect(screen.getAllByText("Changes requested").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /Fix & resubmit/ })).toHaveAttribute("href", "/learning-v2/modules/module.dynamic/practical/support");
    expect(screen.getByRole("link", { name: "Continue learning" })).toHaveAttribute("href", "/learning-v2/modules/next");
    expect(screen.getByText("You can continue learning in a later stage while this practical is being reviewed or updated.")).toBeVisible();
    expect(screen.queryByText("A later stage is available while this practical is with your mentor.")).not.toBeInTheDocument();
  });

  it("shows Approved practical without claiming stage mastery", async () => {
    const data = base({ assessments: [{ key: "support", role: "practical", title: "Support practical", available: true, progress: { status: "passed" } }],
      progress: { module_complete: false, status: "in_progress" } });
    show(data);
    expect(await screen.findByText("Approved")).toBeVisible();
    expect(screen.getByText("Not yet mastered")).toBeVisible();
    expect(screen.queryByText("Mastered")).not.toBeInTheDocument();
  });

  it("shows Mastered only when the server says so and promises no terminal successor", async () => {
    const data = base({ progress: { module_complete: true, status: "mastered" },
      continue: { kind: "complete", label: "Review module", title: "Module mastered", route: "/learning-v2/modules/module.dynamic" } });
    show(data);
    expect((await screen.findAllByText("Mastered")).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Review stage" })).toHaveAttribute("href", "/learning-v2/modules/module.dynamic");
    expect(screen.queryByText(/Stage 5/)).not.toBeInTheDocument();
  });

  it("keeps a terminal pending stage read-only and avoids a next-stage claim", async () => {
    const data = base({ assessments: [{ key: "support", role: "practical", title: "Support practical", available: true, progress: { status: "needs_review" } }],
      progress: { module_complete: false, status: "awaiting_mentor_review", continuation_granted: true },
      continue: { kind: "review_pending", label: "Awaiting mentor review", title: "Support practical", route: "/learning-v2/modules/module.dynamic/practical/support" } });
    show(data);
    expect(await screen.findByRole("heading", { name: "Mentor follow-up" })).toBeVisible();
    expect(screen.getAllByRole("link", { name: "View practical status" }).length).toBeGreaterThan(0);
    expect(screen.queryByText("A later stage is available while this practical is with your mentor.")).not.toBeInTheDocument();
    expect(screen.queryByText(/Stage 5/)).not.toBeInTheDocument();
  });

  it("preserves non-beginner practical review display and API errors", async () => {
    const data = base({ certification: { key: "aplus", name: "CompTIA A+", version: { key: "core1", label: "Core 1" } },
      assessments: [{ key: "support", role: "practical", title: "Support practical", available: true, progress: { status: "failed", detail: { review_decision: "reject" } } }] });
    show(data);
    expect((await screen.findAllByText("Changes requested")).length).toBeGreaterThan(0);
    expect(screen.getByRole("list", { name: "Module learning sequence" })).toBeVisible();
    cleanup();
    api.getV2Module.mockRejectedValueOnce({ userMessage: "Network unavailable" });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey" element={<V2ModulePage />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("alert")).toHaveTextContent("Network unavailable");
  });
});
