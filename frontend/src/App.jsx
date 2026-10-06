import { BarChart3, BookOpen, ChevronDown, Home, LogOut, Menu, Moon, Search, Sun, Ticket, Wrench, X } from "lucide-react";
import { lazy, Suspense, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import AdminAccessGate from "./components/AdminAccessGate";
import ReportIssueButton from "./components/ReportIssueButton";
import RequireAuth from "./components/RequireAuth";
import { clearAuthSession, getCurrentStudent, isAuthenticated } from "./hooks/useAuth";
import { useDarkMode } from "./hooks/useDarkMode";
import { setStudentMonitoringUser, syncRouteMonitoringContext } from "./monitoring/sentry";
import { withSentryReactRouterV7Routing } from "@sentry/react";
import AdminLoginPage from "./pages/AdminLoginPage";
import LoginPage from "./pages/LoginPage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import StudentHome from "./pages/StudentHome";
import { authLogout, getAdminV2PracticalReviews, globalSearch } from "./services/api";
import { V2_CURRICULUM_ENABLED } from "./config/features";
import { useV2Access } from "./hooks/useV2Access";

const LessonPage = lazy(() => import("./pages/LessonPage"));
const CapstonePage = lazy(() => import("./pages/CapstonePage"));
const CapstonesPage = lazy(() => import("./pages/CapstonesPage"));
const CliLabPage = lazy(() => import("./pages/CliLabPage"));
const CliLabsPage = lazy(() => import("./pages/CliLabsPage"));
const CommandReferencePage = lazy(() => import("./pages/CommandReferencePage"));
const LabPage = lazy(() => import("./pages/LabPage"));
const LabsPage = lazy(() => import("./pages/LabsPage"));
const QuizPage = lazy(() => import("./pages/QuizPage"));
const QuizReviewPage = lazy(() => import("./pages/QuizReviewPage"));
const QuizzesPage = lazy(() => import("./pages/QuizzesPage"));
const StudyTrackerPage = lazy(() => import("./pages/StudyTrackerPage"));
const TrainingDashboardPage = lazy(() => import("./pages/TrainingDashboardPage"));
const TrainingProgressPage = lazy(() => import("./pages/TrainingProgressPage"));
const TrainingWeekPage = lazy(() => import("./pages/TrainingWeekPage"));
const TerminalCommandsPage = lazy(() => import("./pages/TerminalCommandsPage"));
const AdminHome = lazy(() => import("./pages/AdminHome"));
const AdminStudentsPage = lazy(() => import("./pages/AdminStudentsPage"));
const ModuleManager = lazy(() => import("./pages/ModuleManager"));
const AICostDashboard = lazy(() => import("./pages/admin/AICostDashboard"));
const AdminCapstonesPage = lazy(() => import("./pages/admin/AdminCapstonesPage"));
const AdminLabsPage = lazy(() => import("./pages/admin/AdminLabsPage"));
const AdminServiceDeskReviewPage = lazy(() => import("./pages/admin/AdminServiceDeskReviewPage"));
const BookmarkletPage = lazy(() => import("./pages/admin/BookmarkletPage"));
const QuestionImportPage = lazy(() => import("./pages/admin/QuestionImportPage"));
const CurriculumEditorPage = lazy(() => import("./pages/admin/CurriculumEditorPage"));
const CurriculumTagsPage = lazy(() => import("./pages/admin/CurriculumTagsPage"));
const QuizEditorPage = lazy(() => import("./pages/admin/QuizEditorPage"));
const AdminTrainingPage = lazy(() => import("./pages/admin/AdminTrainingPage"));
const V2MentorProgressPage = lazy(() => import("./pages/admin/V2MentorProgressPage"));
const V2MentorStudentPage = lazy(() => import("./pages/admin/V2MentorStudentPage"));
const V2MentorGradePage = lazy(() => import("./pages/admin/V2MentorGradePage"));
const V2LearningPage = lazy(() => import("./pages/v2/V2LearningPage"));
const V2ModulePage = lazy(() => import("./pages/v2/V2ModulePage"));
const V2LessonPage = lazy(() => import("./pages/v2/V2LessonPage"));
const V2InteractionPage = lazy(() => import("./pages/v2/V2InteractionPage"));
const V2AssessmentPage = lazy(() => import("./pages/v2/V2AssessmentPage"));
const V2ExplainPage = lazy(() => import("./pages/v2/V2ExplainPage"));
const V2PracticalRedirect = lazy(() => import("./pages/v2/V2PracticalRedirect"));
const V2ServiceDeskRedirect = lazy(() => import("./pages/v2/V2ServiceDeskRedirect"));
export function buildStudentNavItems(v2Enabled) {
  if (!v2Enabled) {
    return [
      { to: "/", label: "Today" },
      { to: "/service-desk", label: "Service Desk", external: true },
      { to: "/learning-path", label: "Progress" },
    ];
  }
  return [
    { to: "/", label: "Today" },
    { to: "/learning-v2", label: "My Course" },
    { to: "/service-desk", label: "Service Desk", external: true },
    { to: "/progress", label: "Progress" },
    { label: "Extra Practice", children: [
      { to: "/learning-path", label: "Practice path" },
      { to: "/labs", label: "Labs" },
      { to: "/cli-labs", label: "CLI Labs" },
      { to: "/commands", label: "Command Reference" },
    ] },
  ];
}

const adminNavItems = [
  { to: "/admin", label: "Dashboard" },
  {
    label: "Learning Content",
    children: [
      { to: "/admin/modules", label: "Modules, Lessons & Quizzes" },
      { to: "/admin/training", label: "Curriculum Structure" },
      { to: "/admin/curriculum", label: "Study Curriculum" },
      { to: "/admin/curriculum-tags", label: "Job Relevance Tags" },
      { to: "/admin/bookmarklet", label: "ExamCompass Import" },
      { to: "/admin/question-import", label: "Import Questions (CSV/XLSX)" },
    ],
  },
  { to: "/admin/students", label: "Students" },
  ...(V2_CURRICULUM_ENABLED ? [{ to: "/admin/v2-progress", label: "V2 Student Progress" }] : []),
  {
    label: "Assessments & Labs",
    children: [
      { to: "/admin/service-desk-review", label: "Service Desk Review" },
      { to: "/admin/labs", label: "Labs & VM Assignments" },
      { to: "/admin/capstones", label: "Capstones" },
    ],
  },
  {
    label: "System",
    children: [{ to: "/admin/ai-costs", label: "AI Usage & Costs" }],
  },
];

const bottomIcons = { Today: Home, "My Course": BookOpen, "Service Desk": Ticket, Progress: BarChart3, "Extra Practice": Wrench };
const bottomLabels = { "My Course": "Course", "Service Desk": "Desk", "Extra Practice": "Practice" };
const MonitoredRoutes = withSentryReactRouterV7Routing(Routes);

function NotFoundPage() {
  return (
    <main className="mx-auto max-w-xl px-6 py-16 text-center">
      <p className="text-sm font-semibold uppercase tracking-wide text-blue-600">Page not found</p>
      <h1 className="mt-2 text-3xl font-bold">That page is not part of your learning path.</h1>
      <p className="mt-3 text-slate-600 dark:text-slate-300">Return to Today to continue with your next required activity.</p>
      <Link className="btn-primary mt-6 inline-flex" to="/">Go to Today</Link>
    </main>
  );
}

export function isCoursePracticalLocation(location) {
  if (!location.pathname.startsWith("/labs/")) return false;
  const params = new URLSearchParams(location.search);
  return Boolean(params.get("v2Module") && params.get("v2Assessment"));
}

export function isNavItemActive(item, location, coursePractical = isCoursePracticalLocation(location)) {
  if (item.children) return item.children.some((child) => isNavItemActive(child, location, coursePractical));
  const path = item.to?.split(/[?#]/)[0];
  if (!path) return false;
  const hash = item.to?.split("#")[1];
  if (hash && location.hash !== `#${hash}`) return false;
  if (path === "/admin/labs" && !hash && location.hash === "#pending-reviews") return false;
  if (coursePractical && path === "/labs") return false;
  if (coursePractical && path === "/learning-v2") return true;
  if (path === "/progress" && location.pathname === "/skills") return true;
  if (path === "/" || path === "/admin") return location.pathname === path;
  return location.pathname === path || location.pathname.startsWith(`${path}/`);
}

export function AppNav({ items, isAdminRoute, onNavigate, mobile = false }) {
  const location = useLocation();
  const [openGroup, setOpenGroup] = useState(null);
  const coursePractical = !isAdminRoute && isCoursePracticalLocation(location);

  useEffect(() => {
    setOpenGroup(null);
  }, [location.pathname, location.search]);

  return (
    <nav aria-label={mobile ? "All navigation" : "Primary navigation"} className={mobile ? "app-menu-nav" : "app-nav"}>
      {items.map((item) => {
        if (!item.children) {
          const active = isNavItemActive(item, location, coursePractical);
          const props = { className: "app-nav-link", "aria-current": active ? "page" : undefined, onClick: onNavigate };
          return item.external ? <a key={item.to} {...props} href={item.to}>{item.label}</a> : <Link key={item.to} {...props} to={item.to}>{item.label}</Link>;
        }

        const groupActive = isNavItemActive(item, location, coursePractical);
        if (mobile) {
          return (
            <div key={item.label} className="app-menu-group">
              <p className="app-menu-group-label">{item.label}</p>
              <div className="grid gap-1">
                {item.children.map((child) => <Link key={child.to} to={child.to} onClick={onNavigate} aria-current={isNavItemActive(child, location, coursePractical) ? "page" : undefined} className="app-nav-link">{child.label}</Link>)}
              </div>
            </div>
          );
        }

        const isOpen = openGroup === item.label;
        return (
          <div
            key={item.label}
            className="app-nav-group"
            onBlur={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget)) setOpenGroup(null);
            }}
            onKeyDown={(event) => {
              if (event.key === "Escape") setOpenGroup(null);
            }}
          >
            <button
              type="button"
              className="app-nav-link"
              aria-current={groupActive ? "page" : undefined}
              aria-expanded={isOpen}
              aria-haspopup="true"
              onClick={() => setOpenGroup(isOpen ? null : item.label)}
            >
              {item.label}
              <ChevronDown size={15} aria-hidden="true" />
            </button>
            {isOpen ? (
              <div className="app-popover !left-0 !right-auto !w-60" aria-label={`${item.label} destinations`}>
                {item.children.map((child) => <Link key={child.to} to={child.to} onClick={() => { setOpenGroup(null); onNavigate?.(); }} className="app-nav-link flex w-full" aria-current={isNavItemActive(child, location, coursePractical) ? "page" : undefined}>{child.label}</Link>)}
              </div>
            ) : null}
          </div>
        );
      })}
    </nav>
  );
}

