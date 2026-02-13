import { BookOpen } from "./icons";
import { Link } from "react-router-dom";

export default function QuizList({ quizzes }) {
  return (
    <section className="panel">
      <h2 className="mb-3 flex items-center gap-2 text-xl font-bold text-gray-900">
        <BookOpen className="h-5 w-5 text-blue-600" /> Quizzes
      </h2>
      <div className="space-y-2">
        {quizzes?.map((quiz) => (
          <Link
            key={quiz.id}
            to={`/quizzes/${quiz.id}`}
            className="block rounded-lg border border-slate-200 bg-white p-3 shadow-sm transition-all duration-200 hover:bg-blue-50 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <p className="font-semibold text-gray-900">{quiz.title}</p>
            <p className="text-xs text-slate-600">Week {quiz.week_number} · {quiz.question_count} questions</p>
          </Link>
        ))}
        {!quizzes?.length && <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-500">No quizzes published yet.</p>}
      </div>
    </section>
  );
}
