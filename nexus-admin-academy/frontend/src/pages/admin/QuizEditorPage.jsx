import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getQuizQuestions, updateQuestion } from "../../services/api";

export default function QuizEditorPage() {
  const { quizId } = useParams();
  const [quiz, setQuiz] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [saving, setSaving] = useState({});
  const [saved, setSaved] = useState({});

  useEffect(() => {
    const run = async () => {
      const res = await getQuizQuestions(quizId);
      setQuiz({ title: res.data.title });
      setQuestions(res.data.questions || []);
    };
    run();
  }, [quizId]);

  const save = async (question) => {
    setSaving((s) => ({ ...s, [question.id]: true }));
    await updateQuestion(question.id, {
      correct_answer: question.correct_answer,
      explanation: question.explanation,
    });
    setSaving((s) => ({ ...s, [question.id]: false }));
    setSaved((s) => ({ ...s, [question.id]: true }));
    setTimeout(() => setSaved((s) => ({ ...s, [question.id]: false })), 1500);
  };

  const update = (id, field, value) => {
    setQuestions((rows) => rows.map((q) => (q.id === id ? { ...q, [field]: value } : q)));
  };

  if (!quiz) return <main className="p-6">Loading...</main>;

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-6">
      <div>
        <h1 className="text-2xl font-bold dark:text-slate-100">Edit Quiz</h1>
        <p className="text-slate-500">{quiz.title} — {questions.length} questions</p>
      </div>

      {questions.map((q, i) => (
        <div key={q.id} className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
          <p className="font-semibold text-slate-900 dark:text-slate-100">{i + 1}. {q.question_text}</p>

          <div className="grid grid-cols-2 gap-2 text-sm">
            {["a", "b", "c", "d"].map((opt) => (
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
            </select>
            <input className="input-field flex-1" placeholder="Explanation (optional)" value={q.explanation} onChange={(e) => update(q.id, "explanation", e.target.value)} />
            <button className="btn-primary shrink-0" onClick={() => save(q)} disabled={saving[q.id]}>
              {saving[q.id] ? "Saving..." : saved[q.id] ? "✓ Saved" : "Save"}
            </button>
          </div>
        </div>
      ))}
    </main>
  );
}
