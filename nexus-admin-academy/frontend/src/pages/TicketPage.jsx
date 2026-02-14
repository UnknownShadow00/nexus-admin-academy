import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import TicketSubmit from "../components/TicketSubmit";
import Spinner from "../components/Spinner";
import { getTicket } from "../services/api";
import { getSelectedProfile } from "../services/profile";

export default function TicketPage() {
  const { ticketId } = useParams();
  const studentId = getSelectedProfile()?.id || 1;
  const [ticket, setTicket] = useState(null);

  useEffect(() => {
    localStorage.setItem(`ticket_${ticketId}_started`, String(Date.now()));
    getTicket(ticketId).then((res) => setTicket(res.data));
  }, [ticketId]);

  if (!ticket) {
    return <main className="mx-auto max-w-4xl p-6"><Spinner text="Loading ticket..." /></main>;
  }

  return (
    <main className="mx-auto max-w-7xl p-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <article className="panel h-fit dark:border-slate-700 dark:bg-slate-900">
          <h1 className="text-2xl font-bold">{ticket.title}</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{ticket.description}</p>
          <div className="mt-4 flex flex-wrap gap-2 text-xs">
            <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
              Difficulty {ticket.difficulty}
            </span>
            <span className="rounded-full bg-blue-100 px-2 py-1 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
              Domain {ticket.domain_id}
            </span>
          </div>
        </article>
        <TicketSubmit ticket={ticket} studentId={studentId} />
      </div>
    </main>
  );
}
