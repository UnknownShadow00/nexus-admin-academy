import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import V2Status, { statusLabel } from "./V2Status";
import { StatusBadge } from "../ui/Badge";
import { getStatusPresentation, mentorFollowUpStatus, practicalDisplayStatus, stageProgressStatus, statusToneClasses } from "../ui/statusFoundation";

afterEach(cleanup);

describe("V2 status presentation", () => {
  it.each([
    ["locked", "Locked"], ["not_started", "Not started"], ["in_progress", "In progress"],
    ["up_next", "Up next"], ["viewed", "Opened"], ["completed", "Done"],
    ["passed", "Passed"], ["approved", "Approved"],
    ["awaiting_mentor_review", "With your mentor"], ["needs_correction", "Changes requested"],
    ["mastered", "Mastered"], ["failed", "Not quite"],
  ])("labels %s as %s", (status, label) => {
    expect(statusLabel(status)).toBe(label);
    render(<V2Status status={status} />);
    expect(screen.getByText(label)).toBeVisible();
  });

  it("keeps mentor follow-up, correction, approval, mastery, and errors semantically distinct", () => {
    expect(getStatusPresentation("awaiting_mentor_review").tone).toBe("mentor");
    expect(getStatusPresentation("needs_correction").tone).toBe("correction");
    expect(getStatusPresentation("approved").tone).toBe("success");
    expect(getStatusPresentation("mastered").tone).toBe("mastered");
    expect(getStatusPresentation("failed").tone).toBe("error");
    expect(getStatusPresentation("not_quite").tone).toBe("correction");
    expect(statusToneClasses.mentor).toContain("status-tone-mentor");
    expect(statusToneClasses.correction).toContain("status-tone-correction");
    expect(statusToneClasses.success).toContain("status-tone-success");
    render(<><V2Status status="awaiting_mentor_review" /><StatusBadge status="needs_correction" /><V2Status status="approved" /><V2Status status="mastered" /></>);
    expect(screen.getByText("With your mentor")).toBeVisible();
    expect(screen.getByText("Changes requested")).toBeVisible();
    expect(screen.getByText("Approved")).toBeVisible();
    expect(screen.getByText("Mastered")).toBeVisible();
  });

  it("maps display status without changing the server's practical or stage values", () => {
    const pending = { status: "awaiting_mentor_review", module_complete: false };
    expect(stageProgressStatus(pending)).toBe("in_progress");
    expect(mentorFollowUpStatus(pending)).toBe("awaiting_mentor_review");
    expect(pending.status).toBe("awaiting_mentor_review");
    expect(stageProgressStatus({ status: "needs_correction", module_complete: false })).toBe("in_progress");
    expect(stageProgressStatus({ status: "mastered", module_complete: true })).toBe("mastered");
    expect(practicalDisplayStatus({ status: "passed" }, true)).toBe("approved");
    expect(practicalDisplayStatus({ status: "passed" }, false)).toBe("passed");
    expect(practicalDisplayStatus({ status: "needs_review" }, true)).toBe("awaiting_mentor_review");
    expect(practicalDisplayStatus({ status: "needs_review" }, false)).toBe("awaiting_mentor_review");
    expect(practicalDisplayStatus({ status: "failed", detail: { review_decision: "reject" } }, false)).toBe("needs_correction");
    expect(practicalDisplayStatus({ status: "in_progress", detail: { review_decision: "reject" } }, false)).toBe("in_progress");
  });
});
