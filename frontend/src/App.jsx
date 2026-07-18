import { LogOut, Menu, Moon, Search, Sun, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import AdminAccessGate from "./components/AdminAccessGate";
import RequireAuth from "./components/RequireAuth";
import { clearAuthSession, getCurrentStudent, isAuthenticated } from "./hooks/useAuth";
import { useDarkMode } from "./hooks/useDarkMode";
import AdminHome from "./pages/AdminHome";
import AdminLoginPage from "./pages/AdminLoginPage";
import AdminReviewPage from "./pages/AdminReviewPage";
import AdminStudentsPage from "./pages/AdminStudentsPage";
import AICostDashboard from "./pages/admin/AICostDashboard";
import AdminCapstonesPage from "./pages/admin/AdminCapstonesPage";
import AdminLabsPage from "./pages/admin/AdminLabsPage";
import AdminTicketReviewPage from "./pages/admin/AdminTicketReviewPage";
import BookmarkletPage from "./pages/admin/BookmarkletPage";
import CurriculumEditorPage from "./pages/admin/CurriculumEditorPage";
import CurriculumTagsPage from "./pages/admin/CurriculumTagsPage";
import QuizEditorPage from "./pages/admin/QuizEditorPage";
import LearningPath from "./pages/LearningPath";
import CapstonePage from "./pages/CapstonePage";
import CapstonesPage from "./pages/CapstonesPage";
import CliLabPage from "./pages/CliLabPage";
import CliLabsPage from "./pages/CliLabsPage";
import CommandReferencePage from "./pages/CommandReferencePage";
import LabPage from "./pages/LabPage";
import LabsPage from "./pages/LabsPage";
import LoginPage from "./pages/LoginPage";
import ModuleManager from "./pages/ModuleManager";
import QuizPage from "./pages/QuizPage";
import QuizReviewPage from "./pages/QuizReviewPage";
import QuizzesPage from "./pages/QuizzesPage";
import StudentHome from "./pages/StudentHome";
import StudyTrackerPage from "./pages/StudyTrackerPage";
import TerminalCommandsPage from "./pages/TerminalCommandsPage";
import TicketFeedback from "./pages/TicketFeedback";
import TicketPage from "./pages/TicketPage";
import TicketsPage from "./pages/TicketsPage";
import { authLogout, getTickets, globalSearch } from "./services/api";

const studentNavItems = [
  { to: "/", label: "Home" },
  { to: "/learning-path", label: "Learning Path" },
  { to: "/study-tracker", label: "Study Tracker" },
  { to: "/tickets", label: "Tickets" },
  { to: "/labs", label: "Labs" },
  { to: "/cli-labs", label: "Networking Labs" },
  { to: "/capstones", label: "Capstones" },
  { to: "/commands", label: "Command Library" },
  { to: "/terminal", label: "Terminal Practice" },
];

const adminNavItems = [
  { to: "/admin", label: "Admin Home" },
  { to: "/admin/ticket-review", label: "Ticket Review Queue" },
  { to: "/admin/review", label: "Review Tickets" },
  { to: "/admin/students", label: "Students" },
  { to: "/admin/modules", label: "Modules" },
  { to: "/admin/labs", label: "Labs" },
  { to: "/admin/capstones", label: "Capstones" },
  { to: "/admin/bookmarklet", label: "ExamCompass Import" },
  { to: "/admin/curriculum", label: "Curriculum" },
  { to: "/admin/curriculum-tags", label: "Job Tags" },
  { to: "/admin/ai-costs", label: "AI Costs" },
];

const mentorNavItems = [
  { to: "/admin/ticket-review", label: "Ticket Review Queue" },
  { to: "/admin/review", label: "Review Tickets" },
  { to: "/admin/students", label: "Students" },
  { to: "/admin/curriculum", label: "Curriculum" },
];

const navLinkBase = "rounded-lg px-3 py-2 text-sm font-medium transition-colors";
const navLinkInactive = "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100";
const navLinkActive = "bg-blue-600 text-white";
const iconButtonClass = "rounded-lg border border-slate-300 p-2 text-slate-700 transition-colors hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800";

function AppNav({ items, hasTicketFeedback, isAdminRoute, onNavigate, mobile = false }) {
  return (
    <nav className={mobile ? "flex flex-col gap-2" : "hidden items-center gap-3 md:flex"}>
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === "/"}
          onClick={onNavigate}
          className={({ isActive }) => `${navLinkBase} ${isActive ? navLinkActive : navLinkInactive}`}
        >
          {item.label}
          {!isAdminRoute && item.to === "/tickets" && hasTicketFeedback ? (
            <span className="ml-2 inline-flex h-2 w-2 rounded-full bg-orange-400" title="New feedback" />
          ) : null}
        </NavLink>
      ))}
    </nav>
  );
}

