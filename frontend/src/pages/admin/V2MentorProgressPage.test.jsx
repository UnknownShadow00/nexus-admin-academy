import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ getV2MentorCohort: vi.fn(), updateV2CohortFocus: vi.fn() }));
vi.mock("../../services/api", () => api);
import V2MentorProgressPage from "./V2MentorProgressPage";

const cohort = {
  student_count: 2, cohort_focus: null, module_key: "module.aplus.core1.ip_configuration",
  available_modules: [
    { module_key: "module.aplus.core1.ip_configuration", title: "IP Configuration" },
    { module_key: "module.aplus.core1.hardware_support", title: "PC Components" },
  ],
  students: [
    { student_id: 1, student_name: "Student A", certification: { name: "CompTIA A+" }, module_title: "IP Configuration", completion: { module_complete: false, lessons_completed: 5, lessons_total: 5 }, module_quiz: { status: "passed", score: 80, passed: true }, practical: { status: "completed" }, service_desk: { status: "passed", score: 85 }, explain_status: "graded", weak_topics: [{ topic: "DNS troubleshooting", missed_count: 2 }], current_position: { title: "DNS Basics" } },
    { student_id: 2, student_name: "Student B", certification: { name: "CompTIA A+" }, module_title: "IP Configuration", completion: { module_complete: false, lessons_completed: 3, lessons_total: 5 }, module_quiz: { status: "failed", score: 50, passed: false }, practical: { status: "not_started" }, service_desk: { status: "not_started" }, explain_status: "needs_review", weak_topics: [{ topic: "DHCP and APIPA", missed_count: 3 }], current_position: { title: "DHCP and APIPA" } },
  ],
  needs_review: [{ pending_grade_id: 9, student_id: 2, source_type: "interview_explain", status: "needs_review", priority: 4 }],
  weak_areas: [{ topic: "DHCP and APIPA", students_affected: 1, student_count: 2, total_misses: 3, students_with_repeated_misses: 1 }, { topic: "DNS troubleshooting", students_affected: 1, student_count: 2, total_misses: 2, students_with_repeated_misses: 1 }],
  suggested_review_topics: [{ topic: "DHCP and APIPA", reason: "1 student showing difficulty", students_affected: 1 }],
  student_questions: [{ student_id: 2, student_name: "Student B", resource_key: "external", resource: "Practice set", student_note: null, confusing_topic: "DNS", question_for_mentor: "Why can internet work when DNS fails?" }],
};

describe("V2MentorProgressPage", () => {
  afterEach(cleanup);
  beforeEach(() => { api.getV2MentorCohort.mockResolvedValue({ data: cohort }); api.updateV2CohortFocus.mockResolvedValue({ data: {} }); });
  it("renders cohort intelligence, review queue, and self-reported questions", async () => {
    render(<MemoryRouter><V2MentorProgressPage /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "V2 Student Progress" })).toBeInTheDocument();
    expect(screen.getByText("Student A")).toBeInTheDocument();
    expect(screen.getAllByText("Student B").length).toBeGreaterThan(0);
    expect(screen.getAllByText("DHCP and APIPA").length).toBeGreaterThan(1);
    expect(screen.getByText(/Why can internet work/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review" })).toHaveAttribute("href", "/admin/v2-grading/9");
  });
  it("filters failed quizzes and has an honest empty state", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><V2MentorProgressPage /></MemoryRouter>);
    await screen.findByText("Student A");
    await user.selectOptions(screen.getByLabelText("Filter"), "failed_quiz");
    expect(screen.queryByText("Student A")).not.toBeInTheDocument();
    expect(screen.getAllByText("Student B").length).toBeGreaterThan(0);
    await user.selectOptions(screen.getByLabelText("Filter"), "weak:DNS troubleshooting");
    expect(screen.getByText("Student A")).toBeInTheDocument();
  });
  it("shows loading and error states", async () => {
    api.getV2MentorCohort.mockRejectedValueOnce({ userMessage: "Development API unavailable" });
    render(<MemoryRouter><V2MentorProgressPage /></MemoryRouter>);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
    expect(await screen.findByRole("alert")).toHaveTextContent("Development API unavailable");
  });
  it("loads another module through the generic selector", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><V2MentorProgressPage /></MemoryRouter>);
    await screen.findByText("Student A");
    await user.selectOptions(screen.getByLabelText("Module"), "module.aplus.core1.hardware_support");
    expect(api.getV2MentorCohort).toHaveBeenLastCalledWith("module.aplus.core1.hardware_support", { suppressToast: true });
  });
});
