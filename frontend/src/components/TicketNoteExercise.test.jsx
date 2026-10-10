import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import TicketNoteExercise from "./TicketNoteExercise";
afterEach(cleanup);
it("treats natural notes and formerly flagged words as advisory study work", () => {
  render(<TicketNoteExercise />);
  for (const label of ["Issue summary", "Troubleshooting performed", "Resolution", "User confirmation / verification"]) fireEvent.change(screen.getByLabelText(label), { target: { value: "The broken cable was replaced; Dana can now sign in." } });
  fireEvent.click(screen.getByRole("button", { name: "Check my note" }));
  expect(screen.getByText(/All fields are filled/)).toHaveTextContent("not a grade");
  expect(screen.queryByText(/Too vague|Fix the flagged|objectively/)).not.toBeInTheDocument();
  expect(screen.getByLabelText("Resolution")).toHaveValue("The broken cable was replaced; Dana can now sign in.");
});
it("keeps genuine empty-response guidance", () => {
  render(<TicketNoteExercise />);
  fireEvent.click(screen.getByRole("button", { name: "Check my note" }));
  expect(screen.getAllByText(/Not filled in yet/)).toHaveLength(4);
  expect(screen.getByText(/Fill in the empty fields/)).toBeInTheDocument();
});
