import { TICKET_FIXTURES, getFixtureTicket } from '@service-desk/shared';
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { TicketWorkspace } from '../../../../components/TicketWorkspace';

interface TicketPageProps {
  params: Promise<{ ticketId: string }>;
}

export function generateStaticParams() {
  return TICKET_FIXTURES.map((ticket) => ({ ticketId: ticket.id }));
}

export async function generateMetadata({
  params,
}: TicketPageProps): Promise<Metadata> {
  const { ticketId } = await params;
  const ticket = getFixtureTicket(ticketId);

  return {
    title: ticket
      ? `${ticket.id}: ${ticket.title} | Nexus Service Desk`
      : 'Ticket not found',
  };
}

export default async function TicketPage({ params }: TicketPageProps) {
  const { ticketId } = await params;

  if (!getFixtureTicket(ticketId)) {
    notFound();
  }

  return <TicketWorkspace ticketId={ticketId} />;
}
