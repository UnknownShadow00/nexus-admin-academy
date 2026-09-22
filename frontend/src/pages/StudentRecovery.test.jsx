import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import LessonPage from "./LessonPage";
import QuizReviewPage from "./QuizReviewPage";
import TrainingProgressPage from "./TrainingProgressPage";
import OrientationPracticePanel from "../components/OrientationPracticePanel";
import * as api from "../services/api";
vi.mock("../services/api", () => ({ getLesson: vi.fn(), completeLesson: vi.fn(), getLessonNote: vi.fn(), saveLessonNote: vi.fn(), getOrientationProgress: vi.fn(), getWeekPlan: vi.fn(), getQuizReview: vi.fn(), getTrainingProgress: vi.fn(), getServiceDeskProgressSummary: vi.fn() }));
vi.mock("../hooks/useAuth", () => ({ getCurrentStudent: () => ({ id: 7 }) }));
afterEach(cleanup);
beforeEach(() => { vi.resetAllMocks(); localStorage.clear(); api.getLessonNote.mockResolvedValue({ data: { content: "" } }); });
const lesson = { id: 1, title: "Test lesson", summary: "Read this first.", is_complete: false };
const review = { title: "Ticket quiz", score: 1, total: 2, questions: [{ id: 1, question_text: "First question" }, { id: 2, question_text: "Second question" }], results: [{ question_id: 1, student_answer: "A", correct_answer: "A", is_correct: true, options: { A: "Ask first", B: "Guess" }, explanation: "Confirm the problem first." }, { question_id: 2, student_answer: "B", correct_answer: "A", is_correct: false, options: { A: "Document evidence", B: "Skip notes" }, explanation: "Notes help the next technician." }] };
function mountLesson() { return render(<MemoryRouter initialEntries={["/lessons/1"]}><Routes><Route path="/lessons/:lessonId" element={<LessonPage />} /></Routes></MemoryRouter>); }
function mountReview() { return render(<MemoryRouter initialEntries={["/quizzes/1/review"]}><Link to="/quizzes/2/review">Second review</Link><Routes><Route path="/quizzes/:quizId/review" element={<QuizReviewPage />} /></Routes></MemoryRouter>); }
it("shows a retryable lesson failure instead of a false prerequisite lock", async () => {
  api.getLesson.mockRejectedValueOnce({ response: { status: 500 } }).mockResolvedValueOnce({ data: lesson });
  mountLesson();
  await screen.findByRole("heading", { name: "Lesson unavailable" });
  expect(screen.queryByText("Complete remaining work")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Retry lesson" }));
  await screen.findByRole("heading", { name: "Test lesson" });
});
it("preserves the actual prerequisite lock and next action", async () => {
  api.getLesson.mockRejectedValue({ response: { status: 403, data: { data: { next_action_route: "/training/week/1" } } } });
  mountLesson();
  await screen.findByRole("heading", { name: "Lesson locked" });
  expect(screen.getByRole("link", { name: "Complete remaining work" })).toHaveAttribute("href", "/training/week/1");
});
it("does not claim completion after a failed save and lets the learner retry", async () => {
  api.getLesson.mockResolvedValue({ data: lesson });
  api.completeLesson.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ data: {} });
  mountLesson();
  fireEvent.click(await screen.findByRole("button", { name: "Mark lesson complete" }));
  await screen.findByRole("alert");
  expect(screen.queryByRole("button", { name: "Lesson complete" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Mark lesson complete" }));
  expect(await screen.findByRole("button", { name: "Lesson complete" })).toBeDisabled();
});
it("retries an orientation checklist error instead of loading forever", async () => {
  api.getOrientationProgress.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ data: { steps: {}, quiz_route: "/quizzes/42" } });
  render(<MemoryRouter><OrientationPracticePanel /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Retry checklist" }));
  await screen.findByRole("heading", { name: "Two quick steps" });
});
it("keeps a review service failure distinct from having no saved attempt", async () => {
  api.getQuizReview.mockRejectedValueOnce({ response: { status: 500 } }).mockResolvedValueOnce({ data: review });
  mountReview();
  await screen.findByRole("heading", { name: "Quiz review unavailable" });
  expect(screen.queryByRole("link", { name: "Take quiz" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  await screen.findByRole("heading", { name: "Ticket quiz" });
  expect(screen.getByText("Notes help the next technician.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Review missed questions" }));
  expect(screen.queryByText("Q1. First question")).not.toBeInTheDocument();
  expect(screen.getByText("Q2. Second question")).toBeInTheDocument();
  expect(screen.getByText("Incorrect", { exact: true })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Show all questions" }));
  expect(screen.getByText("Q1. First question")).toBeInTheDocument();
});
it("offers a first attempt only when the API confirms that none exists", async () => {
  api.getQuizReview.mockRejectedValue({ response: { status: 404, data: { detail: "No attempt found for this quiz" } } });
  mountReview();
  expect(await screen.findByRole("link", { name: "Take quiz" })).toHaveAttribute("href", "/quizzes/1");
});
it("does not display an old review after route navigation", async () => {
  let finish;
  api.getQuizReview.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; })).mockResolvedValueOnce({ data: { ...review, title: "Current review" } });
  mountReview();
  fireEvent.click(screen.getByRole("link", { name: "Second review" }));
  await screen.findByRole("heading", { name: "Current review" });
  await act(async () => finish({ data: review }));
  expect(screen.queryByRole("heading", { name: "Ticket quiz" })).not.toBeInTheDocument();
});
it("makes Progress retryable and identifies a partial skill evidence failure", async () => {
  const metric = { completed: 0, total: 1, percent: 0 };
  api.getTrainingProgress.mockRejectedValueOnce(new Error("offline")).mockResolvedValue({ data: { overall_training: metric, videos: metric, quizzes: metric, practice: metric, guided_labs: metric, service_desk: metric } });
  api.getServiceDeskProgressSummary.mockRejectedValue(new Error("offline"));
  render(<MemoryRouter><TrainingProgressPage /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Retry progress" }));
  await screen.findByRole("heading", { name: "Progress", exact: true });
  expect(screen.getByText(/Service Desk skill evidence could not be loaded/)).toBeInTheDocument();
  api.getServiceDeskProgressSummary.mockResolvedValue({ data: { tickets_completed: 1, passed_first_try: 1, needed_revision: 0 } });
  fireEvent.click(screen.getByRole("button", { name: "Retry skill evidence" }));
  await screen.findByRole("heading", { name: "Skill Evidence" });
});
