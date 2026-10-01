import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";
import V2CorrectionAlerts from "./V2CorrectionAlerts";

it("shows each outstanding practical with mentor feedback and a direct resubmission link", () => {
  render(<MemoryRouter><V2CorrectionAlerts corrections={[{ module_key: "stage4", assessment_key: "practical", stage_title: "Stage 4", practical_title: "Windows observation", feedback: "Show the application view", route: "/learning-v2/modules/stage4/practical/practical" }]} /></MemoryRouter>);
  expect(screen.getByRole("heading", { name: "Needs correction (1)" })).toBeVisible();
  expect(screen.getByText("Mentor feedback: Show the application view")).toBeVisible();
  expect(screen.getByRole("link", { name: /Fix & resubmit/ })).toHaveAttribute("href", "/learning-v2/modules/stage4/practical/practical");
});
