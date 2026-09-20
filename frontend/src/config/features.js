export function isV2CurriculumEnabled(env = import.meta.env) {
  return String(env?.VITE_V2_CURRICULUM_ENABLED || "false").toLowerCase() === "true";
}

export const V2_CURRICULUM_ENABLED = isV2CurriculumEnabled();
