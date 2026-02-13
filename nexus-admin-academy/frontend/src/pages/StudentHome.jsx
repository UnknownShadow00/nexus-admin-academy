import { useEffect, useState } from "react";
import Dashboard from "../components/Dashboard";
import Leaderboard from "../components/Leaderboard";
import QuizList from "../components/QuizList";
import TicketList from "../components/TicketList";
import { getDashboard, getLeaderboard, getQuizzes, getTickets } from "../services/api";

export default function StudentHome() {
  const studentId = 1;
  const [dashboard, setDashboard] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [quizzes, setQuizzes] = useState([]);
  const [week, setWeek] = useState(1);

  useEffect(() => {
    getDashboard(studentId).then((res) => setDashboard(res.data));
    getLeaderboard().then((res) => setLeaderboard(res.data));
  }, []);

  useEffect(() => {
    getTickets(week).then((res) => setTickets(res.data.tickets));
    getQuizzes(week).then((res) => setQuizzes(res.data.quizzes));
  }, [week]);

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <section className="rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 p-6 text-white shadow-md">
        <h1 className="text-3xl font-bold">Welcome back, {dashboard?.student?.name || "Student"}</h1>
        <p className="mt-2 text-sm text-blue-100">Build real-world IT admin confidence with tickets, quizzes, and XP progression.</p>
      </section>

      <div className="panel flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <label className="text-sm font-semibold text-slate-700">Filter by week</label>
        <input
          className="input-field max-w-24"
          type="number"
          min={1}
          value={week}
          onChange={(e) => setWeek(Number(e.target.value || 1))}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Dashboard dashboard={dashboard} />
          <TicketList tickets={tickets} />
        </div>
        <div className="space-y-4">
          <QuizList quizzes={quizzes} />
          <Leaderboard data={leaderboard} currentStudentId={studentId} />
        </div>
      </div>
    </main>
  );
}
