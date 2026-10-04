import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import V2Status, { statusLabel } from "./V2Status";
import { StatusBadge } from "../ui/Badge";

afterEach(cleanup);

describe("V2 status presentation", () => {
  it.each([
    ["locked", "Locked"], ["not_started", "Not started"], ["in_progress", "In progress"],
    ["viewed", "Viewed / Opened"], ["passed", "Passed"],
    ["awaiting_mentor_review", "Awaiting mentor review"], ["needs_correction", "Needs correction"],
    ["mastered", "Mastered"], ["failed", "Needs another try"],
  ])("labels %s as %s", (status, label) => {
    expect(statusLabel(status)).toBe(label);
    render(<V2Status status={status} />);
    expect(screen.getByText(label)).toBeVisible();
  });

  it("keeps pending review, correction, failure, and mastery distinct across badge components", () => {
    const { container } = render(<><V2Status status="awaiting_mentor_review" /><V2Status status="mastered" /><StatusBadge status="needs_correction" /><StatusBadge status="failed" /></>);
    const pills = Array.from(container.querySelectorAll("span.inline-flex"));
    expect(pills.map((pill) => pill.textContent)).toEqual([
      "Awaiting mentor review", "Mastered", "Needs correction", "Needs another try",
    ]);
    expect(pills[0].className).toContain("amber");
    expect(pills[1].className).toContain("green");
    expect(pills[2].className).toContain("rose");
    expect(pills[3].className).toContain("red");
  });
});
