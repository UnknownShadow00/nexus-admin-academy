import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import QuizTaker from "../components/QuizTaker";
import Banner from "../components/ui/Banner";
import { getCurrentStudent } from "../hooks/useAuth";
import { getQuiz } from "../services/api";

export default function QuizPage() {
  const { quizId } = useParams();
  const location = useLocation();
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
      {bannerError ? <Banner variant="error">{bannerError}</Banner> : null}
      {showRetakeBanner ? <Banner variant="warning">Retakes do not award XP {"\u2014"} only your first attempt counts</Banner> : null}
      <QuizTaker quizId={quizId} studentId={studentId} />
      {location.state?.returnTo ? <Link className="btn-secondary" to={location.state.returnTo}>Return to This Week</Link> : null}
    </main>
  );
}
