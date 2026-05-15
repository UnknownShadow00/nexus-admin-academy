import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getCurrentStudent } from "../hooks/useAuth";
import TicketSubmit from "../components/TicketSubmit";
import Spinner from "../components/Spinner";
import { DifficultyBadge } from "../components/ui/Badge";
import PageHeader from "../components/ui/PageHeader";
import { getTicket } from "../services/api";

export default function TicketPage() {
  const { ticketId } = useParams();
  const studentId = getCurrentStudent()?.id;
  const [ticket, setTicket] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    localStorage.setItem(`ticket_${ticketId}_started`, String(Date.now()));
    let cancelled = false;

    getTicket(ticketId, { suppressToast: true })
      .then((res) => {
        if (!cancelled) setTicket(res.data);
      })
      .catch((err) => {
        if (!cancelled) setError(err?.userMessage || "Unable to load ticket.");
      });

    return () => {
      cancelled = true;
    };
  }, [ticketId]);

  if (!ticket && !error) {
    return <main className="mx-auto max-w-4xl p-6"><Spinner text="Loading ticket..." /></main>;
  }

  if (error) {
    return <main className="mx-auto max-w-4xl p-6 text-sm text-slate-500 dark:text-slate-300">{error}</main>;
  }

  const checkpoints = ticket.required_checkpoints?.checkpoints || [];
  const anchors = ticket.scoring_anchors || {};
  const anchorEntries = Object.entries(anchors).sort(([a], [b]) => Number(a) - Number(b));

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <PageHeader title={ticket.title} />
      <div className="grid gap-6 lg:grid-cols-2">
        <article className="space-y-4 h-fit">
          <div className="panel dark:border-slate-700 dark:bg-slate-900">
            <p className="text-sm text-slate-600 dark:text-slate-300">{ticket.description}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <DifficultyBadge level={ticket.difficulty} />
              {ticket.category && (
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
                  {ticket.category}
                </span>
              )}
            </div>
          </div>

          {checkpoints.length > 0 && (
            <div className="panel dark:border-slate-700 dark:bg-slate-900">
              <h3 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Required Checkpoints</h3>
              <ol className="space-y-2">
                {checkpoints.map((cp) => (
                  <li key={cp.id} className="flex items-start gap-2 text-sm">
                    <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                      {cp.id}
                    </span>
                    <span className="text-slate-700 dark:text-slate-300">{cp.step}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {anchorEntries.length > 0 && (
            <div className="panel dark:border-slate-700 dark:bg-slate-900">
              <h3 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Scoring Guide</h3>
              <div className="space-y-2">
                {anchorEntries.map(([score, desc]) => (
                  <div key={score} className="flex items-start gap-2 text-sm">
                    <span className="shrink-0 font-bold text-blue-600 dark:text-blue-400">{score}/10</span>
                    <span className="text-slate-600 dark:text-slate-300">{desc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </article>
        <TicketSubmit ticket={ticket} studentId={studentId} />
      </div>
    </main>
  );
}
