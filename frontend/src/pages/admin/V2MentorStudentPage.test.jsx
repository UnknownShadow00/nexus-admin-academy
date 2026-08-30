import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ getV2MentorStudent: vi.fn() }));
vi.mock("../../services/api", () => api);
import V2MentorStudentPage from "./V2MentorStudentPage";

describe("V2MentorStudentPage", () => {
  it("renders detailed misses, Explain state, engine links, and external practice", async () => {
    api.getV2MentorStudent.mockResolvedValue({ data: {
      student_name: "Student B", certification: { name: "CompTIA A+", version: "220-1201" }, module_title: "IP Configuration", current_position: { title: "Module Quiz" }, completion: { lessons_completed: 5, lessons_total: 5, required_resources_completed: 1, required_resources_total: 1, module_complete: false }, module_quiz: { score: 50, status: "failed" }, required_resources: [{ resource_key: "required", resource: "DHCP lesson", lesson: "DHCP and APIPA", completed: true }], quick_checks: [{ assessment_key: "qc", title: "DNS Quick Check", status: "failed", score: 50 }], weak_objectives: [{ objective_code: "5.7", objective_text: "Troubleshoot wired/wireless connectivity", missed_count: 2 }], missed_questions: [{ question_id: 2, question_text: "What does APIPA indicate?", student_answer: "DNS failure", correct_answer: ["B — DHCP did not respond"], explanation: "APIPA is a DHCP fallback.", objective_code: "5.7", objective_text: "Troubleshoot wired/wireless connectivity", topic: "DHCP and APIPA", times_missed: 2 }], explain_responses: [{ pending_grade_id: 8, submission_ref: "x", prompt: "Explain APIPA.", submitted_answer: "It is fallback.", status: "needs_review", expected_concepts: ["APIPA", { concept: "DHCP failure", aliases: ["DHCP unavailable"] }], rubric_version: "v1", deterministic: { status: "needs_review" }, confidence: null, resolved: { grade_source: null, score: null }, mentor_overrides: [] }], practical: { status: "completed", score: 90, review_url: "/admin/labs" }, service_desk: { status: "failed", score: 55, review_url: "/admin/service-desk-review", breakdown: [{ key: "verification", label: "Verification", met: false }] }, external_practice: [{ resource_key: "ext", resource: "External quiz", completed: true, reported_score: 60, student_note: "Need help", confusing_topic: "DNS", question_for_mentor: "Why?" }],
    } });
    render(<MemoryRouter initialEntries={["/admin/v2-progress/students/2"]}><Routes><Route path="/admin/v2-progress/students/:studentId" element={<V2MentorStudentPage />} /></Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Student B" })).toBeInTheDocument();
    expect(screen.getByText("What does APIPA indicate?")).toBeInTheDocument();
    expect(screen.getByText(/Missed 2 times/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Grade response" })).toHaveAttribute("href", "/admin/v2-grading/8");
    expect(screen.getByText(/APIPA, DHCP failure/)).toBeInTheDocument();
    expect(screen.getByText(/Reported score: 60/)).toBeInTheDocument();
    expect(screen.getByText(/Verification:/)).toHaveTextContent("Needs work");
  });
});
