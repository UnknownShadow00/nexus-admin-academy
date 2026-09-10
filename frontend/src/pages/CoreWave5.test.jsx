import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import ReviewEvidence from "../components/ReviewEvidence";
import TodayReviewCard from "../components/TodayReviewCard";
import { getDueFlashcards, getServiceDeskProgressSummary, getTrainingProgress } from "../services/api";
import TrainingProgressPage from "./TrainingProgressPage";

vi.mock("../services/api", () => ({
  getDueFlashcards: vi.fn(),
  getServiceDeskProgressSummary: vi.fn(),
  getTrainingProgress: vi.fn(),
  rateFlashcard: vi.fn(),
}));

const evidence = {
  started: false,
  course_required_activities: { completed: 0, total: 11 },
  current_module: {
    required: { completed: 0, total: 3 },
    lessons: { completed: 0, total: 1 },
    assessments: { passed: 0, total: 1 },
    practical: { completed: 0, total: 1 },
    optional_practice: { completed: 0, total: 2 },
  },
  learning: { lessons_completed: 0, lessons_required: 4 },
  assessments: { required_assessments_passed: 0, required_assessments_total: 3 },
  practice: { completed: 0 },
  practical: {
    guided_completed: 0,
    guided_total: 1,
    independent_completed: 0,
    independent_total: 1,
    historical_unclassified_completed: 0,
    historical_unclassified_total: 0,
    tickets_passed: 0,
  },
};

function progressData(overrides = {}) {
  return {
    current_module: { title: "Support Workflow Essentials", route: "/training/module/support" },
    evidence: { ...evidence, ...overrides },
    assessments: [],
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  getServiceDeskProgressSummary.mockResolvedValue({ data: { tickets_completed: 0 } });
  getDueFlashcards.mockResolvedValue({ review_state: "fresh", due_count: 0, priorities: [], data: [] });
});
afterEach(cleanup);

describe("Core Wave 5 progress", () => {
  it("gives a fresh learner a useful start without mastery or readiness claims", async () => {
    getTrainingProgress.mockResolvedValue({ data: progressData() });
    render(<MemoryRouter><TrainingProgressPage /></MemoryRouter>);

    expect(await screen.findByText("You’re just getting started")).toBeInTheDocument();
    expect(screen.getByText("0 of 3", { exact: false })).toBeInTheDocument();
    expect(screen.getByText(/Review will appear after/)).toBeInTheDocument();
    expect(screen.queryByText(/readiness:/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/mastered/i)).not.toBeInTheDocument();
  });

  it("separates lesson, assessment, guided, and independent evidence", async () => {
    getTrainingProgress.mockResolvedValue({ data: progressData({
      started: true,
      current_module: { ...evidence.current_module, required: { completed: 2, total: 3 }, lessons: { completed: 1, total: 1 }, assessments: { passed: 1, total: 1 } },
      learning: { lessons_completed: 1, lessons_required: 4 },
      assessments: { required_assessments_passed: 1, required_assessments_total: 3 },
      practical: { ...evidence.practical, guided_completed: 1 },
    }) });
    render(<MemoryRouter><TrainingProgressPage /></MemoryRouter>);

    expect(await screen.findByText("Learning")).toBeInTheDocument();
    expect(screen.getByText("Required assessments passed")).toBeInTheDocument();
    expect(screen.getByText("Guided practice")).toBeInTheDocument();
    expect(screen.getByText("Independent demonstrations")).toBeInTheDocument();
    expect(screen.getByText(/Optional practice: 0 completed.*does not change required progress/)).toBeInTheDocument();
  });
});

it("shows actionable priorities and a distinct review error", () => {
  const retry = vi.fn();
  const { rerender } = render(<MemoryRouter><ReviewEvidence summary={{ review_state: "due", due_count: 4, priorities: [{ question_id: 1, concept_name: "DHCP and APIPA", reason: "You missed a question about DHCP and APIPA.", review_url: "/lessons/2#worked-example", practice_url: "/quizzes/9" }] }} onRetry={retry} /></MemoryRouter>);
  expect(screen.getByText("DHCP and APIPA")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Review worked example" })).toHaveAttribute("href", "/lessons/2#worked-example");
  expect(screen.getByText(/Showing the most useful priorities first/)).toBeInTheDocument();

  rerender(<MemoryRouter><ReviewEvidence error onRetry={retry} /></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(retry).toHaveBeenCalled();
  expect(screen.getByText("We couldn’t load your review items.")).toBeInTheDocument();
});

it("keeps Today review compact and hides it when nothing is due", async () => {
  const { rerender } = render(<TodayReviewCard summary={{ review_state: "clear", due_count: 0 }} />);
  expect(screen.queryByText(/Start review/)).not.toBeInTheDocument();
  rerender(<TodayReviewCard summary={{ review_state: "due", due_count: 2 }} />);
  expect(screen.getByText("Review 2 concepts")).toBeInTheDocument();
  expect(screen.getByText(/About 4 minutes/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Start review" })).toBeInTheDocument();
  await waitFor(() => expect(screen.queryByText(/All caught up/)).not.toBeInTheDocument());
});
