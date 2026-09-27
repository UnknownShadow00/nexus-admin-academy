import { StrictMode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import QuizTaker from "./QuizTaker";
import { MemoryRouter } from "react-router-dom";

afterEach(cleanup);
import { getQuiz, submitQuiz } from "../services/api";

vi.mock("../services/api", () => ({ getQuiz: vi.fn(), submitQuiz: vi.fn() }));

const quiz = {
  id: 1,
  title: "Orientation",
  questions: [1, 2, 3, 4].map((id) => ({
    id, question_text: `Support question ${id}`, option_a: "Ask the user", option_b: "Guess",
  })),
};

describe("QuizTaker request lifecycle", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.resetAllMocks();
  });

  it("keeps the learner's question and answer when an older StrictMode request finishes late", async () => {
    let finishOldRequest;
    getQuiz.mockImplementationOnce(() => new Promise((resolve) => { finishOldRequest = resolve; }));
    getQuiz.mockResolvedValueOnce({ data: quiz });
    render(<StrictMode><QuizTaker quizId={1} studentId={7} /></StrictMode>);

    await screen.findByText("Question 1 of 4");
    fireEvent.click(screen.getByRole("radio", { name: /Ask the user/ }));
    fireEvent.click(screen.getByRole("button", { name: "Next", exact: true }));
    expect(screen.getByText("Question 2 of 4")).toBeInTheDocument();
    await act(async () => { finishOldRequest({ data: quiz }); });

    expect(screen.getByText("Question 2 of 4")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Previous", exact: true }));
    expect(screen.getByRole("radio", { name: /Ask the user/ })).toBeChecked();
  });

  it("ignores an old quiz response after navigation to a different quiz", async () => {
    let finishOldRequest;
    getQuiz.mockImplementationOnce(() => new Promise((resolve) => { finishOldRequest = resolve; }));
    getQuiz.mockResolvedValueOnce({ data: { ...quiz, questions: [{ ...quiz.questions[0], question_text: "Current quiz question" }] } });
    const { rerender } = render(<QuizTaker quizId={1} studentId={7} />);
    rerender(<QuizTaker quizId={2} studentId={7} />);
    await screen.findByText("1. Current quiz question");
    await act(async () => { finishOldRequest({ data: quiz }); });
    expect(screen.getByText("1. Current quiz question")).toBeInTheDocument();
    expect(screen.getByText("Question 1 of 1")).toBeInTheDocument();
  });
});

