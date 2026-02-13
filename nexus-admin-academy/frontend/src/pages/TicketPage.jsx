import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import TicketSubmit from "../components/TicketSubmit";
import { getTicket } from "../services/api";

export default function TicketPage() {
  const { ticketId } = useParams();
  const [ticket, setTicket] = useState(null);

  useEffect(() => {
    getTicket(ticketId).then((res) => setTicket(res.data));
  }, [ticketId]);

  if (!ticket) return <main className="mx-auto max-w-7xl p-6"><section className="panel text-sm text-slate-500">Loading ticket...</section></main>;

  return (
    <main className="mx-auto max-w-7xl p-6">
      <TicketSubmit ticket={ticket} studentId={1} />
    </main>
  );
}
