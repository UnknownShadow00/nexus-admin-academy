import { useParams } from "react-router-dom";
import BackLink from "../components/BackLink";
import QuizTaker from "../components/QuizTaker";
import { getCurrentStudent } from "../hooks/useAuth";

export default function QuizPage() {
  const { quizId } = useParams();
  const studentId = getCurrentStudent()?.id;
  return (
    <div className="space-y-4">
      <QuizTaker key={`${studentId}:${quizId}`} quizId={quizId} studentId={studentId} back={<BackLink className="small" fallbackLabel="Back to Quizzes" fallbackTo="/quizzes" />} />
    </div>
  );
}
