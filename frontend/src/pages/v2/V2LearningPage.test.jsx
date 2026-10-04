import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ getV2Learning: vi.fn(), getV2Module: vi.fn() }));
vi.mock("../../services/api", () => api);
import V2LearningPage from "./V2LearningPage";

const beginnerCert = { key: "beginner-aplus", name: "Beginner A+ Foundation", version: { key: "nexus_beginner_aplus_v1", label: "Beginner A+", exam_codes: [] } };
const stage = (number, overrides = {}) => ({
  certification: beginnerCert,
  module: { key: `module.nexus.beginner.stage${number}`, title: `Stage ${number} — ${["", "What Is IT?", "Computer Basics", "Operating Systems", "Everyday Windows Support"][number]}`, description: `Stage ${number} skills` },
  progress: { module_complete: false, status: "not_started", continuation_granted: false, lessons: { completed: 0, total: 3 } },
  continue: { kind: "lesson", label: "Continue learning", title: `Stage ${number} lesson`, route: `/learning-v2/modules/module.nexus.beginner.stage${number}/lessons/first` },
  locked: false,
  ...overrides,
});
const detail = (row, overrides = {}) => ({
  certification: row.certification, module: row.module,
  lessons: [{ key: "first", title: `${row.module.title} lesson`, group_status: "not_started", progress: { status: "not_started" }, resources: [], quick_check: null }],
  interactions: [], assessments: [], explain_prompts: [], progress: row.progress, continue: row.continue,
  ...overrides,
});
const show = (modules, current, corrections = [], currentDetail = detail(current)) => {
  api.getV2Learning.mockResolvedValue({ data: { modules, current, corrections } });
  api.getV2Module.mockResolvedValue({ data: currentDetail });
  return render(<MemoryRouter><V2LearningPage /></MemoryRouter>);
};
const row = (name) => screen.getByRole("article", { name: new RegExp(name) });

