import { ChevronDown, LogOut, Menu, Moon, Search, Sun, X } from "lucide-react";
import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import AdminAccessGate from "./components/AdminAccessGate";
import RequireAuth from "./components/RequireAuth";
import { clearAuthSession, getCurrentStudent, isAuthenticated } from "./hooks/useAuth";
import { useDarkMode } from "./hooks/useDarkMode";
import AdminLoginPage from "./pages/AdminLoginPage";
import LessonPage from "./pages/LessonPage";
import CapstonePage from "./pages/CapstonePage";
import CapstonesPage from "./pages/CapstonesPage";
import CliLabPage from "./pages/CliLabPage";
import CliLabsPage from "./pages/CliLabsPage";
import CommandReferencePage from "./pages/CommandReferencePage";
import LabPage from "./pages/LabPage";
import LabsPage from "./pages/LabsPage";
import LoginPage from "./pages/LoginPage";
import QuizPage from "./pages/QuizPage";
import QuizReviewPage from "./pages/QuizReviewPage";
import QuizzesPage from "./pages/QuizzesPage";
import StudentHome from "./pages/StudentHome";
import StudyTrackerPage from "./pages/StudyTrackerPage";
import TrainingDashboardPage from "./pages/TrainingDashboardPage";
import TrainingProgressPage from "./pages/TrainingProgressPage";
import TrainingWeekPage from "./pages/TrainingWeekPage";
import TerminalCommandsPage from "./pages/TerminalCommandsPage";
import TicketFeedback from "./pages/TicketFeedback";
import TicketPage from "./pages/TicketPage";
import TicketsPage from "./pages/TicketsPage";
import { authLogout, getTickets, globalSearch } from "./services/api";

const AdminHome = lazy(() => import("./pages/AdminHome"));
const AdminStudentsPage = lazy(() => import("./pages/AdminStudentsPage"));
const ModuleManager = lazy(() => import("./pages/ModuleManager"));
const AICostDashboard = lazy(() => import("./pages/admin/AICostDashboard"));
const AdminCapstonesPage = lazy(() => import("./pages/admin/AdminCapstonesPage"));
const AdminLabsPage = lazy(() => import("./pages/admin/AdminLabsPage"));
const AdminTicketReviewPage = lazy(() => import("./pages/admin/AdminTicketReviewPage"));
const BookmarkletPage = lazy(() => import("./pages/admin/BookmarkletPage"));
const QuestionImportPage = lazy(() => import("./pages/admin/QuestionImportPage"));
const CurriculumEditorPage = lazy(() => import("./pages/admin/CurriculumEditorPage"));
const CurriculumTagsPage = lazy(() => import("./pages/admin/CurriculumTagsPage"));
const QuizEditorPage = lazy(() => import("./pages/admin/QuizEditorPage"));
const AdminTrainingPage = lazy(() => import("./pages/admin/AdminTrainingPage"));
const studentNavItems = [
  { to: "/", label: "Home" },
  { to: "/training", label: "My Training" },
  { to: "/service-desk", label: "Service Desk Simulator", external: true },
  {
    label: "Practice Library",
    children: [
      { to: "/tickets", label: "Support Tickets" },
      { to: "/labs", label: "Guided Labs" },
      { to: "/cli-labs", label: "Networking Labs" },
      { to: "/capstones", label: "Capstones" },
      { to: "/commands", label: "Command Library" },
      { to: "/terminal", label: "Terminal Practice" },
    ],
  },
  { to: "/progress", label: "Progress" },
];

