import { useParams } from "react-router-dom";
import BackLink from "../components/BackLink";
import QuizTaker from "../components/QuizTaker";
import { getCurrentStudent } from "../hooks/useAuth";

export default function QuizPage() {
  const { quizId } = useParams();
  const studentId = getCurrentStudent()?.id;
  return (
    <main className="mx-auto max-w-4xl space-y-4 p-4 sm:p-6">
      <BackLink className="btn-secondary" fallbackLabel="Back to Quizzes" fallbackTo="/quizzes" />
      <QuizTaker key={`${studentId}:${quizId}`} quizId={quizId} studentId={studentId} />
    </main>
  );
}
