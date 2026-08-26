import { describe, expect, it } from "vitest";
import { createSafeRouteContext, mergeSafeLearningContext, mergeSafeRouteContext } from "./context";

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

  it("supports route-only context", () => {
    expect(mergeSafeRouteContext(undefined, { pathname: "/labs" }, { width: 1280, height: 720 })).toEqual({
      tags: { route: "/labs", nexus_area: "lab" },
      context: { route: "/labs", area: "lab", viewport_width: 1280, viewport_height: 720 },
    });
  });

  it("preserves page tags when synchronizing the same route", () => {
    const route = mergeSafeRouteContext(undefined, { pathname: "/labs/endpoint-1" });
    const page = mergeSafeLearningContext(route, {
      module_name: "Endpoint Support",
      activity_type: "structured_lab",
      activity_stable_id: "endpoint-practice-1",
    });

    expect(mergeSafeRouteContext(page, { pathname: "/labs/endpoint-1" }).tags).toEqual(expect.objectContaining({
      route: "/labs/endpoint-1",
      lab_template_id: "endpoint-1",
      module_name: "Endpoint Support",
      activity_type: "structured_lab",
      activity_stable_id: "endpoint-practice-1",
    }));
  });

  it("replaces stale activity context when the route selects a different activity", () => {
    const route = mergeSafeRouteContext(undefined, { pathname: "/training/week/4", search: "?activity=activity-old" });
    const oldActivity = mergeSafeLearningContext(route, {
      module_name: "Networking",
      activity_type: "service_desk_scenario",
      service_desk_scenario_id: "scenario-old",
    });
    const nextActivity = mergeSafeRouteContext(oldActivity, {
      pathname: "/training/week/4",
      search: "?activity=activity-new",
    });

    expect(nextActivity.tags).toEqual(expect.objectContaining({
      route: "/training/week/4",
      module_name: "Networking",
      activity_stable_id: "activity-new",
    }));
    expect(nextActivity.tags).not.toHaveProperty("activity_type");
    expect(nextActivity.tags).not.toHaveProperty("service_desk_scenario_id");
    expect(JSON.stringify(nextActivity)).not.toContain("scenario-old");
  });

  it("clears activity context when navigating to a generic page", () => {
    const lab = mergeSafeLearningContext(
      mergeSafeRouteContext(undefined, { pathname: "/labs/endpoint-1" }),
      { module_name: "Endpoint Support", activity_type: "structured_lab", activity_stable_id: "practice-1" },
    );

    expect(mergeSafeRouteContext(lab, { pathname: "/dashboard" })).toEqual({
      tags: { route: "/dashboard", nexus_area: "student_app" },
      context: { route: "/dashboard", area: "student_app", viewport_width: undefined, viewport_height: undefined, release: undefined },
    });
  });

  it("does not wipe valid page context for query-string-only changes", () => {
    const page = mergeSafeLearningContext(
      mergeSafeRouteContext(undefined, { pathname: "/training/week/7", search: "?activity=valid-activity" }),
      { module_name: "Identity Support", activity_type: "video" },
    );
    const result = mergeSafeRouteContext(page, {
      pathname: "/training/week/7",
      search: "?panel=overview&token=never-capture",
    });

    expect(result.tags).toEqual(expect.objectContaining({
      route: "/training/week/7",
      activity_stable_id: "valid-activity",
      module_name: "Identity Support",
      activity_type: "video",
    }));
    expect(JSON.stringify(result)).not.toMatch(/panel|token|never-capture|overview/);
  });
});
