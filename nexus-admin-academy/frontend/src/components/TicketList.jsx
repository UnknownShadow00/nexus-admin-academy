import { Link } from "react-router-dom";

export default function TicketList({ tickets }) {
  return (
    <section className="panel">
      <h2 className="text-xl font-semibold">Tickets</h2>
      <div className="mt-3 space-y-2">
        {tickets?.map((t) => (
          <Link key={t.id} to={`/tickets/${t.id}`} className="block rounded border p-3 hover:bg-slate-50">
            <div className="font-medium">{t.title}</div>
            <div className="text-sm text-slate-600">Difficulty {t.difficulty}</div>
          </Link>
        ))}
      </div>
    </section>
  );
}
