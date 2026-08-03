'use client';

import {
  filterTickets,
  isOpenTicket,
  type TicketFilters,
} from '@service-desk/shared';
import {
  IconClipboardList,
  IconFilterOff,
  IconTicket,
  IconUser,
} from '@tabler/icons-react';
import { Button, Card } from '@service-desk/ui';
import { useMemo, useState } from 'react';

import { TicketQueueFilters } from './TicketQueueFilters';
import { TicketQueueSection } from './TicketQueueSection';
import { useTicketSession } from './TicketSessionProvider';

const EMPTY_FILTERS: TicketFilters = {
  priority: 'all',
  query: '',
  status: 'all',
};

export function TicketQueue() {
  const { tickets } = useTicketSession();
  const [filters, setFilters] = useState<TicketFilters>(EMPTY_FILTERS);
  const filteredTickets = useMemo(
    () => filterTickets(tickets, filters),
    [filters, tickets],
  );
  const assignedTickets = filteredTickets.filter(
    (ticket) => ticket.assignedTo === 'you' && isOpenTicket(ticket),
  );
  const openIncidents = filteredTickets.filter(
    (ticket) => ticket.assignedTo === null && isOpenTicket(ticket),
  );
  const visibleCount = assignedTickets.length + openIncidents.length;
  const allOpenCount = tickets.filter(isOpenTicket).length;

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 md:space-y-6">
      <header className="flex flex-col gap-2 border-b border-zinc-800 pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-label text-xs font-extrabold uppercase tracking-widest text-sky-400">
            Support operations
          </p>
          <h1 className="mt-1 font-display text-2xl font-bold text-zinc-100 sm:text-3xl">
            Ticket Queue
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-zinc-400">
            Continue your active incident or pick up an open request from the
            shared queue.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-bold uppercase text-zinc-500">
          <IconTicket aria-hidden="true" className="h-4 w-4 text-sky-400" />
          {allOpenCount} active incidents
        </div>
      </header>

      <TicketQueueFilters filters={filters} onChange={setFilters} />

      {assignedTickets.length > 0 ? (
        <TicketQueueSection
          icon={IconUser}
          label="Assigned to you"
          meta={`${assignedTickets.length} active`}
          tickets={assignedTickets}
        />
      ) : null}

      {openIncidents.length > 0 ? (
        <section aria-labelledby="open-incidents-title">
          <div className="mb-3 flex items-center gap-2">
            <h2
              className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-zinc-500"
              id="open-incidents-title"
            >
              <IconClipboardList
                aria-hidden="true"
                className="h-4 w-4 text-sky-400"
              />
              Open incidents
            </h2>
            <span className="ml-auto text-xs font-semibold text-zinc-500">
              Select an incident to open its workspace
            </span>
          </div>
          <TicketQueueSection
            icon={IconClipboardList}
            label="Incidents"
            meta={`${openIncidents.length} open`}
            tickets={openIncidents}
          />
        </section>
      ) : null}

      {visibleCount === 0 ? (
        <Card className="flex min-h-56 flex-col items-center justify-center px-5 py-10 text-center">
          <IconFilterOff aria-hidden="true" className="h-9 w-9 text-zinc-600" />
          <h2 className="mt-4 text-base font-bold text-zinc-100">
            No incidents match this view
          </h2>
          <p className="mt-2 max-w-md text-sm text-zinc-400">
            Try a broader search or clear the filters to bring the active queue
            back into view.
          </p>
          <Button
            className="mt-5"
            onClick={() => setFilters(EMPTY_FILTERS)}
            variant="soft"
          >
            Clear filters
          </Button>
        </Card>
      ) : null}
    </div>
  );
}