const adminNavItems = [
  { to: "/admin", label: "Dashboard" },
  {
    label: "Learning Content",
    children: [
      { to: "/admin/modules", label: "Modules, Lessons & Quizzes" },
      { to: "/admin/training", label: "Weekly Training" },
      { to: "/admin/curriculum", label: "Study Curriculum" },
      { to: "/admin/curriculum-tags", label: "Job Relevance Tags" },
      { to: "/admin/bookmarklet", label: "ExamCompass Import" },
      { to: "/admin/question-import", label: "Import Questions (CSV/XLSX)" },
    ],
  },
  { to: "/admin/students", label: "Students" },
  {
    label: "Assessments & Labs",
    children: [
      { to: "/admin/ticket-review", label: "Ticket Review" },
      { to: "/admin/labs", label: "Labs & VM Assignments" },
      { to: "/admin/capstones", label: "Capstones" },
    ],
  },
  {
    label: "System",
    children: [{ to: "/admin/ai-costs", label: "AI Usage & Costs" }],
  },
];

const navLinkBase = "rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-900";
const navLinkInactive = "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100";
const navLinkActive = "bg-blue-600 text-white";
const iconButtonClass = "rounded-lg border border-slate-300 p-2 text-slate-700 transition-colors hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800 dark:focus-visible:ring-offset-slate-900";