export default function App() {
  const [isDark, setIsDark] = useDarkMode();
  const location = useLocation();
  const navigate = useNavigate();
  const isAdminRoute = location.pathname === "/admin" || location.pathname.startsWith("/admin/");
  const isAdminLoginRoute = location.pathname === "/admin-login";
  const authenticated = isAuthenticated();
  const currentStudent = authenticated ? getCurrentStudent() : null;
  const [hasTicketFeedback, setHasTicketFeedback] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState({ lessons: [], commands: [] });
  const [searchOpen, setSearchOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const showChrome = authenticated || isAdminRoute;
  const showSearch = authenticated && !isAdminRoute && !isAdminLoginRoute;
  const hasSearchResults = searchResults.lessons?.length || searchResults.commands?.length;

  const navItems = useMemo(() => {
    if (isAdminRoute) {
      return currentStudent?.is_mentor ? mentorNavItems : adminNavItems;
    }
    if (!currentStudent?.is_mentor && currentStudent?.has_unlocked_capstones === false) {
      return studentNavItems.filter((item) => item.to !== "/capstones");
    }
    return studentNavItems;
  }, [isAdminRoute, currentStudent?.has_unlocked_capstones, currentStudent?.is_mentor]);

  useEffect(() => {
    setMobileOpen(false);
    setSearchOpen(false);
    setSearchQuery("");
    setSearchResults({ lessons: [], commands: [] });
  }, [location.pathname]);

  useEffect(() => {
    const studentId = currentStudent?.id;
    if (!authenticated || !studentId || isAdminRoute || isAdminLoginRoute) {
      setHasTicketFeedback(false);
      return;
    }
    const run = async () => {
      try {
        const res = await getTickets(undefined, studentId, { suppressToast: true });
        const rows = Array.isArray(res.data) ? res.data : [];
        setHasTicketFeedback(rows.some((row) => row.status === "needs_revision"));
      } catch {
        setHasTicketFeedback(false);
      }
    };
    run();
  }, [authenticated, currentStudent?.id, isAdminLoginRoute, isAdminRoute, location.pathname]);

  useEffect(() => {
    if (!showSearch || !searchOpen) return;
    const timer = setTimeout(async () => {
      const q = searchQuery.trim();
      if (!q) {
        setSearchResults({ lessons: [], commands: [] });
        return;
      }
      try {
        const res = await globalSearch(q, { suppressToast: true });
        setSearchResults(res.data || { lessons: [], commands: [] });
      } catch {
        setSearchResults({ lessons: [], commands: [] });
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchOpen, searchQuery, showSearch]);

  async function handleLogout() {
    try {
      await authLogout({ suppressToast: true });
    } catch {
      // Local cleanup still logs the browser out if the backend is unavailable.
    }
    clearAuthSession();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 dark:bg-slate-950 dark:text-slate-100">
      {showChrome ? (
        <header className="relative sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur dark:border-slate-800 dark:bg-slate-900/95">
          <div className="mx-auto flex max-w-7xl items-center gap-3 px-6 py-4">
            <div className="text-lg font-bold">Nexus Admin Academy</div>
            <AppNav items={navItems} hasTicketFeedback={hasTicketFeedback} isAdminRoute={isAdminRoute} />
            <div className="ml-auto flex items-center gap-3">
              <button
                className={`${iconButtonClass} md:hidden`}
                onClick={() => setMobileOpen((o) => !o)}
                aria-label="Toggle menu"
              >
                {mobileOpen ? <X size={18} /> : <Menu size={18} />}
              </button>
              {showSearch ? (
                <div className="relative">
                  <button
                    className={iconButtonClass}
                    onClick={() => setSearchOpen((open) => !open)}
                    aria-expanded={searchOpen}
                    aria-label="Toggle search"
                    type="button"
                  >
                    <Search size={18} />
                  </button>
                  {searchOpen ? (
                    <div className="absolute right-0 top-full z-30 mt-3 w-[min(22rem,calc(100vw-3rem))] rounded-xl border border-slate-200 bg-white p-3 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                      <input
                        className="input-field w-full"
                        placeholder="Search lessons or commands..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                      />
                      {hasSearchResults ? (
                        <div className="mt-3 max-h-80 overflow-auto">
                          {searchResults.lessons?.length ? <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Lessons</p> : null}
                          {(searchResults.lessons || []).map((lesson) => (
                            <Link key={`lesson-${lesson.id}`} to="/learning-path" className="block rounded-lg px-2 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
                              {lesson.title}
                            </Link>
                          ))}
                          {searchResults.commands?.length ? <p className="mb-1 mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Commands</p> : null}
                          {(searchResults.commands || []).map((cmd) => (
                            <Link key={`command-${cmd.id}`} to="/commands" className="block rounded-lg px-2 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
                              {cmd.command}
                            </Link>
                          ))}
                        </div>
                      ) : searchQuery.trim() ? (
                        <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">No matches found.</p>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}

              <button
                className={iconButtonClass}
                onClick={() => setIsDark(!isDark)}
                aria-label="Toggle dark mode"
                type="button"
              >
                {isDark ? <Sun size={18} /> : <Moon size={18} />}
              </button>

              {!isAdminRoute ? (
                <button
                  className="hidden items-center gap-2 rounded-full border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 md:inline-flex dark:border-slate-700 dark:text-slate-200"
                  onClick={handleLogout}
                  type="button"
                >
                  <span>{currentStudent?.name || "Student"}</span>
                  <LogOut size={16} />
                </button>
              ) : null}
            </div>
            {mobileOpen ? (
              <div className="absolute inset-x-0 top-full z-30 border-b border-slate-200 bg-white px-6 py-4 shadow-lg md:hidden dark:border-slate-800 dark:bg-slate-900">
                <div className="flex flex-col gap-3">
                  <AppNav items={navItems} hasTicketFeedback={hasTicketFeedback} isAdminRoute={isAdminRoute} onNavigate={() => setMobileOpen(false)} mobile />
                  {!isAdminRoute ? (
                    <button
                      className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 dark:border-slate-700 dark:text-slate-200"
                      onClick={handleLogout}
                      type="button"
                    >
                      <span>{currentStudent?.name || "Student"}</span>
                      <LogOut size={16} />
                    </button>
                  ) : null}
                </div>
              </div>
            ) : null}
          </div>
        </header>
      ) : null}

      <Routes>
        <Route path="/" element={<RequireAuth><StudentHome /></RequireAuth>} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/learning-path" element={<RequireAuth><LearningPath /></RequireAuth>} />
        <Route path="/quizzes" element={<RequireAuth><QuizzesPage /></RequireAuth>} />
        <Route path="/study-tracker" element={<RequireAuth><StudyTrackerPage /></RequireAuth>} />
        <Route path="/quizzes/:quizId" element={<RequireAuth><QuizPage /></RequireAuth>} />
        <Route path="/quizzes/:quizId/review" element={<RequireAuth><QuizReviewPage /></RequireAuth>} />
        <Route path="/tickets" element={<RequireAuth><TicketsPage /></RequireAuth>} />
        <Route path="/tickets/:ticketId" element={<RequireAuth><TicketPage /></RequireAuth>} />
        <Route path="/tickets/:submissionId/feedback" element={<RequireAuth><TicketFeedback /></RequireAuth>} />
        <Route path="/labs" element={<RequireAuth><LabsPage /></RequireAuth>} />
        <Route path="/labs/:labId" element={<RequireAuth><LabPage /></RequireAuth>} />
        <Route path="/cli-labs" element={<RequireAuth><CliLabsPage /></RequireAuth>} />
        <Route path="/cli-labs/:labId" element={<RequireAuth><CliLabPage /></RequireAuth>} />
        <Route path="/capstones" element={<RequireAuth><CapstonesPage /></RequireAuth>} />
        <Route path="/capstones/:capstoneId" element={<RequireAuth><CapstonePage /></RequireAuth>} />
        <Route path="/commands" element={<RequireAuth><CommandReferencePage /></RequireAuth>} />
        <Route path="/terminal" element={<RequireAuth><TerminalCommandsPage /></RequireAuth>} />
        <Route path="/admin-login" element={<AdminLoginPage />} />

        <Route path="/admin" element={<AdminAccessGate><AdminHome /></AdminAccessGate>} />
        <Route path="/admin/ticket-review" element={<AdminAccessGate><AdminTicketReviewPage /></AdminAccessGate>} />
        <Route path="/admin/review" element={<AdminAccessGate><AdminReviewPage /></AdminAccessGate>} />
        <Route path="/admin/students" element={<AdminAccessGate><AdminStudentsPage /></AdminAccessGate>} />
        <Route path="/admin/modules" element={<AdminAccessGate><ModuleManager /></AdminAccessGate>} />
        <Route path="/admin/labs" element={<AdminAccessGate><AdminLabsPage /></AdminAccessGate>} />
        <Route path="/admin/capstones" element={<AdminAccessGate><AdminCapstonesPage /></AdminAccessGate>} />
        <Route path="/admin/bookmarklet" element={<AdminAccessGate><BookmarkletPage /></AdminAccessGate>} />
        <Route path="/admin/curriculum" element={<AdminAccessGate><CurriculumEditorPage /></AdminAccessGate>} />
        <Route path="/admin/curriculum-tags" element={<AdminAccessGate><CurriculumTagsPage /></AdminAccessGate>} />
        <Route path="/admin/quizzes/:quizId/edit" element={<AdminAccessGate><QuizEditorPage /></AdminAccessGate>} />
        <Route path="/admin/ai-costs" element={<AdminAccessGate><AICostDashboard /></AdminAccessGate>} />
      </Routes>
    </div>
  );
}
