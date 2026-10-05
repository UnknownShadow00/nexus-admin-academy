import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ getV2Assessment: vi.fn(), getV2Module: vi.fn(), startV2AssessmentAttempt: vi.fn(), submitV2Assessment: vi.fn() }));
vi.mock("../../services/api", () => api);
vi.mock("../../hooks/useAuth", () => ({ getCurrentStudent: () => ({ id: 7 }) }));
import V2AssessmentPage from "./V2AssessmentPage";

function mountAssessment() {
  render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/assessments/qc.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/assessments/:assessmentKey" element={<V2AssessmentPage />} /></Routes></MemoryRouter>);
}

describe("V2AssessmentPage", () => {
  beforeEach(() => { cleanup(); localStorage.clear(); const payload = { assessment: { key: "qc.dynamic", role: "quick_check", title: "Dynamic Quick Check", pass_percent: 60 }, attempt: { id: 99, attempt_number: 1, status: "in_progress" }, questions: [{ id: 42, type: "short_answer", question_text: "Which command shows IP settings?", options: [] }], attempts: [] }; api.getV2Assessment.mockResolvedValue({ data: payload }); api.getV2Module.mockResolvedValue({ data: { continue: { route: "/learning-v2/modules/module.dynamic/lessons/next", label: "Continue learning" } } }); api.startV2AssessmentAttempt.mockResolvedValue({ data: { ...payload, attempt: { ...payload.attempt, id: 100, attempt_number: 2 } } }); api.submitV2Assessment.mockResolvedValue({ data: { attempt_id: 99, score: 100, total: 1, passed: true, grading_state: "graded", pass_percent: 60, results: [{ question_id: 42, question_text: "Which command shows IP settings?", student_answer: "ipconfig", is_correct: true, correct_answer: null, explanation: "ipconfig displays the settings." }] } }); });
  it("accepts a plain-language short answer and shows deterministic feedback", async () => {
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/assessments/qc.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/assessments/:assessmentKey" element={<V2AssessmentPage />} /></Routes></MemoryRouter>);
    const input = await screen.findByLabelText("Your answer");
    await userEvent.type(input, "ipconfig");
    await userEvent.click(screen.getByRole("button", { name: "Submit answers" }));
    expect(await screen.findByRole("heading", { name: "Passed" })).toBeVisible();
    expect(screen.getByText("ipconfig displays the settings.")).toBeVisible();
    expect(api.submitV2Assessment).toHaveBeenCalledWith("module.dynamic", "qc.dynamic", 99, { 42: "ipconfig" }, { suppressToast: true });
  });

  it("calls an incorrect graded answer Not quite rather than Needs review", async () => {
    api.submitV2Assessment.mockResolvedValueOnce({ data: { attempt_id: 99, score: 0, total: 1, passed: false, grading_state: "graded", pass_percent: 60, results: [{ question_id: 42, question_text: "Which command shows IP settings?", student_answer: "ping", is_correct: false, correct_answer: null, explanation: "Review the IP settings command." }] } });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/assessments/qc.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/assessments/:assessmentKey" element={<V2AssessmentPage />} /></Routes></MemoryRouter>);
    await userEvent.type(await screen.findByLabelText("Your answer"), "ping");
    await userEvent.click(screen.getByRole("button", { name: "Submit answers" }));
    expect(await screen.findByRole("heading", { name: "Not quite" })).toBeVisible();
    expect(screen.getAllByText("Not quite")).toHaveLength(2);
    expect(screen.queryByText("Needs review")).not.toBeInTheDocument();
    expect(screen.getByText(/Score: 0% · Pass mark: 60%/)).toBeVisible();
  });

  it("renders free-response assessment questions as writable text", async () => {
    const base = (await api.getV2Assessment()).data;
    api.getV2Assessment.mockResolvedValue({ data: {
      ...base,
      questions: [{ id: 44, type: "free_response", question_text: "Explain the DHCP failure.", options: [] }],
    } });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/assessments/qc.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/assessments/:assessmentKey" element={<V2AssessmentPage />} /></Routes></MemoryRouter>);

    const answer = await screen.findByLabelText("Your answer");
    expect(answer.tagName).toBe("TEXTAREA");
    await userEvent.type(answer, "APIPA indicates that DHCP did not answer; renew and verify the lease.");
    expect(answer).toHaveValue("APIPA indicates that DHCP did not answer; renew and verify the lease.");
  });

  it("scopes drafts by authenticated student, assessment, and server attempt", async () => {
    localStorage.setItem("v2_assessment_7_qc.dynamic_98", JSON.stringify({ 42: "stale" }));
    localStorage.setItem("v2_assessment_8_qc.dynamic_99", JSON.stringify({ 42: "other student" }));
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/assessments/qc.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/assessments/:assessmentKey" element={<V2AssessmentPage />} /></Routes></MemoryRouter>);
    expect(await screen.findByLabelText("Your answer")).toHaveValue("");
    await userEvent.type(screen.getByLabelText("Your answer"), "mine");
    expect(localStorage.getItem("v2_assessment_7_qc.dynamic_99")).toContain("mine");
  });

  it("warns before submitting unanswered questions and can review them", async () => {
    const base = (await api.getV2Assessment()).data;
    api.getV2Assessment.mockResolvedValue({ data: { ...base, questions: [...base.questions, { id: 43, type: "short_answer", question_text: "How do you verify it?", options: [] }] } });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/assessments/qc.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/assessments/:assessmentKey" element={<V2AssessmentPage />} /></Routes></MemoryRouter>);
    await userEvent.click(await screen.findByRole("button", { name: "Next question" }));
    await userEvent.click(screen.getByRole("button", { name: "Submit answers" }));
    expect(screen.getByRole("alert")).toHaveTextContent("2 unanswered questions");
    await userEvent.click(screen.getByRole("button", { name: "Review unanswered" }));
    expect(screen.getByText("Question 1 of 2")).toBeVisible();
  });

  it("restores a saved server result after reload", async () => {
    const base = (await api.getV2Assessment()).data;
    api.getV2Assessment.mockResolvedValue({ data: { ...base, result: { attempt_id: 99, score: 80, passed: true, grading_state: "graded", pass_percent: 60, results: [] } } });
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/assessments/qc.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/assessments/:assessmentKey" element={<V2AssessmentPage />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Passed" })).toBeVisible();
    expect(screen.getByText(/Score: 80%/)).toBeVisible();
  });

  it("uses labeled radio and checkbox rows across real choice question types", async () => {
    const base = (await api.getV2Assessment()).data;
    api.getV2Assessment.mockResolvedValue({ data: { ...base, questions: [
      { id: 51, type: "multiple_choice", question_text: "What should you do first?", is_multi_select: false, options: [{ key: "A", text: "Ask the user" }, { key: "B", text: "Restart now" }] },
      { id: 52, type: "multiple_choice", question_text: "Which checks are safe?", is_multi_select: true, options: [{ key: "A", text: "Read the error" }, { key: "B", text: "Confirm account" }] },
    ] } });
    mountAssessment();
    expect(await screen.findByRole("heading", { name: "What should you do first?" })).toBeVisible();
    expect(screen.getByRole("radio", { name: "A. Ask the user" })).toBeVisible();
    await userEvent.click(screen.getByRole("radio", { name: "A. Ask the user" }));
    await userEvent.click(screen.getByRole("button", { name: "Next question" }));
    expect(screen.getByText("Question 2 of 2")).toBeVisible();
    await userEvent.click(screen.getByRole("checkbox", { name: "A. Read the error" }));
    await userEvent.click(screen.getByRole("checkbox", { name: "B. Confirm account" }));
    await userEvent.click(screen.getByRole("button", { name: "Submit answers" }));
    expect(api.submitV2Assessment).toHaveBeenCalledWith("module.dynamic", "qc.dynamic", 99, { 51: "A", 52: ["A", "B"] }, { suppressToast: true });
  });

  it("keeps failure separate from mastery and starts a new server attempt for retry", async () => {
    api.submitV2Assessment.mockResolvedValueOnce({ data: { attempt_id: 99, score: 0, passed: false, grading_state: "graded", pass_percent: 60, results: [{ question_id: 42, question_text: "Which command shows IP settings?", is_correct: false, correct_answer: null, explanation: "Review the command in the lesson." }] } });
    mountAssessment();
    await userEvent.type(await screen.findByLabelText("Your answer"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Submit answers" }));
    expect(await screen.findByRole("heading", { name: "Not quite" })).toBeVisible();
    expect(screen.getByText("Review the command in the lesson.")).toBeVisible();
    expect(screen.queryByText("Mastered")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(api.startV2AssessmentAttempt).toHaveBeenCalledWith("module.dynamic", "qc.dynamic", { suppressToast: true });
    expect(await screen.findByLabelText("Your answer")).toHaveValue("");
    expect(screen.queryByRole("heading", { name: "Not quite" })).not.toBeInTheDocument();
  });

  it("shows pending grading without pass or retry and uses a real stage route", async () => {
    api.submitV2Assessment.mockResolvedValueOnce({ data: { attempt_id: 99, score: null, passed: false, grading_state: "pending", pass_percent: 60, results: [{ question_id: 42, question_text: "Which command shows IP settings?", grading_status: "needs_review", is_correct: false, explanation: "" }] } });
    mountAssessment();
    await userEvent.type(await screen.findByLabelText("Your answer"), "ipconfig");
    await userEvent.click(screen.getByRole("button", { name: "Submit answers" }));
    expect(await screen.findByRole("heading", { name: "Grading pending" })).toBeVisible();
    expect(screen.getByText("Waiting for grading")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to Stage" })).toHaveAttribute("href", "/learning-v2/modules/module.dynamic");
    expect(screen.queryByText("Mastered")).not.toBeInTheDocument();
  });

  it("returns a terminal passed learner to My Course from server continuation", async () => {
    const base = (await api.getV2Assessment()).data;
    api.getV2Assessment.mockResolvedValue({ data: { ...base, result: { attempt_id: 99, score: 100, passed: true, grading_state: "graded", pass_percent: 60, results: [] } } });
    api.getV2Module.mockResolvedValue({ data: { continue: null } });
    mountAssessment();
    expect(await screen.findByRole("heading", { name: "Passed" })).toBeVisible();
    expect(await screen.findByRole("link", { name: /Back to My Course/ })).toHaveAttribute("href", "/learning-v2");
    expect(screen.queryByText("Mastered")).not.toBeInTheDocument();
  });
});