function AppNav({ items, hasTicketFeedback, isAdminRoute, onNavigate, mobile = false }) {
  const location = useLocation();
  const [openGroup, setOpenGroup] = useState(null);

  useEffect(() => {
    setOpenGroup(null);
  }, [location.pathname]);

  const isPathActive = (path) => {
    if (path === "/" || path === "/admin") return location.pathname === path;
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  const linkContent = (item) => (
    <>
      {item.label}
      {!isAdminRoute && item.to === "/tickets" && hasTicketFeedback ? (
        <span className="ml-2 inline-flex h-2 w-2 rounded-full bg-orange-400" title="New feedback" />
      ) : null}
    </>
  );

  return (
    <nav className={mobile ? "flex flex-col gap-2" : "hidden items-center gap-3 md:flex"}>
      {items.map((item) => {
        if (!item.children) {
          if (item.external) {
            return (
              <a
                key={item.to}
                href={item.to}
                onClick={onNavigate}
                className={`${navLinkBase} ${navLinkInactive}`}
              >
                {linkContent(item)}
              </a>
            );
          }
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/" || item.to === "/admin"}
              onClick={onNavigate}
              className={({ isActive }) => `${navLinkBase} ${isActive ? navLinkActive : navLinkInactive}`}
            >
              {linkContent(item)}
            </NavLink>
          );
        }

        const groupActive = item.children.some((child) => isPathActive(child.to));
        if (mobile) {
          return (
            <div key={item.label} className="rounded-lg border border-slate-200 p-2 dark:border-slate-700">
              <p className={`px-2 pb-1 text-xs font-semibold uppercase tracking-wide ${groupActive ? "text-blue-600 dark:text-blue-400" : "text-slate-500 dark:text-slate-400"}`}>
                {item.label}
              </p>
              <div className="flex flex-col gap-1">
                {item.children.map((child) => (
                  <NavLink
                    key={child.to}
                    to={child.to}
                    onClick={onNavigate}
                    className={({ isActive }) => `${navLinkBase} ${isActive ? navLinkActive : navLinkInactive}`}
                  >
                    {linkContent(child)}
                  </NavLink>
                ))}
              </div>
            </div>
          );
        }

        const isOpen = openGroup === item.label;
        return (
          <div
            key={item.label}
            className="relative"
            onBlur={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget)) setOpenGroup(null);
            }}
            onKeyDown={(event) => {
              if (event.key === "Escape") setOpenGroup(null);
            }}
          >
            <button
              type="button"
              className={`${navLinkBase} inline-flex items-center gap-1 ${groupActive ? navLinkActive : navLinkInactive}`}
              aria-expanded={isOpen}
              aria-haspopup="menu"
              onClick={() => setOpenGroup(isOpen ? null : item.label)}
            >
              {item.label}
              <ChevronDown size={15} aria-hidden="true" />
            </button>
            {isOpen ? (
              <div className="absolute left-0 top-full z-40 mt-2 min-w-56 rounded-xl border border-slate-200 bg-white p-2 shadow-lg dark:border-slate-700 dark:bg-slate-900" role="menu">
                {item.children.map((child) => (
                  <NavLink
                    key={child.to}
                    to={child.to}
                    onClick={onNavigate}
                    className={({ isActive }) => `block ${navLinkBase} ${isActive ? navLinkActive : navLinkInactive}`}
                    role="menuitem"
                  >
                    {linkContent(child)}
                  </NavLink>
                ))}
              </div>
            ) : null}
          </div>
        );
      })}
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
  const [adminAuthenticated, setAdminAuthenticated] = useState(false);
  const [hasTicketFeedback, setHasTicketFeedback] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState({ lessons: [], commands: [] });
  const [searchOpen, setSearchOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const showChrome = (authenticated && !isAdminRoute) || (isAdminRoute && adminAuthenticated);
  const showSearch = authenticated && !isAdminRoute && !isAdminLoginRoute;
  const hasSearchResults = searchResults.lessons?.length || searchResults.commands?.length;

  const navItems = useMemo(() => {
    if (isAdminRoute) {
      if (!adminAuthenticated) return [];
      return adminNavItems;
    }
    const items = studentNavItems.map((item) => item.children ? { ...item, children: [...item.children] } : item);
    if (!currentStudent?.is_mentor && currentStudent?.has_unlocked_capstones === false) {
      return items.map((item) =>
        item.children
          ? { ...item, children: item.children.filter((child) => child.to !== "/capstones") }
          : item
      );
    }
    return items;
  }, [adminAuthenticated, currentStudent?.has_unlocked_capstones, currentStudent?.is_mentor, isAdminRoute]);

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
                            <Link key={`lesson-${lesson.id}`} to={`/lessons/${lesson.id}`} className="block rounded-lg px-2 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
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

      <Suspense fallback={<main className="mx-auto max-w-3xl p-6">Loading page...</main>}>
      <Routes>
        <Route path="/" element={<RequireAuth><StudentHome /></RequireAuth>} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/learning-path" element={<Navigate to="/training" replace />} />
        <Route path="/lessons/:lessonId" element={<RequireAuth><LessonPage /></RequireAuth>} />
        <Route path="/training" element={<RequireAuth><TrainingDashboardPage /></RequireAuth>} />
        <Route path="/training/week/:weekId" element={<RequireAuth><TrainingWeekPage /></RequireAuth>} />
        <Route path="/training/content" element={<RequireAuth><StudyTrackerPage /></RequireAuth>} />
        <Route path="/progress" element={<RequireAuth><TrainingProgressPage /></RequireAuth>} />
        <Route path="/quizzes" element={<RequireAuth><QuizzesPage /></RequireAuth>} />
        <Route path="/study-tracker" element={<Navigate to="/training/content" replace />} />
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

        <Route path="/admin" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><AdminHome /></AdminAccessGate>} />
        <Route path="/admin/ticket-review" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><AdminTicketReviewPage /></AdminAccessGate>} />
        <Route path="/admin/review" element={<Navigate to="/admin/ticket-review" replace />} />
        <Route path="/admin/students" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><AdminStudentsPage /></AdminAccessGate>} />
        <Route path="/admin/modules" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><ModuleManager /></AdminAccessGate>} />
        <Route path="/admin/training" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><AdminTrainingPage /></AdminAccessGate>} />
        <Route path="/admin/labs" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><AdminLabsPage /></AdminAccessGate>} />
        <Route path="/admin/capstones" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><AdminCapstonesPage /></AdminAccessGate>} />
        <Route path="/admin/bookmarklet" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><BookmarkletPage /></AdminAccessGate>} />
        <Route path="/admin/question-import" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><QuestionImportPage /></AdminAccessGate>} />
        <Route path="/admin/curriculum" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><CurriculumEditorPage /></AdminAccessGate>} />
        <Route path="/admin/curriculum-tags" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><CurriculumTagsPage /></AdminAccessGate>} />
        <Route path="/admin/quizzes/:quizId/edit" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><QuizEditorPage /></AdminAccessGate>} />
        <Route path="/admin/ai-costs" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><AICostDashboard /></AdminAccessGate>} />
      </Routes>
      </Suspense>
    </div>
  );
}
