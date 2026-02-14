import { useParams } from "react-router-dom";
import QuizTaker from "../components/QuizTaker";
import { getSelectedProfile } from "../services/profile";

export default function QuizPage() {
  const { quizId } = useParams();
  const studentId = getSelectedProfile()?.id || 1;
  return (
    <main className="mx-auto max-w-4xl p-6">
      <QuizTaker quizId={quizId} studentId={studentId} />
    </main>
  );
}
