import { describe, expect, it } from "vitest";
import { createSafeRouteContext, mergeSafeLearningContext } from "./context";

describe("safe monitoring context", () => {
  it("creates route and activity context without retaining arbitrary query data", () => {
    const result = createSafeRouteContext(
      { pathname: "/training/week/4", search: "?activity=week-4-lab-1&token=top-secret&notes=private" },
      { width: 1440, height: 900 },
      "abc123",
    );
    expect(result.tags).toEqual({
      route: "/training/week/4",
      nexus_area: "learning_path",
      training_week: "4",
      activity_stable_id: "week-4-lab-1",
      release_sha: "abc123",
    });
    expect(JSON.stringify(result)).not.toMatch(/top-secret|private|token|notes/);
  });

  it("accepts only allow-listed learning fields and rejects unsafe text", () => {
    const result = mergeSafeLearningContext({ tags: {}, context: {} }, {
      module_id: 42,
      module_name: "Endpoint Support",
      activity_type: "lab",
      password: "never-send-this",
      module_notes: "student documentation",
      activity_stable_id: "bad value with spaces",
    });
    expect(result.tags).toEqual({ module_id: "42", module_name: "Endpoint Support", activity_type: "lab" });
    expect(JSON.stringify(result)).not.toMatch(/never-send-this|student documentation|password|module_notes/);
  });
});
