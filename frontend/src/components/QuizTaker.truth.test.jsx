import { cleanup, render, screen, act } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { StrictMode } from "react";
import { MemoryRouter } from "react-router-dom";
import QuizTaker from "./QuizTaker";
import { getQuiz } from "../services/api";
vi.mock("../services/api", () => ({
  checkPracticeAnswer: vi.fn(),
  getQuiz: vi.fn(),
  saveQuizAssessment: vi.fn(),
  startQuizAssessment: vi.fn(),
  submitQuiz: vi.fn(),
  submitQuizAssessment: vi.fn(),
}));
afterEach(cleanup);
it("ignores a stale load that would reshuffle an active quiz", async () => {
  const pending = [];
  getQuiz.mockImplementation(
    () => new Promise((resolve) => pending.push(resolve)),
  );
  render(
    <StrictMode>
      <MemoryRouter>
        <QuizTaker quizId={1} studentId={1} />
      </MemoryRouter>
    </StrictMode>,
  );
  const response = (text) => ({
    data: {
      id: 1,
      is_required: false,
      show_in_weekly_checklist: false,
      questions: [
        { id: 1, question_text: text, option_a: "Correct", option_b: "Wrong" },
      ],
    },
  });
  await act(async () => pending[1](response("Current quiz")));
  expect(screen.getByText(/Current quiz/)).toBeInTheDocument();
  await act(async () => pending[0](response("Stale quiz")));
  expect(screen.queryByText(/Stale quiz/)).not.toBeInTheDocument();
  expect(screen.getByText(/Current quiz/)).toBeInTheDocument();
});
