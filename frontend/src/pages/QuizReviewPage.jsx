import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import BackLink from "../components/BackLink";
import QuizReviewScreen from "../components/QuizReviewScreen";
import Spinner from "../components/Spinner";
import { getCurrentStudent } from "../hooks/useAuth";
import { getQuizReview } from "../services/api";

export default function QuizReviewPage() {
  const { quizId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const studentId = getCurrentStudent()?.id;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setData(null);
    setError(null);
    getQuizReview(quizId, studentId, { suppressToast: true })
      .then((response) => { if (!cancelled) setData(response.data); })
      .catch((requestError) => {
        if (cancelled) return;
        const missingAttempt = requestError?.response?.status === 404
          && requestError?.response?.data?.detail === "No attempt found for this quiz";
        setError({
          missingAttempt,
          message: missingAttempt ? "You have not submitted this quiz yet. Take it to see your answers and explanations." : requestError?.userMessage || "Your quiz review could not be loaded. Try again. Your saved attempts have not been changed.",
        });
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [quizId, retryKey, studentId]);

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-4 sm:p-6">
      <BackLink className="btn-secondary" fallbackLabel="Back to Quizzes" fallbackTo="/quizzes" />
      {loading ? <Spinner text="Loading review..." /> : error ? <section className="panel"><h1 className="text-xl font-bold">{error.missingAttempt ? "Take your first attempt" : "Quiz review unavailable"}</h1><p role="alert" className="mt-2 text-slate-700 dark:text-slate-300">{error.message}</p>{error.missingAttempt ? <Link className="btn-primary mt-4" to={`/quizzes/${quizId}`} state={location.state}>Take quiz</Link> : <button type="button" className="btn-primary mt-4" onClick={() => setRetryKey((value) => value + 1)}>Try again</button>}</section> : data ? <QuizReviewScreen quiz={{ title: data.title, questions: data.questions }} result={data} retakeLabel="Retake Quiz" onRetake={() => navigate(`/quizzes/${quizId}`, { state: location.state })} /> : null}
    </main>
  );
}
