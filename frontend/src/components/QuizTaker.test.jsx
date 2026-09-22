import { StrictMode } from "react";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import QuizTaker from "./QuizTaker";
import { getQuiz } from "../services/api";

vi.mock("../services/api", () => ({ getQuiz: vi.fn(), submitQuiz: vi.fn() }));

afterEach(cleanup);

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


it("does not show prior questions when the next quiz route fails to load", async () => {
  getQuiz.mockResolvedValueOnce({ data: quiz }).mockRejectedValueOnce({ userMessage: "This quiz is locked" });
  const { rerender } = render(<QuizTaker quizId={1} studentId={7} />);
  await screen.findByText("Question 1 of 4");
  fireEvent.click(screen.getByRole("radio", { name: /Ask the user/ }));
  rerender(<QuizTaker quizId={2} studentId={7} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("This quiz is locked");
  expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Submit Quiz" })).not.toBeInTheDocument();
});
