import { beforeEach, expect, it } from "vitest";
import { assessmentDraftKey, readAssessmentDraft, writeAssessmentDraft } from "./assessmentDraft";
const data = { questions: [{ id: 1, type: "short_answer", options: [] }, { id: 2, type: "multi", is_multi_select: true, options: [{ key: "A" }, { key: "B" }] }] };
beforeEach(() => localStorage.clear());
it("isolates students, modules and server attempts without losing the original wording", () => {
  const key = assessmentDraftKey(7, "module.one", "check", 1);
  writeAssessmentDraft(key, data, { 1: "  Own wording\n  ", 2: ["A"] }, 1);
  expect(readAssessmentDraft(key, data)).toMatchObject({ answers: { 1: "  Own wording\n  ", 2: ["A"] }, index: 1 });
  for (const other of [assessmentDraftKey(8, "module.one", "check", 1), assessmentDraftKey(7, "module.two", "check", 1), assessmentDraftKey(7, "module.one", "check", 2)]) expect(readAssessmentDraft(other, data).answers).toEqual({});
});
it("ignores changed questions and corrupt drafts and filters forged options", () => {
  const key = assessmentDraftKey(7, "module.one", "check", 1);
  writeAssessmentDraft(key, data, { 2: ["A", "KEY", "A"] }, 500);
  expect(readAssessmentDraft(key, data)).toMatchObject({ answers: { 2: ["A"] }, index: 0 });
  expect(readAssessmentDraft(key, { questions: [...data.questions, { id: 3 }] }).answers).toEqual({});
  localStorage.setItem(key, "{broken"); expect(readAssessmentDraft(key, data).answers).toEqual({});
});
