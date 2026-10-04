import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  checkInStudent: vi.fn(), getStudentStats: vi.fn(), getTrainingDashboard: vi.fn(), getV2Learning: vi.fn(),
}));
vi.mock("../services/api", () => api);
vi.mock("../hooks/useAuth", () => ({ getCurrentStudent: () => ({ id: 42, name: "Taylor" }) }));
vi.mock("../hooks/useV2Access", () => ({ useV2Access: () => ({ studentEnabled: true, loading: false }) }));

import StudentHome, { buildContinueTarget, buildTodayModel } from "./StudentHome";

const stage = (number, next, progress = {}) => ({
  certification: { name: "Beginner A+ Foundation" },
  module: { key: "module.nexus.beginner.stage" + number, title: "Stage " + number + " — Windows Support" },
  progress: { status: "in_progress", module_complete: false, ...progress },
  continue: next,
});
const next = (kind = "lesson", title = "Windows basics", status = "in_progress") => ({
  kind, title, status, route: "/learning-v2/modules/stage4/" + kind,
});
const correction = { module_key: "module.nexus.beginner.stage3", assessment_key: "practical", stage_title: "Stage 3 — Support", practical_title: "Support note", feedback: "Add the verification step.", route: "/learning-v2/modules/stage3/practical/practical" };

function show(learning) {
  api.getV2Learning.mockResolvedValue({ data: learning });
  return render(<MemoryRouter><StudentHome /></MemoryRouter>);
}

