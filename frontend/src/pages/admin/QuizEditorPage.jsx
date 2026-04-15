import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getQuizQuestions, updateQuestion, updateQuiz } from "../../services/api";

export default function QuizEditorPage() {
  const { quizId } = useParams();
  const [quiz, setQuiz] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [edits, setEdits] = useState({});
  const [saving, setSaving] = useState({});
  const [saved, setSaved] = useState({});
  const [publishSaving, setPublishSaving] = useState(false);

  const [titleEdit, setTitleEdit] = useState("");
  const [titleSaving, setTitleSaving] = useState(false);
  const [titleSaved, setTitleSaved] = useState(false);
  const [titleError, setTitleError] = useState("");

  useEffect(() => {
    const run = async () => {
      const res = await getQuizQuestions(quizId);
      const nextTitle = res.data?.title || "";
      setQuiz({ title: nextTitle, status: res.data?.status || "draft" });
      setTitleEdit(nextTitle);
      setQuestions(res.data?.questions || []);
    };
    run();
  }, [quizId]);

  const publishQuiz = async () => {
    setPublishSaving(true);
    try {
      await updateQuiz(quizId, { status: "published" });
      setQuiz((prev) => ({ ...(prev || {}), status: "published" }));
    } finally {
      setPublishSaving(false);
    }
  };

  const saveTitle = async () => {
    const trimmed = titleEdit.trim();
    if (!trimmed || !quiz) return;

    setTitleSaving(true);
    setTitleSaved(false);
    setTitleError("");
    try {
      const res = await updateQuiz(quizId, { title: trimmed });
      const updatedTitle = res.data?.title || trimmed;
      setQuiz((prev) => ({ ...(prev || {}), title: updatedTitle }));
      setTitleEdit(updatedTitle);
      setTitleSaved(true);
      setTimeout(() => setTitleSaved(false), 1500);
    } catch (error) {
      setTitleError(error?.response?.data?.detail || "Failed to save title");
    } finally {
      setTitleSaving(false);
    }
  };

  const save = async (question) => {
    setSaving((s) => ({ ...s, [question.id]: true }));
    const patch = edits[question.id] || {};
    await updateQuestion(question.id, {
      correct_answer: patch.correct_answer ?? question.correct_answer,
      correct_answers: patch.correct_answers ?? question.correct_answers ?? "",
      explanation: patch.explanation ?? question.explanation,
    });
    setSaving((s) => ({ ...s, [question.id]: false }));
    setSaved((s) => ({ ...s, [question.id]: true }));
    setTimeout(() => setSaved((s) => ({ ...s, [question.id]: false })), 1500);
    setEdits((prev) => ({ ...prev, [question.id]: {} }));
  };

  const update = (id, field, value) => {
    setQuestions((rows) => rows.map((q) => (q.id === id ? { ...q, [field]: value } : q)));
    setEdits((prev) => ({ ...prev, [id]: { ...(prev[id] || {}), [field]: value } }));
  };

  if (!quiz) return <main className="p-6">Loading...</main>;

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-6">
      <div className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
        <h1 className="text-2xl font-bold dark:text-slate-100">Edit Quiz</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">{questions.length} questions</p>

        <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200">
          Quiz Title
          <span className="ml-2 text-xs font-normal text-slate-500 dark:text-slate-400">
            (must match quiz_title in curriculum for video linking)
          </span>
        </label>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <input
            className="input-field flex-1"
            value={titleEdit}
            onChange={(e) => setTitleEdit(e.target.value)}
            placeholder="Enter quiz title"
          />
          <button
            className="btn-primary shrink-0"
            onClick={saveTitle}
            disabled={titleSaving || !titleEdit.trim() || titleEdit.trim() === (quiz.title || "").trim()}
          >
            {titleSaving ? "Saving..." : titleSaved ? "Saved" : "Save Title"}
          </button>
        </div>

        {titleError ? <p className="text-sm text-red-600 dark:text-red-400">{titleError}</p> : null}

        <p className="text-xs text-slate-500 dark:text-slate-400">
          To link this quiz to a video, the title must exactly match the video's quiz_title in the Curriculum editor.
        </p>

        <div className="flex items-center gap-3 pt-2">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
              quiz.status === "published"
                ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
                : "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300"
            }`}
          >
            {quiz.status === "published" ? "Published" : "Draft"}
          </span>
          {quiz.status !== "published" ? (
            <button className="btn-primary" onClick={publishQuiz} disabled={publishSaving}>
              {publishSaving ? "Publishing..." : "Publish Quiz"}
            </button>
          ) : null}
        </div>
      </div>

      {questions.map((q, i) => (
        <div key={q.id} className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
          <p className="font-semibold text-slate-900 dark:text-slate-100">{i + 1}. {q.question_text}</p>

          <div className="grid grid-cols-2 gap-2 text-sm">
            {["a", "b", "c", "d", "e"].filter((opt) => (q[`option_${opt}`] || "").trim()).map((opt) => (
              <div
                key={opt}
                className={`rounded border p-2 dark:border-slate-700 ${
                  q.correct_answer === opt.toUpperCase() ? "border-green-400 bg-green-50 dark:bg-green-950/20" : ""
                }`}
              >
                <span className="font-bold uppercase text-slate-500">{opt}.</span>{" "}
                <span className="text-slate-700 dark:text-slate-300">{q[`option_${opt}`]}</span>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Correct:</label>
            <select className="input-field max-w-24" value={q.correct_answer} onChange={(e) => update(q.id, "correct_answer", e.target.value)}>
              <option value="A">A</option>
              <option value="B">B</option>
              <option value="C">C</option>
              <option value="D">D</option>
              <option value="E">E</option>
            </select>
            <input className="input-field flex-1" placeholder="Explanation (optional)" value={q.explanation} onChange={(e) => update(q.id, "explanation", e.target.value)} />
            <button className="btn-primary shrink-0" onClick={() => save(q)} disabled={saving[q.id]}>
              {saving[q.id] ? "Saving..." : saved[q.id] ? "Saved" : "Save"}
            </button>
          </div>

          <div className="mt-2">
            <label className="mb-1 block text-xs text-slate-500 dark:text-slate-400">
              All correct answers for multi-select (comma-separated e.g. "A,C,D" - leave blank for single answer)
            </label>
            <input
              className="input-field w-full text-sm"
              value={edits[q.id]?.correct_answers ?? q.correct_answers ?? ""}
              placeholder="e.g. A,C,D"
              onChange={(e) =>
                setEdits((prev) => ({
                  ...prev,
                  [q.id]: { ...prev[q.id], correct_answers: e.target.value.toUpperCase().replace(/[^A-E,]/g, "") },
                }))
              }
            />
          </div>
        </div>
      ))}
    </main>
  );
}
