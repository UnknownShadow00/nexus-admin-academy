import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getCurrentStudent } from "../hooks/useAuth";
import QuizTaker from "../components/QuizTaker";
import { getQuiz } from "../services/api";

export default function QuizPage() {
  const { quizId } = useParams();
  const studentId = getCurrentStudent()?.id;
  const [showRetakeBanner, setShowRetakeBanner] = useState(false);
  const [bannerError, setBannerError] = useState("");

  useEffect(() => {
    getQuiz(quizId, studentId, { suppressToast: true })
      .then((res) => {
        setShowRetakeBanner((res.data?.attempts?.length || 0) > 0);
      })
      .catch((err) => {
        setBannerError(err?.userMessage || "The backend is still waking up.");
      });
  }, [quizId, studentId]);

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-6">
      {bannerError ? (
        <div className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
          {bannerError}
        </div>
      ) : null}
      {showRetakeBanner ? (
        <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
          Retakes don't award XP - only your first attempt counts
        </div>
      ) : null}
      <QuizTaker quizId={quizId} studentId={studentId} />
    </main>
  );
}
