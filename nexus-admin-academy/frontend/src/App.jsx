import { Moon, Sun } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import AdminAccessGate from "./components/AdminAccessGate";
import { useDarkMode } from "./hooks/useDarkMode";
import AdminHome from "./pages/AdminHome";
import AdminReviewPage from "./pages/AdminReviewPage";
import AdminStudentsPage from "./pages/AdminStudentsPage";
import AICostDashboard from "./pages/admin/AICostDashboard";
import BookmarkletPage from "./pages/admin/BookmarkletPage";
import QuizEditorPage from "./pages/admin/QuizEditorPage";
import LearningPath from "./pages/LearningPath";
import ModuleManager from "./pages/ModuleManager";
import QuizPage from "./pages/QuizPage";
import QuizReviewPage from "./pages/QuizReviewPage";
import QuizzesPage from "./pages/QuizzesPage";
import SelectProfile from "./pages/SelectProfile";
import StudentHome from "./pages/StudentHome";
import TerminalCommandsPage from "./pages/TerminalCommandsPage";
import TicketFeedback from "./pages/TicketFeedback";
import TicketPage from "./pages/TicketPage";
import TicketsPage from "./pages/TicketsPage";
import { getStudentStats, getTickets, globalSearch } from "./services/api";
import { getSelectedProfile } from "./services/profile";

const studentNavItems = [
  { to: "/", label: "Home" },
  { to: "/learning-path", label: "Learning Path" },
  { to: "/quizzes", label: "Quizzes" },
  { to: "/tickets", label: "Tickets" },
  { to: "/terminal", label: "Terminal & Commands" },
];

const adminNavItems = [
  { to: "/admin", label: "Admin Home" },
  { to: "/admin/review", label: "Review Tickets" },
  { to: "/admin/students", label: "Students" },
  { to: "/admin/modules", label: "Modules" },
  { to: "/admin/bookmarklet", label: "ExamCompass Import" },
  { to: "/admin/ai-costs", label: "AI Costs" },
];

export default function App() {
  const [isDark, setIsDark] = useDarkMode();
  const location = useLocation();
  const isAdminRoute = location.pathname.startsWith("/admin");
  const selected = getSelectedProfile();
  const [xp, setXp] = useState(0);
  const [hasTicketFeedback, setHasTicketFeedback] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState({ lessons: [], commands: [] });

  const navItems = useMemo(() => (isAdminRoute ? adminNavItems : studentNavItems), [isAdminRoute]);

  useEffect(() => {
    const studentId = selected?.id;
    if (!studentId || isAdminRoute) return;
    const run = async () => {
      try {
        const res = await getStudentStats(studentId);
        setXp(res.data?.total_xp || 0);
      } catch {
        setXp(0);
      }
    };
    run();
  }, [selected, isAdminRoute, location.pathname]);

  useEffect(() => {
    const studentId = selected?.id;
    if (!studentId || isAdminRoute) {
      setHasTicketFeedback(false);
      return;
    }
    const run = async () => {
      try {
        const res = await getTickets(undefined, studentId);
        const rows = Array.isArray(res.data) ? res.data : [];
        setHasTicketFeedback(rows.some((row) => row.status === "needs_revision"));
      } catch {
        setHasTicketFeedback(false);
      }
    };
    run();
  }, [selected, isAdminRoute, location.pathname]);

  useEffect(() => {
    if (isAdminRoute) return;
    const timer = setTimeout(async () => {
      const q = searchQuery.trim();
      if (!q) {
        setSearchResults({ lessons: [], commands: [] });
        return;
      }
      try {
        const res = await globalSearch(q);
        setSearchResults(res.data || { lessons: [], commands: [] });
      } catch {
        setSearchResults({ lessons: [], commands: [] });
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, isAdminRoute]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 dark:bg-slate-950 dark:text-slate-100">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur dark:border-slate-800 dark:bg-slate-900/95">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-2 px-6 py-4">
          <div className="mr-4 text-lg font-bold">Nexus Admin Academy</div>
          <nav className="flex flex-wrap items-center gap-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-blue-600 text-white"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                  }`
                }
              >
                {item.label}
                {!isAdminRoute && item.to === "/tickets" && hasTicketFeedback ? (
                  <span className="ml-2 inline-flex h-2 w-2 rounded-full bg-orange-400" title="New feedback" />
                ) : null}
              </NavLink>
            ))}
          </nav>

          {!isAdminRoute ? (
            <div className="relative ml-auto w-72">
              <input
                className="input-field w-full"
                placeholder="Search lessons or commands..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {(searchResults.lessons?.length || searchResults.commands?.length) ? (
                <div className="absolute z-30 mt-1 max-h-80 w-full overflow-auto rounded border border-slate-200 bg-white p-2 shadow dark:border-slate-700 dark:bg-slate-900">
                  {searchResults.lessons?.length ? <p className="mb-1 text-xs font-semibold text-slate-500">Lessons</p> : null}
                  {(searchResults.lessons || []).map((lesson) => (
                    <Link key={`lesson-${lesson.id}`} to="/learning-path" className="block rounded px-2 py-1 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
                      {lesson.title}
                    </Link>
                  ))}
                  {searchResults.commands?.length ? <p className="mb-1 mt-2 text-xs font-semibold text-slate-500">Commands</p> : null}
                  {(searchResults.commands || []).map((cmd) => (
                    <Link key={`command-${cmd.id}`} to="/terminal" className="block rounded px-2 py-1 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
                      {cmd.command}
                    </Link>
                  ))}
                </div>
              ) : null}
            </div>
          ) : (
            <div className="ml-auto" />
          )}

          <button
            className="rounded-md border border-slate-300 p-2 text-slate-700 dark:border-slate-700 dark:text-slate-200"
            onClick={() => setIsDark(!isDark)}
            aria-label="Toggle dark mode"
          >
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          {!isAdminRoute ? (
            <Link to="/select-profile" className="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700">
              {selected ? `${selected.name} • XP ${xp}` : "Select Profile"}
            </Link>
          ) : null}
        </div>
      </header>

      <Routes>
        <Route path="/" element={<StudentHome />} />
        <Route path="/select-profile" element={<SelectProfile />} />
        <Route path="/learning-path" element={<LearningPath />} />
        <Route path="/quizzes" element={<QuizzesPage />} />
        <Route path="/quizzes/:quizId" element={<QuizPage />} />
        <Route path="/quizzes/:quizId/review" element={<QuizReviewPage />} />
        <Route path="/tickets" element={<TicketsPage />} />
        <Route path="/tickets/:ticketId" element={<TicketPage />} />
        <Route path="/tickets/:submissionId/feedback" element={<TicketFeedback />} />
        <Route path="/terminal" element={<TerminalCommandsPage />} />

        <Route path="/admin" element={<AdminAccessGate><AdminHome /></AdminAccessGate>} />
        <Route path="/admin/review" element={<AdminAccessGate><AdminReviewPage /></AdminAccessGate>} />
        <Route path="/admin/students" element={<AdminAccessGate><AdminStudentsPage /></AdminAccessGate>} />
        <Route path="/admin/modules" element={<AdminAccessGate><ModuleManager /></AdminAccessGate>} />
        <Route path="/admin/bookmarklet" element={<AdminAccessGate><BookmarkletPage /></AdminAccessGate>} />
        <Route path="/admin/quizzes/:quizId/edit" element={<AdminAccessGate><QuizEditorPage /></AdminAccessGate>} />
        <Route path="/admin/ai-costs" element={<AdminAccessGate><AICostDashboard /></AdminAccessGate>} />
      </Routes>
    </div>
  );
}
