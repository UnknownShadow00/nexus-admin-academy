import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import {
  checkPracticeAnswer,
  getQuiz,
  saveQuizAssessment,
  startQuizAssessment,
  submitQuizAssessment,
} from "../services/api";
import QuizTaker, { hasAnswer } from "./QuizTaker";

vi.mock("../services/api", () => ({
  checkPracticeAnswer: vi.fn(),
  getQuiz: vi.fn(),
  saveQuizAssessment: vi.fn(),
  startQuizAssessment: vi.fn(),
  submitQuiz: vi.fn(),
  submitQuizAssessment: vi.fn(),
}));

const assessmentQuiz = {
  id: 7,
  title: "Network assessment",
  is_required: true,
  show_in_weekly_checklist: true,
  questions: [],
};
const assessment = {
  purpose: "assessment",
  quiz: { id: 7, title: "Network assessment", question_count: 1 },
  attempt: { id: 91, status: "in_progress", answers: {}, current_position: 0 },
  questions: [{ id: 44, position: 0, question_text: "What does APIPA suggest?", is_multi_select: true, options: [{ letter: "A", text: "DHCP was not obtained" }, { letter: "B", text: "DNS is proven down" }] }],
};

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  saveQuizAssessment.mockResolvedValue({ data: {} });
});
afterEach(cleanup);

describe("Wave 4 quiz contracts", () => {
  it("treats an empty multi-select array as unanswered", () => {
    expect(hasAnswer([])).toBe(false);
    expect(hasAnswer(["A"])).toBe(true);
  });

  it("labels an assessment and saves a learner+quiz+attempt scoped draft", async () => {
    getQuiz.mockResolvedValue({ data: assessmentQuiz });
    startQuizAssessment.mockResolvedValue({ data: assessment });
    render(<MemoryRouter><QuizTaker quizId={7} studentId={3} /></MemoryRouter>);

    expect(await screen.findByText("Assessment", { exact: true })).toBeInTheDocument();
    expect(screen.getByText(/Counts toward module completion/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("DHCP was not obtained"));

    await waitFor(() => expect(saveQuizAssessment).toHaveBeenCalled());
    expect(localStorage.getItem("nexus:quiz-draft:3:7:91")).toContain("A");
    expect(localStorage.getItem("nexus:quiz-draft:4:7:91")).toBeNull();
  });

  it("restores the exact server attempt and submitted answer after refresh", async () => {
    localStorage.setItem("nexus:quiz-draft:3:7:91", JSON.stringify({ answers: { 44: ["A"] }, current_position: 0 }));
    getQuiz.mockResolvedValue({ data: assessmentQuiz });
    startQuizAssessment.mockResolvedValue({ data: assessment });
    submitQuizAssessment.mockResolvedValue({ data: { attempt_id: 91, score: 1, total: 1, percentage: 100, passed: true, purpose: "assessment", disclosure: "full_review", results: [] } });
    render(<MemoryRouter><QuizTaker quizId={7} studentId={3} /></MemoryRouter>);

    const option = (await screen.findAllByRole("checkbox"))[0];
    expect(option).toBeChecked();
    fireEvent.click(screen.getByRole("button", { name: "Submit assessment" }));
    await waitFor(() => expect(submitQuizAssessment).toHaveBeenCalledWith(7, 91, expect.objectContaining({ answers: { 44: "A" } }), expect.anything()));
    expect(localStorage.getItem("nexus:quiz-draft:3:7:91")).toBeNull();
  });

  it("labels practice as non-credit and teaches immediately", async () => {
    getQuiz.mockResolvedValue({ data: { id: 8, title: "Practice DHCP", is_required: false, show_in_weekly_checklist: false, questions: [{ id: 45, question_text: "What does DHCP supply?", option_a: "IP settings", option_b: "Passwords", is_multi_select: false }] } });
    checkPracticeAnswer.mockResolvedValue({ data: { purpose: "practice", awards_credit: false, is_correct: false, your_answer: "Passwords", correct_answer: "IP settings", key_idea: "DHCP supplies normal IP configuration.", review: { url: "/lessons/2#worked-example", label: "DHCP → Worked example" } } });
    render(<MemoryRouter><QuizTaker quizId={8} studentId={3} /></MemoryRouter>);

    expect(await screen.findByText("Practice Check")).toBeInTheDocument();
    expect(screen.getByText(/does not affect module credit/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Passwords"));
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(await screen.findByText(/DHCP supplies normal IP configuration/)).toBeInTheDocument();
  });
});