describe("My Course path", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);

  it("shows the first available stage as Up next and later locked stages without fake links", async () => {
    const first = stage(1);
    const second = stage(2, { locked: true, lock_reason: "Finish Stage 1 before starting Stage 2." });
    show([first, second], first);
    expect(await screen.findByRole("heading", { name: "Your stages" })).toBeVisible();
    const path = screen.getByRole("region", { name: "Beginner A+ Foundation course path" });
    expect(within(path).getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent)).toEqual([first.module.title, second.module.title]);
    expect(row("Stage 1")).toHaveAttribute("aria-current", "step");
    expect(within(row("Stage 1")).getAllByText("Up next").length).toBeGreaterThan(0);
    expect(within(row("Stage 2")).getByText("Locked")).toBeVisible();
    expect(screen.getByText("Finish Stage 1 before starting Stage 2.")).toBeVisible();
    expect(screen.queryByRole("link", { name: second.module.title })).not.toBeInTheDocument();
    expect(screen.queryByText(/Stage 5|Network\+|Security\+/)).not.toBeInTheDocument();
  });

  it("expands the server-selected current stage with its real lesson and one primary next action", async () => {
    const first = stage(1, { progress: { module_complete: false, status: "in_progress", lessons: { completed: 1, total: 3 } } });
    show([first], first);
    expect(await screen.findByText(`${first.module.title} lesson`)).toBeVisible();
    expect(within(row("Stage 1")).getByText("In progress")).toBeVisible();
    expect(within(row("Stage 1")).getByRole("link", { name: "Continue learning" })).toHaveAttribute("href", first.continue.route);
    expect(api.getV2Module).toHaveBeenCalledWith(first.module.key, { suppressToast: true });
  });

  it("keeps a mastered earlier stage compact while later learning is current", async () => {
    const first = stage(1, { progress: { module_complete: true, status: "mastered", continuation_granted: true, lessons: { completed: 3, total: 3 } } });
    const second = stage(2, { progress: { module_complete: false, status: "in_progress", lessons: { completed: 1, total: 3 } } });
    show([first, second], second);
    expect(await screen.findByText(`${second.module.title} lesson`)).toBeVisible();
    expect(within(row("Stage 1")).getByText("Mastered")).toBeVisible();
    expect(row("Stage 2")).toHaveAttribute("aria-current", "step");
    expect(within(row("Stage 2")).getByText("In progress")).toBeVisible();
    expect(within(row("Stage 1")).queryByText(`${first.module.title} lesson`)).not.toBeInTheDocument();
  });

  it("shows an earlier pending mentor practical in violet while a later stage remains current", async () => {
    const first = stage(1, { progress: { module_complete: false, status: "awaiting_mentor_review", continuation_granted: true, lessons: { completed: 3, total: 3 } } });
    const second = stage(2);
    show([first, second], second);
    expect(await screen.findByText(`${second.module.title} lesson`)).toBeVisible();
    expect(within(row("Stage 1")).getByText("With your mentor")).toBeVisible();
    expect(within(row("Stage 1")).getByText("In progress")).toBeVisible();
    expect(row("Stage 2")).toHaveAttribute("aria-current", "step");
    expect(within(row("Stage 1")).queryByText("Mastered")).not.toBeInTheDocument();
  });

  it("keeps requested changes on the earlier stage with a feedback route and later learning available", async () => {
    const first = stage(3, { progress: { module_complete: false, status: "needs_correction", continuation_granted: true, lessons: { completed: 3, total: 3 } } });
    const current = stage(4);
    const correction = { module_key: first.module.key, assessment_key: "practical", practical_title: "Support practical", feedback: "Show the verified result", route: `/learning-v2/modules/${first.module.key}/practical/practical` };
    show([first, current], current, [correction]);
    expect(await screen.findByText(`${current.module.title} lesson`)).toBeVisible();
    expect(within(row("Stage 3")).getByText("Changes requested")).toBeVisible();
    expect(within(row("Stage 3")).getByRole("link", { name: "Review feedback" })).toHaveAttribute("href", correction.route);
    expect(row("Stage 4")).toHaveAttribute("aria-current", "step");
    expect(within(row("Stage 4")).getByRole("link", { name: "Continue learning" })).toHaveAttribute("href", current.continue.route);
  });

  it("shows a terminal pending practical without mastery or an invented successor", async () => {
    const terminal = stage(4, { progress: { module_complete: false, status: "awaiting_mentor_review", continuation_granted: true, lessons: { completed: 3, total: 3 } },
      continue: { kind: "review_pending", title: "Support practical", route: "/learning-v2/modules/module.nexus.beginner.stage4/practical/support" } });
    show([terminal], terminal);
    expect(await screen.findByText(`${terminal.module.title} lesson`)).toBeVisible();
    expect(within(row("Stage 4")).getByText("With your mentor")).toBeVisible();
    expect(within(row("Stage 4")).getByRole("link", { name: "View practical status" })).toHaveAttribute("href", terminal.continue.route);
    expect(within(row("Stage 4")).queryByText("Mastered")).not.toBeInTheDocument();
    expect(screen.queryByText(/Stage 5/)).not.toBeInTheDocument();
  });

  it("keeps Approved practical distinct from stage mastery", async () => {
    const current = stage(4, { progress: { module_complete: false, status: "in_progress", lessons: { completed: 3, total: 3 } } });
    show([current], current, [], detail(current, { assessments: [{ key: "support", role: "practical", title: "Support practical", available: true, progress: { status: "passed" } }] }));
    expect(await screen.findByText("Support practical")).toBeVisible();
    expect(within(row("Stage 4")).getByText("Approved")).toBeVisible();
    expect(within(row("Stage 4")).queryByText("Mastered")).not.toBeInTheDocument();
  });

  it("shows Mastered only from server module_complete", async () => {
    const current = stage(4, { progress: { module_complete: true, status: "mastered", continuation_granted: true, lessons: { completed: 3, total: 3 } }, continue: { kind: "complete", title: "Module mastered", route: "/learning-v2/modules/module.nexus.beginner.stage4" } });
    show([current], current);
    expect(await screen.findByRole("heading", { name: current.module.title, level: 3 })).toBeVisible();
    expect(within(row("Stage 4")).getByText("Mastered")).toBeVisible();
    expect(within(row("Stage 4")).getByText("Completed stage")).toBeVisible();
    expect(screen.getByText(`${current.module.title} is mastered. Review your completed learning below.`)).toBeVisible();
    expect(screen.queryByText(/Stage 5/)).not.toBeInTheDocument();
  });

  it("keeps non-beginner modules from real data without a future-program selector", async () => {
    const current = stage(1, { certification: { key: "aplus", name: "CompTIA A+", version: { key: "aplus-core2", label: "CompTIA A+ Core 2 (220-1202)", exam_codes: ["220-1202"] } }, module: { key: "module.tools", title: "Windows Support Tools", description: "Support Windows" } });
    show([current], current);
    expect(await screen.findByRole("heading", { name: "CompTIA A+", level: 1 })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Your modules" })).toBeVisible();
    expect(screen.queryByText(/Network\+|Security\+/)).not.toBeInTheDocument();
  });
});
