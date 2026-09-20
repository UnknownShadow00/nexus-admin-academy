import { describe, expect, it } from "vitest";
import { isV2CurriculumEnabled } from "./features";

describe("V2 curriculum feature flag", () => {
  it("is off when missing and only enables explicitly", () => {
    expect(isV2CurriculumEnabled({})).toBe(false);
    expect(isV2CurriculumEnabled({ VITE_V2_CURRICULUM_ENABLED: "false" })).toBe(false);
    expect(isV2CurriculumEnabled({ VITE_V2_CURRICULUM_ENABLED: "true" })).toBe(true);
  });
});
