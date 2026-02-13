import { useEffect, useState } from "react";
import Dashboard from "../components/Dashboard";
import Leaderboard from "../components/Leaderboard";
import TicketList from "../components/TicketList";
import { getDashboard, getLeaderboard, getTickets } from "../services/api";

export default function StudentHome() {
  const studentId = 1;
  const [dashboard, setDashboard] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);
  const [tickets, setTickets] = useState([]);

  useEffect(() => {
    getDashboard(studentId).then((res) => setDashboard(res.data));
    getLeaderboard().then((res) => setLeaderboard(res.data));
    getTickets().then((res) => setTickets(res.data.tickets));
  }, []);

  return (
    <main className="mx-auto grid max-w-6xl gap-4 p-6 md:grid-cols-2">
      <Dashboard dashboard={dashboard} />
      <Leaderboard data={leaderboard} />
      <div className="md:col-span-2">
        <TicketList tickets={tickets} />
      </div>
    </main>
  );
}
