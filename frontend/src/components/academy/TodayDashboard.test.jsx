import { describe, expect, it } from "vitest";
import { todayActivities, todayProgress } from "./TodayDashboard";

describe("Today evidence mapping", () => {
  it("keeps lesson groups, lesson completion, check passes and practical approval distinct", () => {
    const current = { certification: { version: { key: "nexus_beginner_aplus_v1" } }, progress: {
      groups: { completed: 1, total: 3 }, lessons: { completed: 0, total: 3 },
      quick_checks: { completed: 1, total: 2 }, module_quiz: { activity: { passed: false } },
      service_desk: { activity: { passed: true } }, practical: { activity: { status: "needs_review" } },
      module_complete: false,
    } };
    expect(todayProgress(current)).toEqual({ percent: 33, label: "Lesson groups", rows: [
      { label: "Lessons", value: "0/3", color: "blue" }, { label: "Quick Checks", value: "1/2", color: "purple" },
      { label: "Checkpoint", value: "Not passed", color: "purple" }, { label: "Practiced", value: "Passed", color: "cyan" },
      { label: "Practical", value: "With mentor", color: "mute" },
    ] });
    expect(current.progress.module_complete).toBe(false);
  });

  it("does not turn a mentor rejection into an approved practical", () => {
    const current = { certification: { version: { key: "nexus_beginner_aplus_v1" } }, progress: { practical: { activity: { status: "in_progress", detail: { review_decision: "reject" } } } } };
    expect(todayProgress(current).rows).toContainEqual({ label: "Practical", value: "Changes requested", color: "mute" });
    expect(todayProgress(current).percent).toBeNull();
  });

  it("hides incomplete optional count metadata instead of inventing completion", () => {
    expect(todayProgress({ progress: { lessons: { total: 3 }, quick_checks: { total: 2 } } }).rows).toEqual([]);
    expect(todayProgress(null, { current_module: { required_total: 4 } }).rows).toEqual([]);
  });

  it("uses actual legacy required completion without mixing in V2", () => {
    expect(todayProgress(null, { current_module: { completion_percent: 50, required_complete: 2, required_total: 4 } }))
      .toEqual({ percent: 50, label: "Required work", rows: [{ label: "Required", value: "2/4", color: "blue" }] });
    expect(todayProgress(null, null)).toEqual({ percent: null, label: "Required work", rows: [] });
  });

  it("keeps server availability and learner-specific destinations in course cards", () => {
    const detail = { module: { key: "module.test" }, certification: { version: { key: "nexus_beginner_aplus_v1" } }, lessons: [{ key: "lesson.test", title: "Protect the work", group_status: "completed", resources: [], quick_check: { key: "check.test", title: "Check understanding", available: false, progress: { status: "not_started" } } }], assessments: [{ key: "practical.test", role: "practical", title: "Record observations", available: true, progress: { status: "needs_review" } }], interactions: [] };
    const activities = todayActivities(detail, null);
    expect(activities).toContainEqual(expect.objectContaining({ route: "/learning-v2/modules/module.test/lessons/lesson.test", complete: true }));
    expect(activities).toContainEqual(expect.objectContaining({ route: "/learning-v2/modules/module.test/assessments/check.test", available: false }));
    expect(activities).toContainEqual(expect.objectContaining({ route: "/learning-v2/modules/module.test/practical/practical.test", available: true, status: "awaiting_mentor_review", complete: false }));
  });

  it("excludes broken and prerequisite-locked legacy activities from available work", () => {
    const rows = todayActivities(null, { current_module_activities: [
      { stable_id: "broken", title: "Old reference", destination_route: "/lessons/1", broken_reference: true },
      { stable_id: "locked", title: "Locked", destination_route: null, status: "locked" },
      { stable_id: "desk", title: "Available ticket", destination_route: "/service-desk/task/2", activity_type: "service_desk_scenario" },
    ] });
    expect(rows.filter(item => item.available).map(item => item.route)).toEqual(["/service-desk/task/2"]);
    expect(rows[2].activity.activity_type).toBe("service_desk_scenario");
  });
});
