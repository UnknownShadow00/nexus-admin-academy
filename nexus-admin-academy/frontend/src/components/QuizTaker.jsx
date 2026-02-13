import { useEffect, useState } from "react";
import { getQuiz, submitQuiz } from "../services/api";

export default function QuizTaker({ quizId, studentId }) {
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);

  useEffect(() => {
    getQuiz(quizId).then((res) => setQuiz(res.data));
  }, [quizId]);

  const onSubmit = async () => {
    const payload = { student_id: studentId, answers };
    const res = await submitQuiz(quizId, payload);
    setResult(res.data);
  };

  if (!quiz) return <div className="panel">Loading quiz...</div>;

  return (
    <section className="panel space-y-4">
      <h2 className="text-xl font-semibold">{quiz.title}</h2>
      {quiz.questions.map((q) => (
        <div key={q.id} className="rounded border p-3">
          <p className="font-medium">{q.question_text}</p>
          {["A", "B", "C", "D"].map((opt) => (
            <label key={opt} className="block">
              <input
                type="radio"
                name={`q_${q.id}`}
                className="mr-2"
                onChange={() => setAnswers((prev) => ({ ...prev, [q.id]: opt }))}
              />
              {q[`option_${opt.toLowerCase()}`]}
            </label>
          ))}
        </div>
      ))}
      <button className="rounded bg-sky-600 px-4 py-2 text-white" onClick={onSubmit}>
        Submit Quiz
      </button>
      {result && (
        <div className="rounded border border-green-200 bg-green-50 p-3">
          Score: {result.score}/{result.total} | XP: {result.xp_awarded}
        </div>
      )}
    </section>
  );
}
