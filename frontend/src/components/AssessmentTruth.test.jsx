import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AttemptResult } from "./AssessmentEvidence";
import StudentTrainingDetail from "./StudentTrainingDetail";
import QuizReviewScreen from "./QuizReviewScreen";
afterEach(cleanup);
describe("Assessment evidence", () => {
  it("does not present the legacy mastery number as competency", () => {
    render(
      <StudentTrainingDetail
        studentId={1}
        cachedProgress={{
          weekly_roadmap: [],
          skills: [
            {
              domain_id: "1.0",
              domain_name: "Hardware",
              mastery_percent: 13.3,
            },
          ],
          required_quizzes: { completed: 2, total: 2 },
          assessments: [],
        }}
      />,
    );
    expect(screen.queryByText("Skills Mastery")).not.toBeInTheDocument();
    expect(screen.queryByText("13.3%")).not.toBeInTheDocument();
    expect(screen.getByText(/Required quizzes passed/)).toBeInTheDocument();
  });
  it.each([
    [4, 4, 100],
    [3, 4, 75],
    [0, 4, 0],
    [3, 6, 50],
  ])("identifies an immediate %i/%i attempt", (score, total, percentage) => {
    render(
      <MemoryRouter>
        <QuizReviewScreen
          quiz={{ id: 1, title: "Quiz", questions: [] }}
          result={{
            score,
            total,
            correct_count: score,
            question_count: total,
            percentage,
            passed: percentage >= 70,
            attempt_id: 7,
            submitted_at: "2026-09-08T12:00:00Z",
          }}
        />
      </MemoryRouter>,
    );
    expect(screen.getAllByText(`${percentage}%`).length).toBeGreaterThan(0);
    expect(screen.getByText(/Attempt #7/)).toBeInTheDocument();
  });
});

it("does not label unrecoverable historical performance as a failure", () => {
  render(
    <AttemptResult
      attempt={{
        correct_count: 8,
        question_count: 4,
        percentage: null,
        passed: null,
        attempt_id: 1,
        score_basis: "current_bank_legacy_estimate",
      }}
    />,
  );
  expect(screen.getByText(/Pass state unavailable/)).toBeInTheDocument();
  expect(screen.queryByText(/Not passed/)).not.toBeInTheDocument();
});
it("discloses retained legacy credit without inventing a passing attempt", () => {
  render(
    <StudentTrainingDetail
      studentId={1}
      cachedProgress={{
        weekly_roadmap: [],
        required_quizzes: { completed: 1, total: 1 },
        assessments: [
          {
            quiz_id: 1,
            title: "Legacy quiz",
            earned_pass: true,
            legacy_passing_credit: true,
            latest_attempt: null,
            best_attempt: null,
          },
        ],
      }}
    />,
  );
  expect(screen.getAllByText(/Prior passing credit retained/)).toHaveLength(1);
});
