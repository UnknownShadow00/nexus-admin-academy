// Account + module + assessment + attempt isolation; stale definitions are ignored.
export function assessmentDraftKey(studentId, moduleKey, assessmentKey, attemptId) {
  return studentId && attemptId ? `nexus:assessment:${studentId}:${moduleKey}:${assessmentKey}:${attemptId}` : null;
}
function signature(data) { return JSON.stringify(data.questions); }
export function readAssessmentDraft(key, data, legacyKey) {
  try {
    const raw = key && localStorage.getItem(key);
    const saved = raw ? JSON.parse(raw) : null;
    const old = !raw && legacyKey ? JSON.parse(localStorage.getItem(legacyKey) || "null") : null;
    const candidate = saved?.signature === signature(data) ? saved.answers : old;
    const answers = {};
    for (const question of data.questions || []) {
      const answer = candidate?.[question.id];
      const keys = question.options?.map(option => option.key) || [];
      if (["short_answer", "free_response"].includes(question.type)) {
        if (typeof answer === "string" && answer.length <= 10000) answers[question.id] = answer;
      } else if (question.is_multi_select) {
        if (Array.isArray(answer)) answers[question.id] = [...new Set(answer.filter(value => keys.includes(value)))];
      } else if (keys.includes(answer)) answers[question.id] = answer;
    }
    const index = Number.isInteger(saved?.index) && saved.index >= 0 && saved.index < data.questions.length ? saved.index : 0;
    return { answers, index, available: Boolean(key) };
  } catch { return { answers: {}, index: 0, available: false }; }
}
export function writeAssessmentDraft(key, data, answers, index) {
  try { if (!key) return false; localStorage.setItem(key, JSON.stringify({ signature: signature(data), answers, index })); return true; }
  catch { return false; }
}
export function clearAssessmentDraft(key, legacyKey) {
  try { if (key) localStorage.removeItem(key); if (legacyKey) localStorage.removeItem(legacyKey); } catch { /* Server submission remains authoritative. */ }
}
