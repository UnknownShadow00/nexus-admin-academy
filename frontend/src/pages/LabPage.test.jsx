import { describe, expect, it } from "vitest";

import { isVmProvisioningStatus, normalizeLabTask } from "./LabPage";


describe("Hybrid lab presentation", () => {
  it("keeps polling while the worker configures the guest VM", () => {
    expect(isVmProvisioningStatus("configuring_vm")).toBe(true);
    expect(isVmProvisioningStatus("running")).toBe(false);
  });

  it("normalizes structured curriculum tasks into renderable text", () => {
    expect(normalizeLabTask({
      part: "A",
      title: "Deployment check",
      steps: ["Choose a supported driver.", "Verify the workflow."],
      evidence: "Deployment checklist.",
    }, 0)).toEqual({
      key: "task-0-Part A — Deployment check",
      title: "Part A — Deployment check",
      steps: ["Choose a supported driver.", "Verify the workflow."],
      evidence: "Deployment checklist.",
    });
  });
});
