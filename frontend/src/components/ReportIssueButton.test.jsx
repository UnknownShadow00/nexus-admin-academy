import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ReportIssueButton from "./ReportIssueButton";

describe("ReportIssueButton", () => {
  it("renders for the student UI and invokes feedback", async () => {
    const onOpen = vi.fn();
    render(<ReportIssueButton onOpen={onOpen} />);
    await userEvent.click(screen.getByRole("button", { name: "Report Issue" }));
    expect(screen.getByText("Report Issue")).toBeVisible();
    expect(onOpen).toHaveBeenCalledOnce();
  });
});
