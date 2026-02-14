import { Moon, Sun } from "lucide-react";
import { Link, Route, Routes } from "react-router-dom";
import { useDarkMode } from "./hooks/useDarkMode";
import AdminHome from "./pages/AdminHome";
import AdminReviewPage from "./pages/AdminReviewPage";
import AdminStudentsPage from "./pages/AdminStudentsPage";
import AICostDashboard from "./pages/admin/AICostDashboard";
import CommandReference from "./pages/CommandReference";
import QuizPage from "./pages/QuizPage";
import QuizzesPage from "./pages/QuizzesPage";
import ResourcesPage from "./pages/ResourcesPage";
import StudentHome from "./pages/StudentHome";
import TicketFeedback from "./pages/TicketFeedback";
import TicketPage from "./pages/TicketPage";
import TicketsPage from "./pages/TicketsPage";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/quizzes", label: "Quizzes" },
  { to: "/tickets", label: "Tickets" },
  { to: "/resources", label: "Resources" },
  { to: "/commands", label: "Commands" },
  { to: "/admin", label: "Admin" },
  { to: "/admin/review", label: "Review" },
  { to: "/admin/students", label: "Students" },
  { to: "/admin/ai-costs", label: "AI Costs" },
];

export default function App() {
  const [isDark, setIsDark] = useDarkMode();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 dark:bg-slate-950 dark:text-slate-100">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur dark:border-slate-800 dark:bg-slate-900/95">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-2 px-6 py-4">
          <div className="mr-4 text-lg font-bold">Nexus Admin Academy</div>
          <nav className="flex flex-wrap items-center gap-2">
            {navItems.map((item) => (
              <Link key={item.to} to={item.to} className="rounded-md px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100">
                {item.label}
              </Link>
            ))}
          </nav>
          <button
            className="ml-auto rounded-md border border-slate-300 p-2 text-slate-700 dark:border-slate-700 dark:text-slate-200"
            onClick={() => setIsDark(!isDark)}
            aria-label="Toggle dark mode"
          >
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </header>

      <Routes>
        <Route path="/" element={<StudentHome />} />
        <Route path="/quizzes" element={<QuizzesPage />} />
        <Route path="/tickets" element={<TicketsPage />} />
        <Route path="/resources" element={<ResourcesPage />} />
        <Route path="/commands" element={<CommandReference />} />
        <Route path="/admin" element={<AdminHome />} />
        <Route path="/admin/review" element={<AdminReviewPage />} />
        <Route path="/admin/students" element={<AdminStudentsPage />} />
        <Route path="/admin/ai-costs" element={<AICostDashboard />} />
        <Route path="/quizzes/:quizId" element={<QuizPage />} />
        <Route path="/tickets/:submissionId/feedback" element={<TicketFeedback />} />
        <Route path="/tickets/:ticketId" element={<TicketPage />} />
      </Routes>
    </div>
  );
}
