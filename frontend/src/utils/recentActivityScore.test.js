import { describe, expect, it } from "vitest";
import { recentActivityScore } from "./recentActivityScore";

describe("recent activity scores", () => {
  it.each([
    [17, 19, 89],
    [7, 8, 88],
    [4, 4, 100],
    [0, 8, 0],
  ])("shows %i of %i as %i percent", (score, score_total, percent) => {
    expect(recentActivityScore({ type: "quiz", score, score_total })).toEqual({
      percent,
      label: `Score ${score} / ${score_total} · ${percent}%`,
    });
  });

  it("does not invent a denominator for unknown or old attempts", () => {
    expect(recentActivityScore({ type: "quiz", score: null })).toBeNull();
    expect(recentActivityScore({ type: "quiz", score: 7 })).toBeNull();
    expect(recentActivityScore({ type: "quiz", score: 7, score_percent: 88 })).toEqual({ percent: 88, label: "Score 88%" });
  });

  it("keeps ticket scores on their existing 100-point scale", () => {
    expect(recentActivityScore({ type: "service_desk", score: 100 })).toEqual({ percent: 100, label: "Score 100%" });
  });
});
