import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import BackLink from "../components/BackLink";
import QuizTaker from "../components/QuizTaker";
import Banner from "../components/ui/Banner";
import { getCurrentStudent } from "../hooks/useAuth";
import { getQuiz } from "../services/api";

export default function QuizPage() {
  const { quizId } = useParams();
  const studentId = getCurrentStudent()?.id;
  const [showRetakeBanner, setShowRetakeBanner] = useState(false);

  useEffect(() => {
    getQuiz(quizId, studentId, { suppressToast: true })
      .then((res) => {
        setShowRetakeBanner((res.data?.attempts?.length || 0) > 0);
      })
      .catch(() => {
        setShowRetakeBanner(false);
      });
  }, [quizId, studentId]);

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-6">
      <BackLink className="btn-secondary" fallbackLabel="Back to Quizzes" fallbackTo="/quizzes" />
      {showRetakeBanner ? <Banner variant="warning">Retakes do not award XP {"\u2014"} only your first attempt counts</Banner> : null}
      <QuizTaker quizId={quizId} studentId={studentId} />
    </main>
  );
}