export function BottomNav({ items, menuOpen = false }) {
  const location = useLocation();
  const coursePractical = isCoursePracticalLocation(location);
  return <nav aria-label="Mobile primary navigation" aria-hidden={menuOpen || undefined} className="app-bottom-nav" inert={menuOpen ? "" : undefined}>
    {items.map((item) => {
      const target = item.children?.[0] || item;
      const active = isNavItemActive(item, location, coursePractical);
      const Icon = bottomIcons[item.label] || Home;
      const content = <><Icon size={20} strokeWidth={active ? 2.4 : 1.9} aria-hidden="true" /><span>{bottomLabels[item.label] || item.label}</span></>;
      const props = { className: "app-bottom-nav-link", "aria-label": item.label, "aria-current": active ? "page" : undefined };
      return target.external ? <a key={item.label} {...props} href={target.to}>{content}</a> : <Link key={item.label} {...props} to={target.to}>{content}</Link>;
    })}
  </nav>;
}

export default function App() {
  const [isDark, setIsDark] = useDarkMode();
  const location = useLocation();
  const navigate = useNavigate();
  const isAdminRoute = location.pathname === "/admin" || location.pathname.startsWith("/admin/");
  const isAdminLoginRoute = location.pathname === "/admin-login";
  const authenticated = isAuthenticated();
  const currentStudent = authenticated ? getCurrentStudent() : null;
  const passwordChangeRequired = Boolean(currentStudent?.must_change_password);
  const [adminAuthenticated, setAdminAuthenticated] = useState(false);
  const [pendingReviewCount, setPendingReviewCount] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState({ lessons: [], commands: [] });
  const [searchOpen, setSearchOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const searchAnchor = useRef(null);
  const searchButton = useRef(null);
  const searchInput = useRef(null);
  const accountAnchor = useRef(null);
  const accountButton = useRef(null);
  const accountPanel = useRef(null);
  const brandLink = useRef(null);
  const headerRef = useRef(null);
  const menuButton = useRef(null);
  const menuPanel = useRef(null);
  const showChrome = (authenticated && !isAdminRoute && !passwordChangeRequired) || (isAdminRoute && adminAuthenticated);
  const showSearch = authenticated && !isAdminRoute && !isAdminLoginRoute && !passwordChangeRequired;
  const hasSearchResults = searchResults.lessons?.length || searchResults.commands?.length;

  // Student V2 navigation follows the student's own pilot enrolment, which
  // only the backend knows. The build flag says V2 exists; it cannot say who
  // is in the pilot. Routes stay compiled either way — the server refuses a
  // typed V2 URL from a student who is not enrolled.
  const { studentEnabled: v2StudentEnabled } = useV2Access(authenticated && !isAdminRoute && !passwordChangeRequired);

  const navItems = useMemo(() => {
    if (isAdminRoute) {
      if (!adminAuthenticated) return [];
      return [{ to: "/admin/labs#pending-reviews", label: `Pending Reviews (${pendingReviewCount})` }, ...adminNavItems];
    }
    return buildStudentNavItems(v2StudentEnabled);
  }, [adminAuthenticated, isAdminRoute, pendingReviewCount, v2StudentEnabled]);

  useEffect(() => {
    if (!adminAuthenticated || !isAdminRoute) return undefined;
    let active = true;
    const refresh = () => getAdminV2PracticalReviews({ suppressToast: true }).then(({ data }) => { if (active) setPendingReviewCount(data?.length || 0); }).catch(() => { if (active) setPendingReviewCount(0); });
    refresh();
    window.addEventListener("v2-practical-reviews-changed", refresh);
    return () => { active = false; window.removeEventListener("v2-practical-reviews-changed", refresh); };
  }, [adminAuthenticated, isAdminRoute, location.pathname]);

  useEffect(() => {
    setMobileOpen(false);
    setAccountOpen(false);
    setSearchOpen(false);
    setSearchQuery("");
    setSearchResults({ lessons: [], commands: [] });
  }, [location.pathname]);

  useEffect(() => { if (searchOpen) searchInput.current?.focus(); }, [searchOpen]);
  useEffect(() => { if (accountOpen) accountPanel.current?.querySelector("button")?.focus(); }, [accountOpen]);
  useEffect(() => { if (mobileOpen) menuPanel.current?.querySelector("a, button")?.focus(); }, [mobileOpen]);

  useEffect(() => {
    if (!mobileOpen) return undefined;
    const closeOnEscape = (event) => {
      if (event.key !== "Escape") return;
      setMobileOpen(false);
      menuButton.current?.focus();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [mobileOpen]);

  useEffect(() => {
    const header = headerRef.current;
    if (!header) return undefined;
    const closeOnWideHeader = () => {
      if (header.clientWidth < (isAdminRoute ? 1440 : 1280) || !menuPanel.current) return;
      if (menuPanel.current.contains(document.activeElement)) brandLink.current?.focus();
      setMobileOpen(false);
    };
    closeOnWideHeader();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", closeOnWideHeader);
      return () => window.removeEventListener("resize", closeOnWideHeader);
    }
    const observer = new ResizeObserver(closeOnWideHeader);
    observer.observe(header);
    return () => observer.disconnect();
  }, [isAdminRoute, showChrome]);

  useEffect(() => {
    if (!searchOpen && !accountOpen) return undefined;
    const closeOutside = (event) => {
      if (searchOpen && !searchAnchor.current?.contains(event.target)) setSearchOpen(false);
      if (accountOpen && !accountAnchor.current?.contains(event.target)) setAccountOpen(false);
    };
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, [accountOpen, searchOpen]);

  useLayoutEffect(() => {
    syncRouteMonitoringContext(location);
    setStudentMonitoringUser(!isAdminRoute ? currentStudent : null);
  }, [currentStudent?.id, isAdminRoute, location.pathname, location.search]);

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
    <div className="app-root">
      {showChrome ? <>
        <header ref={headerRef} className={`app-header${isAdminRoute ? " app-header-admin" : ""}`}>
          <div className="app-header-inner">
            <Link ref={brandLink} className="app-brand" to={isAdminRoute ? "/admin" : "/"} aria-label="Nexus Admin Academy home">
              <span className="app-brand-mark" aria-hidden="true">N</span>
              <span><span className="app-brand-title">Nexus</span><span className="app-brand-subtitle">Admin Academy</span></span>
            </Link>
            <AppNav items={navItems} isAdminRoute={isAdminRoute} />
            <div className="app-toolbar">
              {showSearch ? <div ref={searchAnchor} className="app-popover-anchor">
                <button ref={searchButton} className="app-icon-button" onClick={() => { setSearchOpen((open) => !open); setAccountOpen(false); setMobileOpen(false); }} aria-expanded={searchOpen} aria-controls={searchOpen ? "app-search-panel" : undefined} aria-label="Toggle search" type="button"><Search size={19} aria-hidden="true" /></button>
                {searchOpen ? <div id="app-search-panel" className="app-popover" role="search" onKeyDown={(event) => { if (event.key === "Escape") { setSearchOpen(false); searchButton.current?.focus(); } }}>
                  <label className="type-label mb-2 block" htmlFor="app-search-input">Search Nexus</label>
                  <input ref={searchInput} id="app-search-input" className="input-field" placeholder="Search lessons or commands..." value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} />
                  {hasSearchResults ? <div className="mt-3 max-h-80 overflow-auto">
                    {searchResults.lessons?.length ? <p className="type-label mb-1">Lessons</p> : null}
                    {(searchResults.lessons || []).map((lesson) => <Link key={`lesson-${lesson.id}`} to={`/lessons/${lesson.id}`} onClick={() => setSearchOpen(false)} className="app-nav-link flex w-full">{lesson.title}</Link>)}
                    {searchResults.commands?.length ? <p className="type-label mb-1 mt-3">Commands</p> : null}
                    {(searchResults.commands || []).map((cmd) => <Link key={`command-${cmd.id}`} to="/commands" onClick={() => setSearchOpen(false)} className="app-nav-link flex w-full">{cmd.command}</Link>)}
                  </div> : searchQuery.trim() ? <p className="type-secondary mt-3">No matches found.</p> : null}
                </div> : null}
              </div> : null}
              {!isAdminRoute ? <div className="hidden xl:block"><ReportIssueButton compact /></div> : null}
              <button className="app-icon-button" onClick={() => setIsDark(!isDark)} aria-label="Toggle dark mode" aria-pressed={isDark} type="button">{isDark ? <Sun size={19} aria-hidden="true" /> : <Moon size={19} aria-hidden="true" />}</button>
              {!isAdminRoute ? <div ref={accountAnchor} className="app-popover-anchor">
                <button ref={accountButton} className="app-account-button" onClick={() => { setAccountOpen((open) => !open); setSearchOpen(false); setMobileOpen(false); }} aria-expanded={accountOpen} aria-controls={accountOpen ? "app-account-panel" : undefined} aria-label="Account menu" type="button">
                  <span className="app-account-avatar" aria-hidden="true">{(currentStudent?.name || "Student").slice(0, 1).toUpperCase()}</span>
                  <span className="hidden max-w-28 truncate 2xl:inline">{currentStudent?.name || "Student"}</span>
                  <ChevronDown className="hidden 2xl:block" size={15} aria-hidden="true" />
                </button>
                {accountOpen ? <div ref={accountPanel} id="app-account-panel" className="app-popover !w-56" role="group" aria-label="Account actions" onKeyDown={(event) => { if (event.key === "Escape") { setAccountOpen(false); accountButton.current?.focus(); } }}>
                  <p className="type-label mb-1">Signed in as</p><p className="truncate font-semibold">{currentStudent?.name || "Student"}</p>
                  <button className="btn-quiet mt-3 w-full justify-start" onClick={handleLogout} type="button"><LogOut size={16} aria-hidden="true" />Sign out</button>
                </div> : null}
              </div> : null}
              <button ref={menuButton} className="app-icon-button app-menu-toggle" onClick={() => { setMobileOpen((open) => !open); setSearchOpen(false); setAccountOpen(false); }} aria-label="Toggle menu" aria-expanded={mobileOpen} aria-controls={mobileOpen ? "app-mobile-menu" : undefined} type="button">{mobileOpen ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}</button>
            </div>
          </div>
          {mobileOpen ? <>
            <div className="app-menu-backdrop" aria-hidden="true" onClick={() => { setMobileOpen(false); menuButton.current?.focus(); }} />
            <div ref={menuPanel} id="app-mobile-menu" className="app-menu-panel">
              <div className="app-menu-inner">
                <AppNav items={navItems} isAdminRoute={isAdminRoute} onNavigate={() => setMobileOpen(false)} mobile />
                {!isAdminRoute ? <div className="app-menu-actions"><ReportIssueButton /></div> : null}
              </div>
            </div>
          </> : null}
        </header>
        {!isAdminRoute ? <BottomNav items={navItems} menuOpen={mobileOpen} /> : null}
      </> : null}
      <div className={showChrome && !isAdminRoute ? "app-main-with-bottom-nav" : ""} aria-hidden={mobileOpen || undefined} inert={mobileOpen ? "" : undefined}>
      <Suspense fallback={<div className="mx-auto max-w-3xl p-6" role="status">Loading page...</div>}>
      <MonitoredRoutes>
        <Route path="/" element={<RequireAuth><StudentHome /></RequireAuth>} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/change-password" element={<RequireAuth passwordChangeOnly><ChangePasswordPage /></RequireAuth>} />
        <Route path="/lessons/:lessonId" element={<RequireAuth><LessonPage /></RequireAuth>} />
        <Route path="/learning-path" element={<RequireAuth><TrainingDashboardPage /></RequireAuth>} />
        {V2_CURRICULUM_ENABLED ? <>
          <Route path="/learning-v2" element={<RequireAuth><V2LearningPage /></RequireAuth>} />
          <Route path="/learning-v2/modules/:moduleKey" element={<RequireAuth><V2ModulePage /></RequireAuth>} />
          <Route path="/learning-v2/modules/:moduleKey/lessons/:lessonKey" element={<RequireAuth><V2LessonPage /></RequireAuth>} />
          <Route path="/learning-v2/modules/:moduleKey/interactions/:interactionKey" element={<RequireAuth><V2InteractionPage /></RequireAuth>} />
          <Route path="/learning-v2/modules/:moduleKey/assessments/:assessmentKey" element={<RequireAuth><V2AssessmentPage /></RequireAuth>} />
          <Route path="/learning-v2/modules/:moduleKey/explain/:promptKey" element={<RequireAuth><V2ExplainPage /></RequireAuth>} />
          <Route path="/learning-v2/modules/:moduleKey/practical/:assessmentKey" element={<RequireAuth><V2PracticalRedirect /></RequireAuth>} />
          <Route path="/learning-v2/modules/:moduleKey/service-desk/:assessmentKey" element={<RequireAuth><V2ServiceDeskRedirect /></RequireAuth>} />
        </> : null}
        <Route path="/training" element={<Navigate to="/learning-path" replace />} />
        <Route path="/training/week/:weekId" element={<RequireAuth><TrainingWeekPage /></RequireAuth>} />
        <Route path="/training/module/:moduleId" element={<RequireAuth><TrainingWeekPage /></RequireAuth>} />
        <Route path="/training/content" element={<RequireAuth><StudyTrackerPage /></RequireAuth>} />
        <Route path="/skills" element={<RequireAuth><TrainingProgressPage /></RequireAuth>} />
        <Route path="/progress" element={<Navigate to="/skills" replace />} />
        <Route path="/quizzes" element={<RequireAuth><QuizzesPage /></RequireAuth>} />
        <Route path="/study-tracker" element={<Navigate to="/training/content" replace />} />
        <Route path="/quizzes/:quizId" element={<RequireAuth><QuizPage /></RequireAuth>} />
        <Route path="/quizzes/:quizId/review" element={<RequireAuth><QuizReviewPage /></RequireAuth>} />
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
        <Route path="/admin/service-desk-review" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><AdminServiceDeskReviewPage /></AdminAccessGate>} />
        <Route path="/admin/review" element={<Navigate to="/admin/service-desk-review" replace />} />
        <Route path="/admin/students" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><AdminStudentsPage /></AdminAccessGate>} />
        {V2_CURRICULUM_ENABLED ? <>
          <Route path="/admin/v2-progress" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><V2MentorProgressPage /></AdminAccessGate>} />
          <Route path="/admin/v2-progress/students/:studentId" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><V2MentorStudentPage /></AdminAccessGate>} />
          <Route path="/admin/v2-grading/:pendingGradeId" element={<AdminAccessGate onAuthenticationChange={setAdminAuthenticated}><V2MentorGradePage /></AdminAccessGate>} />
        </> : null}
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
        <Route path="*" element={<NotFoundPage />} />
      </MonitoredRoutes>
      </Suspense>
      </div>
    </div>
  );
}
