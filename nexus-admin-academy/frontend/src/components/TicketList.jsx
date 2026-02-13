import { Ticket } from "./icons";
import { Link } from "react-router-dom";

const difficultyStyles = {
  1: "bg-emerald-100 text-emerald-700",
  2: "bg-blue-100 text-blue-700",
  3: "bg-amber-100 text-amber-700",
  4: "bg-orange-100 text-orange-700",
  5: "bg-red-100 text-red-700",
};

export default function TicketList({ tickets }) {
  return (
    <section className="panel">
      <h2 className="mb-3 flex items-center gap-2 text-xl font-bold text-gray-900">
        <Ticket className="h-5 w-5 text-blue-600" /> Tickets
      </h2>
      <div className="grid gap-3 md:grid-cols-2">
        {tickets?.map((ticket) => (
          <Link
            key={ticket.id}
            to={`/tickets/${ticket.id}`}
            className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-blue-50 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <p className="font-semibold text-gray-900">{ticket.title}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              <span className={`rounded-full px-2 py-1 font-semibold ${difficultyStyles[ticket.difficulty] || "bg-slate-100 text-slate-600"}`}>
                Difficulty {ticket.difficulty}
              </span>
              <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-600">Week {ticket.week_number}</span>
              <span className="rounded-full bg-blue-100 px-2 py-1 font-medium text-blue-700">Not Started</span>
            </div>
          </Link>
        ))}
      </div>
      {!tickets?.length && <p className="mt-2 rounded-lg bg-slate-50 p-3 text-sm text-slate-500">No tickets are available for this week.</p>}
    </section>
  );
}
