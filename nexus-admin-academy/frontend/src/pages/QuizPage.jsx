import { useParams } from "react-router-dom";
import QuizTaker from "../components/QuizTaker";

export default function QuizPage() {
  const { quizId } = useParams();
  return (
    <main className="mx-auto max-w-4xl p-6">
      <QuizTaker quizId={quizId} studentId={1} />
    </main>
  );
}
