import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import QuizReviewScreen from "./QuizReviewScreen";

it("shows retry-safe concept remediation without inventing a correct answer", () => {
  render(
    <MemoryRouter>
      <QuizReviewScreen
        quiz={{ id: 7, title: "Network assessment", questions: [{ id: 44, question_text: "What does APIPA suggest?", option_a: "DHCP issue", option_b: "DNS proven down" }] }}
        result={{ attempt_id: 91, purpose: "assessment", disclosure: "concepts_only", passed: false, score: 0, total: 1, percentage: 0, passing_percentage: 70, message: "Assessment not passed yet. No module credit earned.", review: { url: "/lessons/2#worked-example", title: "DHCP and APIPA" }, results: [{ question_id: 44, question_text: "What does APIPA suggest?", student_answer: "B", student_answer_text: "DNS proven down", is_correct: false, key_idea: "Review the underlying concept before another graded attempt.", options: { A: "DHCP issue", B: "DNS proven down" }, review: { url: "/lessons/2#worked-example", label: "DHCP and APIPA → Worked example" } }] }}
        onRetake={vi.fn()}
      />
    </MemoryRouter>,
  );
  expect(screen.getByText("Not passed")).toBeInTheDocument();
  expect(screen.getByText(/Exact answers stay hidden/)).toBeInTheDocument();
  expect(screen.getAllByText("DNS proven down").length).toBeGreaterThan(0);
  expect(screen.queryByText("Correct answer")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Review DHCP and APIPA/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry assessment" })).toBeInTheDocument();
});
