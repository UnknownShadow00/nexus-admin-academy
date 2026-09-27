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
});
