import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ActivityAccessError from "../components/ActivityAccessError";
import BackLink from "../components/BackLink";
import LessonPage from "./LessonPage";
import { buildContinueTarget } from "./StudentHome";
import { getLesson } from "../services/api";
vi.mock("../services/api", async (original) => ({
  ...(await original()),
  getLesson: vi.fn(),
}));
afterEach(cleanup);
it("preserves explicit named module origin after reopening a URL", () => {
  render(
    <MemoryRouter
      initialEntries={[
        "/quizzes/42?returnTo=%2Ftraining%2Fmodule%2Fmodule.orientation.nexus&returnToLabel=Nexus%20Orientation",
      ]}
    >
      <BackLink fallbackTo="/quizzes" fallbackLabel="Back to Quizzes" />
    </MemoryRouter>,
  );
  expect(
    screen.getByRole("link", { name: "Back to Nexus Orientation" }),
  ).toHaveAttribute("href", "/training/module/module.orientation.nexus");
});
it("Today names the activity, purpose, time and following step", () => {
  const result = buildContinueTarget(null, {
    current_module: {
      title: "Nexus Orientation",
      route: "/training/module/module.orientation.nexus",
      purpose: "Understand tickets",
    },
    next_activity: {
      id: 1,
      title: "Welcome to Nexus",
      activity_type: "lesson",
      description: "Learn ticket fields",
      estimated_minutes: 8,
      destination_route: "/lessons/1",
    },
    current_module_activities: [
      { id: 1, is_required: true },
      { id: 2, is_required: true, title: "Ticketing Systems Quiz" },
    ],
  });
  expect(result).toMatchObject({
    title: "Welcome to Nexus",
    estimatedMinutes: 8,
    why: "Understand tickets",
    after: "Ticketing Systems Quiz",
  });
});
it("a lesson network failure is not a prerequisite lock", async () => {
  getLesson.mockRejectedValue(new Error("offline"));
  render(
    <MemoryRouter>
      <LessonPage />
    </MemoryRouter>,
  );
  expect(
    await screen.findByRole("heading", { name: "Unable to load lesson" }),
  ).toBeVisible();
  expect(screen.queryByText("Lesson locked")).not.toBeInTheDocument();
});

it("a missing activity is unavailable, not a prerequisite lock", () => {
  render(
    <MemoryRouter>
      <ActivityAccessError
        kind="Lesson"
        error={{ response: { status: 404 } }}
      />
    </MemoryRouter>,
  );
  expect(
    screen.getByRole("heading", { name: "Lesson unavailable" }),
  ).toBeVisible();
});
it("a prerequisite response shows its exact recovery action", () => {
  render(
    <MemoryRouter>
      <ActivityAccessError
        kind="Quiz"
        error={{
          response: {
            status: 403,
            data: {
              code: "PREREQUISITE_NOT_MET",
              error: "Complete IP basics first.",
              data: {
                missing_prerequisite: "IP basics",
                next_action_route: "/lessons/7",
              },
            },
          },
        }}
      />
    </MemoryRouter>,
  );
  expect(screen.getByRole("heading", { name: "Quiz locked" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Go to IP basics" })).toHaveAttribute(
    "href",
    "/lessons/7",
  );
});
it("rejects a malicious return destination", () => {
  render(
    <MemoryRouter
      initialEntries={[
        "/quizzes/42?returnTo=https://example.invalid&returnToLabel=Injected",
      ]}
    >
      <BackLink fallbackTo="/quizzes" fallbackLabel="Back to Quizzes" />
    </MemoryRouter>,
  );
  expect(screen.getByRole("link")).toHaveAttribute("href", "/quizzes");
});

it("constrains the learner-facing return label", () => {
  render(
    <MemoryRouter
      initialEntries={[
        `/quizzes/42?returnTo=%2Ftraining%2Fmodule%2Fmodule.orientation.nexus&returnToLabel=${encodeURIComponent(`Back to Nexus\nOrientation${"x".repeat(200)}`)}`,
      ]}
    >
      <BackLink fallbackTo="/quizzes" fallbackLabel="Back to Quizzes" />
    </MemoryRouter>,
  );
  const link = screen.getByRole("link");
  expect(link).toHaveTextContent(/^Back to Nexus Orientationx+$/);
  expect(link.textContent.length).toBeLessThanOrEqual(168);
});
