import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getCurrentStudent } from "../hooks/useAuth";
import TicketSubmit from "../components/TicketSubmit";
import Spinner from "../components/Spinner";
import { DifficultyBadge } from "../components/ui/Badge";
import PageHeader from "../components/ui/PageHeader";
import { getTicket, revealTicketHint } from "../services/api";

export default function TicketPage() {
  const { ticketId } = useParams();
  const studentId = getCurrentStudent()?.id;
  const [ticket, setTicket] = useState(null);
  const [error, setError] = useState("");
  const [hints, setHints] = useState({ revealed: [], used: 0, total: 0, nextCost: null });
  const [hintBusy, setHintBusy] = useState(false);

  const HINT_COSTS = [5, 10, 20, 35]; // % XP penalty per ladder step (TB-04)

  useEffect(() => {
    localStorage.setItem(`ticket_${ticketId}_started`, String(Date.now()));
    let cancelled = false;

    getTicket(ticketId, { suppressToast: true })
      .then((res) => {
        if (!cancelled) {
          setTicket(res.data);
          setHints({
            revealed: res.data.hints_revealed || [],
            used: res.data.hints_used || 0,
            total: res.data.hints_total || 0,
            nextCost: (res.data.hints_used || 0) < (res.data.hints_total || 0)
              ? HINT_COSTS[res.data.hints_used || 0]
              : null,
          });
        }
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

          {(ticket.grading_rubric || []).length > 0 && (
            <div className="panel dark:border-slate-700 dark:bg-slate-900">
              <h3 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">Graded On (2 points each)</h3>
              <div className="flex flex-wrap gap-2">
                {ticket.grading_rubric.map((anchor) => (
                  <span key={anchor} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                    {anchor.replaceAll("_", " ")}
                  </span>
                ))}
              </div>
            </div>
          )}

          {hints.total > 0 && (
            <div className="panel dark:border-slate-700 dark:bg-slate-900">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                  Hints ({hints.used}/{hints.total} used)
                </h3>
                {hints.nextCost != null ? (
                  <button
                    type="button"
                    disabled={hintBusy}
                    onClick={async () => {
                      setHintBusy(true);
                      try {
                        const res = await revealTicketHint(ticket.id, { suppressToast: true });
                        const d = res?.data || {};
                        setHints({
                          revealed: d.hints_revealed || [],
                          used: d.hints_used || 0,
                          total: d.hints_total || hints.total,
                          nextCost: d.next_hint_xp_penalty_percent ?? null,
                        });
                      } catch {
                        /* toast suppressed; button re-enables */
                      } finally {
                        setHintBusy(false);
                      }
                    }}
                    className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800 hover:bg-amber-100 disabled:opacity-50 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-300"
                  >
                    {hintBusy ? "Revealing..." : `Reveal hint (costs ${hints.used === 0 ? HINT_COSTS[0] : hints.nextCost}% XP)`}
                  </button>
                ) : (
                  <span className="text-xs text-slate-400">All hints revealed</span>
                )}
              </div>
              {hints.revealed.length > 0 ? (
                <ol className="space-y-2">
                  {hints.revealed.map((hint, i) => (
                    <li key={i} className="rounded-lg border border-amber-200 bg-amber-50/60 p-2.5 text-sm text-slate-700 dark:border-amber-900 dark:bg-amber-950/30 dark:text-slate-300">
                      <span className="mr-2 font-semibold text-amber-700 dark:text-amber-400">Hint {i + 1}.</span>
                      {hint}
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Try it on your own first — hints reduce the XP this ticket awards (−5/−10/−20/−35%, you always keep at least 40%).
                </p>
              )}
            </div>
          )}
        </article>
        <TicketSubmit ticket={ticket} studentId={studentId} />
      </div>
    </main>
  );
}
