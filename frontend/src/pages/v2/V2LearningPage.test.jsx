import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ getV2Learning: vi.fn() }));
vi.mock("../../services/api", () => api);
import V2LearningPage from "./V2LearningPage";

const moduleRow = (key, title, complete = false, completed = 0, version = "CompTIA A+ Core 1 (220-1201)", status = complete ? "mastered" : completed ? "in_progress" : "not_started") => ({
  certification: { name: "CompTIA A+", version: { label: version, exam_codes: [version.includes("1202") ? "220-1202" : "220-1201"] } },
  module: { key, title, description: `${title} skills` },
  progress: { module_complete: complete, status, lessons: { completed, total: 5 } },
  continue: { label: complete ? "Review module" : "Continue learning", title: title, route: `/learning-v2/modules/${key}` },
});

describe("V2LearningPage multi-module certification view", () => {
  afterEach(cleanup);
  it("renders all modules and one clear continue action", async () => {
    const rows = [
      moduleRow("module.ip", "IP Configuration", true, 5),
      moduleRow("module.hardware", "PC Components", false, 2),
      moduleRow("module.tools", "Windows Support Tools", false, 0, "CompTIA A+ Core 2 (220-1202)"),
      moduleRow("module.triage", "Windows Troubleshooting", false, 0, "CompTIA A+ Core 2 (220-1202)"),
    ];
    api.getV2Learning.mockResolvedValue({ data: { modules: rows, current: rows[1] } });
    render(<MemoryRouter><V2LearningPage /></MemoryRouter>);
    expect((await screen.findAllByRole("heading", { name: "PC Components" })).length).toBeGreaterThan(0);
    expect(screen.getByText("IP Configuration")).toBeInTheDocument();
    expect(screen.getByText("Windows Support Tools")).toBeInTheDocument();
    expect(screen.getByText("Windows Troubleshooting")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Continue learning" })).toHaveAttribute("href", "/learning-v2/modules/module.hardware");
    expect(screen.getAllByText(/Not started/)).toHaveLength(2);
    expect(screen.getByText(/Mastered · 5\/5 lessons/)).toBeInTheDocument();
  });
  it("shows watched and check required from server status without lesson completion", async () => {
    const watched = moduleRow("module.video", "Video foundation", false, 0, undefined, "check_required");
    api.getV2Learning.mockResolvedValue({ data: { modules: [watched], current: watched } });
    render(<MemoryRouter><V2LearningPage /></MemoryRouter>);
    expect(await screen.findByText(/Check required · 0\/5 lessons/)).toBeInTheDocument();
    expect(screen.queryByText(/Not started · 0\/5 lessons/)).not.toBeInTheDocument();
  });
  it("uses the current module's Core 2 label without a Core 1 assumption", async () => {
    const current = moduleRow("module.tools", "Windows Support Tools", false, 1, "CompTIA A+ Core 2 (220-1202)");
    api.getV2Learning.mockResolvedValue({ data: { modules: [current], current } });
    render(<MemoryRouter><V2LearningPage /></MemoryRouter>);
    expect(await screen.findByText("CompTIA A+ Core 2 (220-1202) · 220-1202")).toBeInTheDocument();
  });
  it("shows ordered beginner stages and explains the locked next stage", async () => {
    const first = moduleRow("module.nexus.beginner.stage1", "Stage 1 — What Is IT?");
    const second = moduleRow("module.nexus.beginner.stage2", "Stage 2 — Computer Basics");
    for (const item of [first, second]) {
      item.certification = { name: "Beginner A+ Foundation", version: { key: "nexus_beginner_aplus_v1", label: "Beginner A+ · Version 1", exam_codes: [] } };
      item.progress.lessons.total = 3;
    }
    second.locked = true;
    second.lock_reason = "Finish Stage 1 before starting Stage 2.";
    api.getV2Learning.mockResolvedValue({ data: { modules: [first, second], current: first } });
    render(<MemoryRouter><V2LearningPage /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Your stages" })).toBeVisible();
    expect(screen.getByText("Finish Stage 1 before starting Stage 2.")).toBeVisible();
    expect(screen.queryByRole("link", { name: /Stage 2 — Computer Basics/ })).not.toBeInTheDocument();
    expect(screen.getByText("3 topics")).toBeVisible();
    expect(screen.queryByText(/Version 1/)).not.toBeInTheDocument();
  });
  it("shows Stage 4 without inventing later stage cards", async () => {
    const stages = [1, 2, 3, 4].map((number) => moduleRow(`module.nexus.beginner.stage${number}`, `Stage ${number} — ${number === 4 ? "Everyday Windows Support" : "Foundation"}`));
    for (const item of stages) {
      item.certification = { name: "Beginner A+ Foundation", version: { key: "nexus_beginner_aplus_v1", label: "Beginner A+ · Version 1", exam_codes: [] } };
      item.progress.lessons.total = 3;
    }
    stages[3].locked = true;
    stages[3].lock_reason = "Finish Stage 3 before starting Stage 4.";
    api.getV2Learning.mockResolvedValue({ data: { modules: stages, current: stages[2] } });
    render(<MemoryRouter><V2LearningPage /></MemoryRouter>);
    expect(await screen.findByText("Stages 1–4 · Start here")).toBeVisible();
    expect(screen.getByText("Finish Stage 3 before starting Stage 4.")).toBeVisible();
    expect(screen.queryByText(/Stage 5/)).not.toBeInTheDocument();
  });
  it("keeps a pending earlier stage visible while the server selects newer learning", async () => {
    const older = moduleRow("module.nexus.beginner.stage1", "Stage 1", false, 3, "Beginner", "awaiting_mentor_review");
    const current = moduleRow("module.nexus.beginner.stage2", "Stage 2", false, 0, "Beginner", "not_started");
    for (const item of [older, current]) {
      item.certification = { name: "Beginner A+", version: { key: "nexus_beginner_aplus_v1", label: "Beginner", exam_codes: [] } };
    }
    older.progress.continuation_granted = true;
    older.continue = { kind: "next_stage", label: "Continue learning", route: "/learning-v2/modules/module.nexus.beginner.stage2" };
    api.getV2Learning.mockResolvedValue({ data: { modules: [older, current], current, corrections: [] } });
    render(<MemoryRouter><V2LearningPage /></MemoryRouter>);
    expect(await screen.findByText("You can keep learning.")).toBeVisible();
    expect(screen.getByRole("link", { name: "Continue learning" })).toHaveAttribute("href", "/learning-v2/modules/module.nexus.beginner.stage2");
  });
  it("does not promise later learning for a pending terminal stage", async () => {
    const terminal = moduleRow("module.nexus.beginner.stage4", "Stage 4", false, 3, "Beginner", "awaiting_mentor_review");
    terminal.certification = { name: "Beginner A+", version: { key: "nexus_beginner_aplus_v1", label: "Beginner", exam_codes: [] } };
    terminal.progress.continuation_granted = true;
    terminal.continue = { kind: "review_pending", label: "Awaiting mentor review", title: "Practical review", route: "/learning-v2/modules/module.nexus.beginner.stage4/practical/observation" };
    api.getV2Learning.mockResolvedValue({ data: { modules: [terminal], current: terminal, corrections: [] } });
    render(<MemoryRouter><V2LearningPage /></MemoryRouter>);
    expect(await screen.findByText("In progress · 5 topics")).toBeVisible();
    expect(screen.getAllByText("With your mentor").length).toBeGreaterThan(0);
    expect(screen.queryByText("You can keep learning.")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Continue learning" })).not.toBeInTheDocument();
  });
});
