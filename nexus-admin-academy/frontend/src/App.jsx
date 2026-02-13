import { BookOpen, LayoutDashboard, Shield, Ticket } from "./components/icons";
import { Link, Route, Routes, useLocation } from "react-router-dom";
import AdminHome from "./pages/AdminHome";
import QuizPage from "./pages/QuizPage";
import StudentHome from "./pages/StudentHome";
import TicketPage from "./pages/TicketPage";

const navItems = [
  { to: "/", label: "Student Dashboard", Icon: LayoutDashboard },
  { to: "/admin", label: "Admin Dashboard", Icon: Shield },
  { to: "/quizzes/1", label: "Quiz Demo", Icon: BookOpen },
  { to: "/tickets/1", label: "Ticket Demo", Icon: Ticket },
];

export default function App() {
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen bg-slate-50 text-gray-800">
      <aside className="fixed left-0 top-0 hidden h-screen w-60 flex-col border-r border-slate-200 bg-white p-5 shadow-sm lg:flex">
        <h1 className="mb-8 text-xl font-bold text-gray-900">Nexus Admin Academy</h1>
        <nav className="space-y-2">
          {navItems.map(({ to, label, Icon }) => {
            const active = pathname === to || (to !== "/" && pathname.startsWith(to));
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 ${
                  active ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-blue-50 hover:text-blue-700"
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="lg:ml-60">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <div>
              <p className="text-sm text-slate-500">IT Training Cohort</p>
              <h2 className="text-lg font-bold text-gray-900">Hands-on Tickets & Quizzes</h2>
            </div>
            <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700">XP Track Active</div>
          </div>
        </header>

        <div className="page-shell">
          <Routes>
            <Route path="/" element={<StudentHome />} />
            <Route path="/admin" element={<AdminHome />} />
            <Route path="/quizzes/:quizId" element={<QuizPage />} />
            <Route path="/tickets/:ticketId" element={<TicketPage />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}
