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
  beforeEach(() => { api.getV2Lesson.mockResolvedValue(response); api.completeV2Lesson.mockResolvedValue({ data: { status: "completed" } }); api.recordV2Resource.mockResolvedValue({ data: {} }); vi.spyOn(window, "open").mockImplementation(() => null); });
  it("renders safe Markdown and records deliberate resource completion", async () => {
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/lessons/lesson.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/lessons/:lessonKey" element={<V2LessonPage />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Dynamic lesson" })).toBeVisible();
    expect(screen.getByText("ipconfig")).toBeVisible();
    expect(screen.getByText("Required")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Mark completed" }));
    expect(api.recordV2Resource).toHaveBeenCalledWith("module.dynamic", "resource.dynamic", { completed: true }, { suppressToast: true });
  });
});
