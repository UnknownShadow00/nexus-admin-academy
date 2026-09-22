const VERSION = 1;
export const OPTION_LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H"];

export function quizDraftKey(studentId, quizId) {
  if (!/^[1-9]\d*$/.test(String(studentId)) || !/^[1-9]\d*$/.test(String(quizId))) return null;
  return `nexus:quiz-draft:${studentId}:${quizId}`;
}

export function hasAnswer(answer) {
  return Array.isArray(answer) ? answer.length > 0 : Boolean(answer);
}

function signature(quiz) {
  // Include content and attempt count so changed questions or a submission in
  // another tab cannot silently reuse a draft from the old attempt.
  return JSON.stringify([
    quiz.attempts?.length || 0,
    [...(quiz.questions || [])].sort((a, b) => a.id - b.id).map((question) => [
      question.id, question.question_text, Boolean(question.is_multi_select),
      ...OPTION_LETTERS.map((letter) => question[`option_${letter.toLowerCase()}`] || ""),
    ]),
  ]);
}

function sameMembers(actual, expected) {
  return Array.isArray(actual) && actual.length === expected.length
    && new Set(actual).size === expected.length
    && actual.every((value) => expected.includes(value));
}

export function readQuizDraft(studentId, quizId, quiz) {
  const key = quizDraftKey(studentId, quizId);
  if (!key) return { draft: null, available: false };
  let raw;
  try { raw = localStorage.getItem(key); }
  catch { return { draft: null, available: false }; }
  if (!raw) return { draft: null, available: true };
  try {
    const saved = JSON.parse(raw);
    const questions = quiz.questions || [];
    if (saved?.version !== VERSION || saved.signature !== signature(quiz)
      || !sameMembers(saved.order, questions.map((question) => question.id))) {
      return { draft: null, available: true };
    }
    const answers = {};
    const timings = {};
    for (const question of questions) {
      const letters = OPTION_LETTERS.filter((letter) => question[`option_${letter.toLowerCase()}`]);
      if (!sameMembers(saved.options?.[question.id], letters)) return { draft: null, available: true };
      const answer = saved.answers?.[question.id];
      if (question.is_multi_select && Array.isArray(answer)) {
        const valid = [...new Set(answer.filter((letter) => letters.includes(letter)))];
        if (valid.length) answers[question.id] = valid;
      } else if (!question.is_multi_select && letters.includes(answer)) {
        answers[question.id] = answer;
      }
      const elapsed = saved.timings?.[question.id];
      if (Number.isFinite(elapsed) && elapsed >= 0) timings[question.id] = elapsed;
    }
    const currentIndex = Number.isInteger(saved.currentIndex)
      && saved.currentIndex >= 0 && saved.currentIndex < questions.length ? saved.currentIndex : 0;
    return { draft: { ...saved, answers, timings, currentIndex }, available: true };
  } catch { return { draft: null, available: true }; }
}

export function writeQuizDraft(studentId, quizId, quiz, questions, answers, currentIndex, timings) {
  const key = quizDraftKey(studentId, quizId);
  if (!key) return false;
  try {
    localStorage.setItem(key, JSON.stringify({
      version: VERSION,
      signature: signature(quiz),
      order: questions.map((question) => question.id),
      options: Object.fromEntries(questions.map((question) => [
        question.id, question.shuffledOptions.map((option) => option.realLetter),
      ])),
      answers, currentIndex, timings,
    }));
    return true;
  } catch { return false; }
}

export function clearQuizDraft(studentId, quizId) {
  const key = quizDraftKey(studentId, quizId);
  if (!key) return;
  try { localStorage.removeItem(key); }
  catch { /* An acknowledged server submission remains successful without storage. */ }
}
