import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ getMentorGrade: vi.fn(), submitMentorGrade: vi.fn() }));
vi.mock("../../services/api", () => api);
import V2MentorGradePage from "./V2MentorGradePage";

const detail = { student_id: 2, status: "needs_review", question_text: "Explain APIPA.", submitted_answer: "It is a fallback address.", rubric_version: "v1", deterministic: { matched_concepts: ["APIPA"], missing_concepts: ["DHCP failure"] }, mentor_overrides: [] };

describe("V2MentorGradePage", () => {
  it("submits an append-only mentor override and renders returned history", async () => {
    const user = userEvent.setup();
    api.getMentorGrade.mockResolvedValue({ data: detail });
    api.submitMentorGrade.mockResolvedValue({ data: { history: { ...detail, status: "graded", mentor_overrides: [{ id: 3, override_passed: true, override_score: 0.8, reason: "Understands the cause.", mentor_label: "mentor" }] } } });
    render(<MemoryRouter initialEntries={["/admin/v2-grading/7"]}><Routes><Route path="/admin/v2-grading/:pendingGradeId" element={<V2MentorGradePage />} /></Routes></MemoryRouter>);
    expect(await screen.findByText("Explain APIPA.")).toBeInTheDocument();
    await user.clear(screen.getByLabelText("Score (0–1)"));
    await user.type(screen.getByLabelText("Score (0–1)"), "0.8");
    await user.type(screen.getByLabelText("Reason / note"), "Understands the cause.");
    await user.click(screen.getByRole("button", { name: "Submit mentor grade" }));
    expect(api.submitMentorGrade).toHaveBeenCalledWith("7", { score: 0.8, passed: true, reason: "Understands the cause.", mentor_label: "mentor" }, { suppressToast: true });
    expect(await screen.findByText("Understands the cause.")).toBeInTheDocument();
  });
});
