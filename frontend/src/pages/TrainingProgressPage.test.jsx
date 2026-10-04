import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ getTrainingProgress: vi.fn(), getServiceDeskProgressSummary: vi.fn() }));
const access = vi.hoisted(() => ({ studentEnabled: true }));
vi.mock("../services/api", () => api);
vi.mock("../hooks/useAuth", () => ({ getCurrentStudent: () => ({ id: 7 }) }));
vi.mock("../hooks/useV2Access", () => ({ useV2Access: () => access }));
import TrainingProgressPage from "./TrainingProgressPage";

const emptyMetric = { completed: 0, total: 0, percent: 0 };
const progress = {
  overall_training: { completed: 0, total: 150, percent: 0 },
  videos: emptyMetric, quizzes: emptyMetric, practice: emptyMetric,
  guided_labs: emptyMetric, service_desk: emptyMetric,
  modules_completed: 0, total_modules: 0,
  current_module: { title: "Nexus Orientation" },
  current_activity: null, rank_progress: {}, capstone_readiness: {},
};

beforeEach(() => {
  access.studentEnabled = true;
  api.getTrainingProgress.mockResolvedValue({ data: progress });
  api.getServiceDeskProgressSummary.mockResolvedValue({ data: null });
});
afterEach(cleanup);

it("labels older training counts separately for a current course learner", async () => {
  render(<MemoryRouter><TrainingProgressPage /></MemoryRouter>);
  expect(await screen.findByText("Earlier training progress")).toBeVisible();
  expect(screen.getByText("Earlier training module: Nexus Orientation")).toBeVisible();
  expect(screen.getByRole("link", { name: "My Course" })).toHaveAttribute("href", "/learning-v2");
  expect(screen.getByText("0 of 150 required activities complete")).toBeVisible();
});

it("keeps the existing progress wording for learners outside the current course pilot", async () => {
  access.studentEnabled = false;
  render(<MemoryRouter><TrainingProgressPage /></MemoryRouter>);
  expect(await screen.findByText("Training Progress")).toBeVisible();
  expect(screen.getByText("Current module: Nexus Orientation")).toBeVisible();
  expect(screen.queryByText("Earlier training progress")).not.toBeInTheDocument();
});
