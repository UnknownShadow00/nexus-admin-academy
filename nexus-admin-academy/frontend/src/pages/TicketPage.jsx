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

  if (!ticket) return <main className="mx-auto max-w-4xl p-6">Loading ticket...</main>;

  return (
    <main className="mx-auto max-w-4xl p-6">
      <TicketSubmit ticket={ticket} studentId={1} />
    </main>
  );
}
