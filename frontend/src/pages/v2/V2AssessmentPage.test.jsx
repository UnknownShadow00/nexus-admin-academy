import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ getV2Assessment: vi.fn(), submitV2Assessment: vi.fn() }));
vi.mock("../../services/api", () => api);
import V2AssessmentPage from "./V2AssessmentPage";

describe("V2AssessmentPage", () => {
  beforeEach(() => { localStorage.clear(); api.getV2Assessment.mockResolvedValue({ data: { assessment: { key: "qc.dynamic", role: "quick_check", title: "Dynamic Quick Check", pass_percent: 60 }, questions: [{ id: 42, type: "short_answer", question_text: "Which command shows IP settings?", options: [] }], attempts: [] } }); api.submitV2Assessment.mockResolvedValue({ data: { score: 100, total: 1, passed: true, pass_percent: 60, results: [{ question_id: 42, question_text: "Which command shows IP settings?", student_answer: "ipconfig", is_correct: true, correct_answer: null, explanation: "ipconfig displays the settings." }] } }); });
  it("accepts a plain-language short answer and shows deterministic feedback", async () => {
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/assessments/qc.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/assessments/:assessmentKey" element={<V2AssessmentPage />} /></Routes></MemoryRouter>);
    const input = await screen.findByLabelText("Your answer");
    await userEvent.type(input, "ipconfig");
    await userEvent.click(screen.getByRole("button", { name: "Submit answers" }));
    expect(await screen.findByRole("heading", { name: "You passed" })).toBeVisible();
    expect(screen.getByText("ipconfig displays the settings.")).toBeVisible();
    expect(api.submitV2Assessment).toHaveBeenCalledWith("module.dynamic", "qc.dynamic", { 42: "ipconfig" }, { suppressToast: true });
  });
});
