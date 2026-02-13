import { Link, Route, Routes } from "react-router-dom";
import AdminHome from "./pages/AdminHome";
import QuizPage from "./pages/QuizPage";
import StudentHome from "./pages/StudentHome";
import TicketPage from "./pages/TicketPage";

export default function App() {
  return (
    <div>
      <header className="border-b bg-white">
        <nav className="mx-auto flex max-w-6xl gap-4 p-4">
          <Link to="/">Student</Link>
          <Link to="/admin">Admin</Link>
          <Link to="/quizzes/1">Quiz Demo</Link>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<StudentHome />} />
        <Route path="/admin" element={<AdminHome />} />
        <Route path="/quizzes/:quizId" element={<QuizPage />} />
        <Route path="/tickets/:ticketId" element={<TicketPage />} />
      </Routes>
    </div>
  );
}
