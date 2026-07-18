import { CheckCircle2, XCircle } from "lucide-react";
import { Link } from "react-router-dom";

const ALL_OPTS = ["A", "B", "C", "D", "E", "F", "G", "H"];

function OptionRow({ letter, text, correctAnswers, studentAnswer }) {
  const studentAnswers = Array.isArray(studentAnswer) ? studentAnswer : studentAnswer ? [studentAnswer] : [];
  const isCorrect = correctAnswers.includes(letter);
  const isStudentPick = studentAnswers.includes(letter);
  const isWrong = isStudentPick && !isCorrect;
  let cls = "flex items-center gap-3 rounded-lg border px-3 py-2.5 text-sm transition-all ";
  if (isCorrect) cls += "border-green-400 bg-green-100 text-green-900 font-semibold dark:border-green-700 dark:bg-green-900/30 dark:text-green-200";
  else if (isWrong) cls += "border-red-400 bg-red-100 text-red-900 dark:border-red-700 dark:bg-red-900/30 dark:text-red-200";
  else cls += "border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400";

  return <div className={cls}><span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold ${isCorrect ? "border-green-600 bg-green-600 text-white dark:bg-green-500" : isWrong ? "border-red-500 bg-red-500 text-white" : "border-slate-300 text-slate-400 dark:border-slate-600"}`}>{letter}</span><span className="flex-1">{text}</span>{isCorrect && isStudentPick && <span className="ml-auto text-xs font-bold text-green-700 dark:text-green-400">Correct</span>}{isCorrect && !isStudentPick && <span className="ml-auto text-xs font-bold text-green-600 dark:text-green-400">Correct answer</span>}{isWrong && <span className="ml-auto text-xs font-bold text-red-600 dark:text-red-400">Your answer</span>}</div>;
}

export default function QuizReviewScreen({ quiz, result, onRetake }) {
  const byId = {};
  (result.results || []).forEach((r) => {
    byId[r.question_id] = r;
  });

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-blue-600 p-8 text-center text-white shadow-lg"><h2 className="mb-2 text-lg font-semibold text-blue-200">{quiz.title}</h2><p className="text-7xl font-bold">{result.score}<span className="text-4xl text-blue-300">/{result.total}</span></p><p className="mt-2 text-2xl font-semibold">{Math.round((result.score / result.total) * 100)}%</p>{result.xp_awarded > 0 && <p className="mt-2 text-blue-100">+{result.xp_awarded} XP earned!</p>}</div>
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-center dark:border-slate-700 dark:bg-slate-900"><p className="text-2xl font-bold text-green-600">{result.score}</p><p className="text-xs text-slate-500">Correct</p></div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-center dark:border-slate-700 dark:bg-slate-900"><p className="text-2xl font-bold text-red-500">{result.total - result.score}</p><p className="text-xs text-slate-500">Wrong</p></div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-center dark:border-slate-700 dark:bg-slate-900"><p className="text-2xl font-bold text-blue-600">{Math.round((result.score / result.total) * 100)}%</p><p className="text-xs text-slate-500">Score</p></div>
      </div>
      <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Answer Review</h3>
      {(quiz.questions || []).map((question, index) => {
        const review = byId[question.id];
        const studentAnswer = review?.student_answer;
        const correctAnswers = review?.correct_answers || [review?.correct_answer || question.correct_answer];
        const isCorrect = review?.is_correct;
        const options = review?.options || {
          A: question.option_a,
          B: question.option_b,
          C: question.option_c,
          D: question.option_d,
          E: question.option_e || "",
          F: question.option_f || "",
          G: question.option_g || "",
          H: question.option_h || "",
        };
        const studentAnswerArr = studentAnswer ? String(studentAnswer).split(",").map((s) => s.trim()) : [];

        return (
          <div key={question.id} className={`rounded-xl border p-4 ${isCorrect ? "border-green-200 dark:border-green-900" : "border-red-200 dark:border-red-900"}`}>
            <div className="mb-3 flex items-start justify-between gap-2"><p className="font-semibold text-slate-900 dark:text-slate-100">Q{index + 1}. {question.question_text}</p><span className="shrink-0">{isCorrect ? <CheckCircle2 size={18} className="text-green-500" /> : <XCircle size={18} className="text-red-500" />}</span></div>
            <div className="space-y-1.5">{ALL_OPTS.map((opt) => { const text = options[opt]; if (!text) return null; return <OptionRow key={opt} letter={opt} text={text} correctAnswers={correctAnswers} studentAnswer={studentAnswerArr} />; })}</div>
            {review?.explanation ? <p className="mt-2 rounded bg-slate-50 p-2 text-sm italic text-slate-600 dark:bg-slate-800 dark:text-slate-300">{review.explanation}</p> : null}
          </div>
        );
      })}
      <div className="flex gap-3">
        <button className="btn-secondary flex-1" onClick={onRetake}>Retake Quiz</button>
        <Link to="/quizzes" className="btn-primary flex-1 text-center">Back to Quizzes</Link>
      </div>
    </div>
  );
}
