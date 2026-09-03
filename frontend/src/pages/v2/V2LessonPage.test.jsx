import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ completeV2Lesson: vi.fn(), getV2Lesson: vi.fn(), recordV2Resource: vi.fn() }));
vi.mock("../../services/api", () => api);
import V2LessonPage from "./V2LessonPage";

const response = { data: {
  certification: { name: "Example Cert" }, module: { key: "module.dynamic", title: "Dynamic module" },
  lesson: { key: "lesson.dynamic", title: "Dynamic lesson", importance: "job_critical", estimated_minutes: 10, content_markdown: "## What is this?\n\nUse `ipconfig`.\n\n| Command | Use |\n|---|---|\n| ipconfig | View config |", progress: { status: "not_started" }, resources: [{ key: "resource.dynamic", title: "Dynamic resource", provider: "Provider", type: "documentation", required: true, url: "https://example.test/resource", completed: false }], quick_check: { key: "qc.dynamic", title: "Quick Check", question_count: 4, progress: { status: "not_started" } } },
  previous_lesson_key: null, next_lesson_key: "lesson.next",
} };

describe("V2LessonPage", () => {
  beforeEach(() => { response.data.lesson.progress.status = "not_started"; response.data.lesson.resources[0].opened_at = null; response.data.lesson.resources[0].completed = false; api.getV2Lesson.mockResolvedValue(response); api.completeV2Lesson.mockImplementation(async () => { response.data.lesson.progress.status = "completed"; return { data: { status: "completed" } }; }); api.recordV2Resource.mockImplementation(async (_module, _resource, activity) => { if (activity.opened) response.data.lesson.resources[0].opened_at = "2026-09-03T00:00:00Z"; if (activity.completed) response.data.lesson.resources[0].completed = true; return { data: {} }; }); vi.spyOn(window, "open").mockImplementation(() => null); });
  it("renders safe Markdown and records deliberate resource completion", async () => {
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/lessons/lesson.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/lessons/:lessonKey" element={<V2LessonPage />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Dynamic lesson" })).toBeVisible();
    expect(screen.getByText("ipconfig")).toBeVisible();
    expect(screen.getByText("Required")).toBeVisible();
    await userEvent.click(screen.getByRole("link", { name: /Open required resource/ }));
    await userEvent.click(await screen.findByRole("button", { name: "I finished this" }));
    expect(api.recordV2Resource).toHaveBeenCalledWith("module.dynamic", "resource.dynamic", { completed: true }, { suppressToast: true });
  });
  it("makes completion primary before completion and Next lesson primary after saving", async () => {
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/lessons/lesson.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/lessons/:lessonKey" element={<V2LessonPage />} /></Routes></MemoryRouter>);
    await userEvent.click(await screen.findByRole("button", { name: "Mark lesson complete" }));
    expect(await screen.findByText("✓ Completed")).toBeVisible();
    expect(screen.getByRole("link", { name: /Next lesson/ })).toHaveClass("btn-primary");
  });
});