beforeEach(() => {
  api.checkInStudent.mockResolvedValue({ data: {} });
  api.getStudentStats.mockResolvedValue({ data: { name: "Taylor" } });
  api.getTrainingDashboard.mockResolvedValue({ data: { current_module: { title: "Earlier training", route: "/learning-path" } } });
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("Today next action", () => {
  it("uses the server continuation route and one descriptive primary action", async () => {
    const current = stage(4, next());
    show({ current, modules: [current], corrections: [] });
    expect(await screen.findByRole("heading", { name: "Windows basics" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Continue lesson" })).toHaveAttribute("href", current.continue.route);
    expect(screen.getByRole("complementary", { name: "Mentor follow-up" })).toHaveTextContent("Nothing waiting right now");
    expect(screen.queryByText(/XP|streak|recent activity/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Network\+|Security\+/i)).not.toBeInTheDocument();
  });

  it("keeps available learning primary while an earlier practical is with the mentor", async () => {
    const pending = stage(3, next("next_stage", "Stage 4", "available"), { status: "awaiting_mentor_review", practical: { assessment_key: "practical", title: "Stage 3 practical", activity: { status: "needs_review" } } });
    const current = stage(4, next());
    show({ current, modules: [pending, current], corrections: [] });
    expect(await screen.findByRole("link", { name: "Continue lesson" })).toHaveAttribute("href", current.continue.route);
    const followUp = screen.getByRole("complementary", { name: "Mentor follow-up" });
    expect(within(followUp).getByText("With your mentor")).toBeInTheDocument();
    expect(within(followUp).getByText(/You can keep learning/)).toBeInTheDocument();
    expect(within(followUp).getByRole("link", { name: "View submission" })).toHaveAttribute("href", "/learning-v2/modules/module.nexus.beginner.stage3/practical/practical");
    expect(buildTodayModel({ current, modules: [pending, current] }).mode).toBe("learning");
  });

  it("shows changes as secondary feedback while learning remains available", async () => {
    const current = stage(4, next());
    show({ current, modules: [current], corrections: [correction] });
    expect(await screen.findByRole("link", { name: "Continue lesson" })).toBeInTheDocument();
    const followUp = screen.getByRole("complementary", { name: "Mentor follow-up" });
    expect(within(followUp).getByText("Changes requested")).toBeInTheDocument();
    expect(within(followUp).getByText(/Add the verification step/)).toBeInTheDocument();
    expect(within(followUp).getByText(/You can keep learning/)).toBeInTheDocument();
    expect(within(followUp).getByRole("link", { name: "See changes" })).toHaveAttribute("href", correction.route);
    expect(followUp.querySelector(".today-follow-up-changes")).toBeInTheDocument();
  });

  it("makes the correction primary only when the server has no learning action", async () => {
    const current = stage(4, next("correction", "Stage 4 practical", "needs_correction"), { status: "needs_correction" });
    const currentCorrection = { ...correction, module_key: current.module.key, stage_title: current.module.title, practical_title: "Stage 4 practical", route: current.continue.route };
    show({ current, modules: [current], corrections: [currentCorrection] });
    expect(await screen.findByRole("link", { name: "Update your practical" })).toHaveAttribute("href", currentCorrection.route);
    expect(screen.getByText(/normal part of the process/)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Update your practical" })).toHaveLength(1);
    expect(screen.queryByText(/keep learning while you update/i)).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Stage 4 practical" })).toHaveTextContent("Add the verification step.");
    expect(screen.queryByRole("complementary", { name: "Mentor follow-up" })).not.toBeInTheDocument();
    expect(buildTodayModel({ current, modules: [current], corrections: [currentCorrection] }).mode).toBe("correction");
  });

  it("describes completed learning awaiting mentor review without claiming mastery", async () => {
    const current = stage(4, next("review_pending", "Stage 4 practical", "needs_review"), { status: "awaiting_mentor_review", practical: { assessment_key: "practical", title: "Stage 4 practical", activity: { status: "needs_review" } } });
    show({ current, modules: [current], corrections: [] });
    expect(await screen.findByRole("heading", { name: "Learning is up to date" })).toBeInTheDocument();
    expect(screen.getAllByText(/practical is with your mentor/i)).toHaveLength(2);
    expect(screen.queryByText(/keep learning while it is reviewed/i)).not.toBeInTheDocument();
    expect(screen.queryByText("Stage mastered")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /next stage/i })).not.toBeInTheDocument();
  });

  it("does not turn approved practical into stage mastery when other requirements remain", () => {
    const current = stage(4, next("evidence", "Stage 4", "passed"), { status: "in_progress", module_complete: false, practical: { activity: { status: "passed" } } });
    expect(buildTodayModel({ current, modules: [current] }).mode).toBe("learning");
    expect(buildContinueTarget({ current }).status).toBe("in_progress");
  });

  it("uses server mastery and does not invent a successor for a terminal stage", async () => {
    const current = stage(4, next("complete", "Module mastered", "mastered"), { status: "mastered", module_complete: true });
    show({ current, modules: [current], corrections: [] });
    expect(await screen.findByText("Stage mastered")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View My Course" })).toHaveAttribute("href", "/learning-v2");
    expect(screen.queryByRole("link", { name: /next stage/i })).not.toBeInTheDocument();
  });

  it("prioritizes an earlier correction when the current stage is mastered and no learning remains", async () => {
    const current = stage(4, next("complete", "Module mastered", "mastered"), { status: "mastered", module_complete: true });
    show({ current, modules: [current], corrections: [correction] });
    expect(await screen.findByRole("link", { name: "Update your practical" })).toHaveAttribute("href", correction.route);
    expect(screen.getByRole("region", { name: "Support note" })).toHaveTextContent("Stage 3 — Support");
    expect(screen.queryByText("Stage mastered")).not.toBeInTheDocument();
  });

  it("follows a real server-provided next stage without inventing one", () => {
    const current = stage(3, next("next_stage", "Stage 4 — Windows Support", "available"), { status: "awaiting_mentor_review", continuation_granted: true });
    current.continue.route = "/learning-v2/modules/module.nexus.beginner.stage4";
    expect(buildTodayModel({ current, modules: [current] }).mode).toBe("learning");
    expect(buildContinueTarget({ current }).to).toBe(current.continue.route);
  });

  it("preserves the active earlier training model's server destination", () => {
    const training = {
      current_module: { stable_id: "module.orientation.nexus", title: "Nexus Orientation", route: "/training/module/module.orientation.nexus", required_complete: 0 },
      current_stage: { title: "Orientation" },
      next_activity: { title: "Welcome to Nexus", activity_label: "Lesson", destination_route: "/lessons/12" },
    };
    expect(buildContinueTarget(null, training)).toMatchObject({ label: "Start Training", title: "Welcome to Nexus", to: "/lessons/12" });
    expect(buildTodayModel(null, training).mode).toBe("learning");
  });

  it("does not call completed legacy training a mastered stage", async () => {
    api.getTrainingDashboard.mockResolvedValue({ data: { current_module: { title: "Nexus Orientation" }, training_complete: true } });
    show(null);
    expect(await screen.findByRole("heading", { name: "Training complete" })).toBeInTheDocument();
    expect(screen.queryByText("Stage mastered")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review training" })).toHaveAttribute("href", "/learning-path");
  });

  it("does not claim learning is available when the server has no current module", () => {
    expect(buildTodayModel(null, null).mode).toBe("up_to_date");
    expect(buildContinueTarget(null, null).to).toBe("/learning-path");
  });
});
