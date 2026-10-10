import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ completeV2Lesson: vi.fn(), getV2Lesson: vi.fn(), getV2Module: vi.fn(), recordV2Resource: vi.fn() }));
vi.mock("../../services/api", () => api);
import V2LessonPage from "./V2LessonPage";

const response = { data: {
  certification: { name: "Example Cert" }, module: { key: "module.dynamic", title: "Dynamic module" },
  lesson: { key: "lesson.dynamic", title: "Dynamic lesson", importance: "job_critical", estimated_minutes: 10, content_markdown: "## What is this?\n\nUse `ipconfig`.\n\n| Command | Use |\n|---|---|\n| ipconfig | View config |", progress: { status: "not_started" }, resources: [{ key: "resource.dynamic", title: "Dynamic resource", provider: "Provider", type: "video", required: true, url: "https://example.test/resource", watched_at: null, status: "not_started" }], quick_check: { key: "qc.dynamic", title: "Quick Check", question_count: 4, progress: { status: "not_started" } } },
  previous_lesson_key: null, next_lesson_key: "lesson.next",
} };

describe("V2LessonPage", () => {
  afterEach(cleanup);
  beforeEach(() => { response.data.certification = { name: "Example Cert" }; response.data.lesson.progress.status = "not_started"; response.data.lesson.quick_check.available = true; response.data.lesson.resources[0].opened_at = null; response.data.lesson.resources[0].watched_at = null; response.data.lesson.resources[0].status = "not_started"; api.getV2Lesson.mockResolvedValue(response); api.getV2Module.mockResolvedValue({ data: { continue: { route: "/learning-v2/modules/module.dynamic/assessments/qc.dynamic", label: "Continue with Quick Check" } } }); api.completeV2Lesson.mockImplementation(async () => { response.data.lesson.progress.status = "completed"; return { data: { status: "completed" } }; }); api.recordV2Resource.mockImplementation(async (_module, _resource, activity) => { if (activity.opened) response.data.lesson.resources[0].opened_at = "2026-09-03T00:00:00Z"; if (activity.watched) { response.data.lesson.resources[0].watched_at = "2026-09-03T00:01:00Z"; response.data.lesson.resources[0].status = "watched"; }; return { data: {} }; }); vi.spyOn(window, "open").mockImplementation(() => null); });
  it("renders safe Markdown and records self-reported video viewing without mastery", async () => {
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/lessons/lesson.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/lessons/:lessonKey" element={<V2LessonPage />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Dynamic lesson" })).toBeVisible();
    expect(screen.getByText("ipconfig")).toBeVisible();
    expect(screen.getByText("video · Required")).toBeVisible();
    await userEvent.click(screen.getByRole("link", { name: /Open video/ }));
    await userEvent.click(await screen.findByRole("button", { name: "I watched this" }));
    expect(api.recordV2Resource).toHaveBeenCalledWith("module.dynamic", "resource.dynamic", { watched: true }, { suppressToast: true });
    expect(await screen.findByText("Watched (self reported). Viewing alone does not grant mastery.")).toBeVisible();
    expect(screen.queryByText("Mastered")).not.toBeInTheDocument();
  });
  it("makes completion primary before completion and Next lesson primary after saving", async () => {
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/lessons/lesson.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/lessons/:lessonKey" element={<V2LessonPage />} /></Routes></MemoryRouter>);
    await userEvent.click(await screen.findByRole("button", { name: "Mark lesson complete" }));
    expect(await screen.findByRole("heading", { name: "Lesson done" })).toBeVisible();
    expect(screen.getByText("Lesson completion tracks navigation; checks and practice determine mastery.")).toBeVisible();
    expect(screen.getByRole("link", { name: /Next lesson/ })).toHaveClass("btn-primary");
  });
  it("does not link to an unavailable quick check", async () => {
    response.data.lesson.quick_check.available = false;
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/lessons/lesson.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/lessons/:lessonKey" element={<V2LessonPage />} /></Routes></MemoryRouter>);
    expect(await screen.findByText("Quick Check unavailable")).toBeVisible();
    expect(screen.queryByRole("link", { name: "Start Quick Check" })).not.toBeInTheDocument();
  });
  it("keeps the beginner group focused on practice and the checkpoint", async () => {
    response.data.certification.version = { key: "nexus_beginner_aplus_v1", label: "Beginner A+ · Version 1" };
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/lessons/lesson.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/lessons/:lessonKey" element={<V2LessonPage />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Dynamic lesson" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Mark lesson complete" })).not.toBeInTheDocument();
    expect(await screen.findByRole("link", { name: /Continue with Quick Check/ })).toHaveAttribute("href", "/learning-v2/modules/module.dynamic/assessments/qc.dynamic");
    expect(screen.getByRole("link", { name: "Start Quick Check" })).toBeVisible();
  });
  it("refreshes a Nexus teaching resource and group to Viewed after opening", async () => {
    const lessonData = structuredClone(response.data);
    lessonData.certification.version = { key: "nexus_beginner_aplus_v1" };
    lessonData.lesson.group_status = "not_started";
    lessonData.lesson.resources = [{ key: "res.nexus.beginner.s4.clues", title: "Teaching card", provider: "Nexus", type: "reference", required: true, url: "/v2-interactions/beginner-s4-clues.svg", opened_at: null, status: "not_started", exposure_satisfied: false }];
    api.getV2Lesson.mockImplementation(async () => ({ data: structuredClone(lessonData) }));
    api.recordV2Resource.mockImplementation(async () => {
      lessonData.lesson.resources[0] = { ...lessonData.lesson.resources[0], opened_at: "2026-09-03T00:00:00Z", status: "viewed", exposure_satisfied: true };
      lessonData.lesson.group_status = "viewed";
      return { data: { status: "viewed" } };
    });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/lessons/lesson.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/lessons/:lessonKey" element={<V2LessonPage />} /></Routes></MemoryRouter>);
    await userEvent.click(await screen.findByRole("button", { name: "View teaching card" }));
    await userEvent.click(screen.getByRole("button", { name: "Close teaching card" }));
    await waitFor(() => expect(screen.getAllByText("Opened").length).toBeGreaterThanOrEqual(2));
    expect(screen.getByRole("button", { name: "View again" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Start Quick Check" })).toBeVisible();
  });
  it("retains lesson content when the optional module list fails and retries that list", async () => {
    api.getV2Module.mockRejectedValueOnce(new Error("offline")).mockResolvedValue({ data: { lessons: [{ key: "lesson.dynamic", title: "Dynamic lesson", progress: { status: "not_started" } }] } });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/lessons/lesson.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/lessons/:lessonKey" element={<V2LessonPage />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Dynamic lesson" })).toBeVisible();
    await userEvent.click(await screen.findByRole("button", { name: "Retry lesson list" }));
    expect(await screen.findByText("Lesson 1 of 1")).toBeVisible();
  });
  it("keeps content and completion controls after a rejected completion request", async () => {
    api.completeV2Lesson.mockRejectedValue({ userMessage: "Finish required practice first." });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/lessons/lesson.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/lessons/:lessonKey" element={<V2LessonPage />} /></Routes></MemoryRouter>);
    await userEvent.click(await screen.findByRole("button", { name: "Mark lesson complete" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Finish required practice first.");
    expect(screen.getByRole("heading", { name: "Dynamic lesson" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Lesson done" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mark lesson complete" })).toBeEnabled();
  });
  it("ignores a late lesson response after navigation to another lesson", async () => {
    let finish;
    api.getV2Lesson.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; })).mockResolvedValueOnce({ data: { ...response.data, lesson: { ...response.data.lesson, title: "Current lesson" } } });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/lessons/lesson.dynamic"]}><Link to="/learning-v2/modules/module.dynamic/lessons/lesson.next">Other lesson</Link><Routes><Route path="/learning-v2/modules/:moduleKey/lessons/:lessonKey" element={<V2LessonPage />} /></Routes></MemoryRouter>);
    await userEvent.click(screen.getByRole("link", { name: "Other lesson" }));
    expect(await screen.findByRole("heading", { name: "Current lesson" })).toBeVisible();
    finish(response);
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Dynamic lesson" })).not.toBeInTheDocument());
  });
});