// Product-level regressions exercise shared browsers, recovery, and submission.
describe("QuizTaker learning and recovery", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.resetAllMocks();
    vi.spyOn(Math, "random").mockReturnValue(0.99);
    localStorage.clear();
    getQuiz.mockResolvedValue({ data: quiz });
  });

  const mount = (studentId = 7) => render(<MemoryRouter><QuizTaker quizId={1} studentId={studentId} /></MemoryRouter>);

  it("presents E–H options and submits their exact stable letters", async () => {
    getQuiz.mockResolvedValue({ data: { ...quiz, presentation_hash: "snapshot-1", questions: [{ id: 5, question_text: "Which causes apply?", option_a: "Dust", option_b: "Heat", option_c: "Power", option_d: "Software", option_e: "Memory", option_f: "All of the above", correct_answer: "F" }] } });
    submitQuiz.mockResolvedValue({ data: { score: 1, total: 1, passed: true, results: [{ question_id: 5, question_text: "Which causes apply?", options: { A: "Dust", B: "Heat", C: "Power", D: "Software", E: "Memory", F: "All of the above" }, presented_option_order: ["A", "B", "C", "D", "E", "F"], student_answer: "F", correct_answer: "F", is_correct: true }] } });
    mount();
    await screen.findByText("Question 1 of 1");
    expect(screen.getByRole("radio", { name: /All of the above/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: /All of the above/ }));
    fireEvent.click(screen.getByRole("button", { name: "Submit Quiz" }));
    await screen.findByText("Passed", { exact: true });
    const payload = submitQuiz.mock.calls[0][1];
    expect(payload.answers).toEqual({ 5: "F" });
    expect(payload.presentation_hash).toBe("snapshot-1");
    expect(payload.presented_questions).toEqual([{ id: 5, options: expect.arrayContaining(["A", "B", "C", "D", "E", "F"]) }]);
    expect(screen.getByText("All of the above")).toBeInTheDocument();
  });

  it("restores the same question, option order, and answer after a refresh", async () => {
    const first = mount();
    await screen.findByText("Question 1 of 4");
    fireEvent.click(screen.getByRole("radio", { name: "Ask the user" }));
    fireEvent.click(screen.getByRole("button", { name: "Next", exact: true }));
    fireEvent.click(screen.getByRole("radio", { name: "Guess" }));
    const questionText = screen.getByRole("group").textContent;
    first.unmount();
    // A fresh shuffle would differ; a draft must preserve its original order.
    Math.random.mockReturnValue(0);
    mount();
    await screen.findByText("Question 2 of 4");
    expect(screen.getByRole("group")).toHaveTextContent(questionText);
    expect(screen.getByRole("radio", { name: "Guess" })).toBeChecked();
    expect(screen.getByText("2 answered")).toBeInTheDocument();
  });

  it("keeps learner A's answers out of learner B's quiz", async () => {
    const first = mount(7);
    await screen.findByText("Question 1 of 4");
    fireEvent.click(screen.getByRole("radio", { name: "Ask the user" }));
    first.unmount();
    const second = mount(8);
    await screen.findByText("Question 1 of 4");
    expect(screen.getByRole("radio", { name: "Ask the user" })).not.toBeChecked();
    expect(screen.getByText("0 answered")).toBeInTheDocument();
    second.unmount();
    mount(7);
    await screen.findByText("Question 1 of 4");
    expect(screen.getByRole("radio", { name: "Ask the user" })).toBeChecked();
  });

  it("does not save the prior account's state into a newly selected account", async () => {
    const { rerender } = render(<MemoryRouter><QuizTaker quizId={1} studentId={7} /></MemoryRouter>);
    await screen.findByText("Question 1 of 4");
    fireEvent.click(screen.getByRole("radio", { name: "Guess" }));
    rerender(<MemoryRouter><QuizTaker quizId={1} studentId={8} /></MemoryRouter>);
    await screen.findByText("Question 1 of 4");
    expect(screen.getByText("0 answered")).toBeInTheDocument();
  });

  it("ignores legacy unowned drafts and malformed drafts without blocking the quiz", async () => {
    localStorage.setItem("quiz_progress_1", JSON.stringify({ answers: { 1: "B" } }));
    localStorage.setItem("nexus:quiz-draft:7:1", "invalid json");
    mount();
    await screen.findByText("Question 1 of 4");
    expect(screen.getByText("0 answered")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Guess" })).not.toBeChecked();
  });

  it("does not restore answers after the authored question changes", async () => {
    const first = mount();
    await screen.findByText("Question 1 of 4");
    fireEvent.click(screen.getByRole("radio", { name: "Guess" }));
    first.unmount();
    getQuiz.mockResolvedValue({ data: { ...quiz, questions: quiz.questions.map((question) => ({ ...question, option_b: "Changed option" })) } });
    mount();
    await screen.findByText("Question 1 of 4");
    expect(screen.getByText("0 answered")).toBeInTheDocument();
  });

  it("counts an unchecked multi-select as unanswered and focuses the next question", async () => {
    getQuiz.mockResolvedValue({ data: { ...quiz, questions: quiz.questions.map((question) => ({ ...question, is_multi_select: true })) } });
    mount();
    await screen.findByText("Question 1 of 4");
    fireEvent.click(screen.getByRole("checkbox", { name: "Guess" }));
    expect(screen.getByText("1 answered")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: "Guess" }));
    expect(screen.getByText("0 answered")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next", exact: true }));
    expect(screen.getByRole("heading", { name: "2. Support question 2" })).toHaveFocus();
  });

  it("submits successfully even when browser storage is unavailable", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("Storage unavailable"); });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("Storage unavailable"); });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => { throw new Error("Storage unavailable"); });
    getQuiz.mockResolvedValue({ data: { ...quiz, questions: [quiz.questions[0]] } });
    submitQuiz.mockResolvedValue({ data: { score: 1, total: 1, passed: true, results: [{ question_id: 1, is_correct: true, student_answer: "A", correct_answer: "A", explanation: "Ask before making changes." }] } });
    mount();
    await screen.findByText("Question 1 of 1");
    expect(screen.getByRole("status")).toHaveTextContent("cannot save your quiz draft");
    fireEvent.click(screen.getByRole("radio", { name: "Ask the user" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit Quiz" }));
    expect(await screen.findByText("Passed", { exact: true })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(submitQuiz).toHaveBeenCalledTimes(1);
  });

  it("keeps answers after a failed submission and blocks duplicate pending submits", async () => {
    getQuiz.mockResolvedValue({ data: { ...quiz, questions: [quiz.questions[0]] } });
    let rejectSubmit;
    submitQuiz.mockImplementationOnce(() => new Promise((_, reject) => { rejectSubmit = reject; }));
    mount();
    await screen.findByText("Question 1 of 1");
    fireEvent.click(screen.getByRole("radio", { name: "Guess" }));
    const button = screen.getByRole("button", { name: "Submit Quiz" });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(submitQuiz).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("radio", { name: "Guess" })).toBeDisabled();
    await act(async () => { rejectSubmit(new Error("Offline")); });
    expect(screen.getByRole("alert")).toHaveTextContent("Your answers are still here");
    expect(screen.getByRole("radio", { name: "Guess" })).toBeChecked();
    expect(screen.getByRole("button", { name: "Submit Quiz" })).toBeEnabled();
  });

  it("starts a full deliberate retake and restores that new attempt after refresh", async () => {
    const one = { ...quiz, questions: [quiz.questions[0]], attempts: [] };
    getQuiz.mockResolvedValue({ data: one });
    submitQuiz.mockResolvedValue({ data: { score: 0, total: 1, passed: false, results: [{ question_id: 1, is_correct: false, student_answer: "B", correct_answer: "A" }] } });
    const first = mount();
    await screen.findByText("Question 1 of 1");
    fireEvent.click(screen.getByRole("radio", { name: "Guess" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit Quiz" }));
    await screen.findByText("Not passed", { exact: true });
    fireEvent.click(screen.getByRole("button", { name: "Try Again", exact: true }));
    expect(screen.getByText("0 answered")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "Ask the user" }));
    first.unmount();
    getQuiz.mockResolvedValue({ data: { ...one, attempts: [{ score: 0 }] } });
    mount();
    await screen.findByText("Question 1 of 1");
    expect(screen.getByRole("radio", { name: "Ask the user" })).toBeChecked();
    await waitFor(() => expect(submitQuiz).toHaveBeenCalledTimes(1));
  });
});

it("does not show prior questions when the next quiz route fails to load", async () => {
  vi.resetAllMocks();
  localStorage.clear();
  getQuiz.mockResolvedValueOnce({ data: quiz }).mockRejectedValueOnce({ userMessage: "This quiz is locked" });
  const { rerender } = render(<QuizTaker quizId={1} studentId={7} />);
  await screen.findByText("Question 1 of 4");
  fireEvent.click(screen.getByRole("radio", { name: /Ask the user/ }));
  rerender(<QuizTaker quizId={2} studentId={7} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("This quiz is locked");
  expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Submit Quiz" })).not.toBeInTheDocument();
});
