import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ getV2Learning: vi.fn() }));
vi.mock("../../services/api", () => api);
import V2LearningPage from "./V2LearningPage";

const moduleRow = (key, title, complete = false, completed = 0, version = "CompTIA A+ Core 1 (220-1201)") => ({
  certification: { name: "CompTIA A+", version: { label: version, exam_codes: [version.includes("1202") ? "220-1202" : "220-1201"] } },
  module: { key, title, description: `${title} skills` },
  progress: { module_complete: complete, lessons: { completed, total: 5 }, assessments: {} },
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
    expect(screen.getByText(/Complete · 5\/5 lessons/)).toBeInTheDocument();
  });
  it("uses the current module's Core 2 label without a Core 1 assumption", async () => {
    const current = moduleRow("module.tools", "Windows Support Tools", false, 1, "CompTIA A+ Core 2 (220-1202)");
    api.getV2Learning.mockResolvedValue({ data: { modules: [current], current } });
    render(<MemoryRouter><V2LearningPage /></MemoryRouter>);
    expect(await screen.findByText("CompTIA A+ Core 2 (220-1202) · 220-1202")).toBeInTheDocument();
  });
});
