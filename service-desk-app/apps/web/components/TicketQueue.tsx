'use client';

import {
  filterTickets,
  isOpenTicket,
  type TicketFilters,
} from '@service-desk/shared';
import {
  IconClipboardList,
  IconFilterOff,
  IconLock,
  IconRefresh,
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
  const { assignmentByTicket, progression, tickets } = useTicketSession();
  const [filters, setFilters] = useState<TicketFilters>(EMPTY_FILTERS);
  const filteredTickets = useMemo(
    () => filterTickets(tickets, filters),
    [filters, tickets],
  );
  const queueType = (ticketId: string) =>
    assignmentByTicket[ticketId]?.queue_type ?? 'assigned';
  const assignedTickets = filteredTickets.filter(
    (ticket) => queueType(ticket.id) === 'assigned' && isOpenTicket(ticket),
  );
  const practiceTickets = filteredTickets.filter(
    (ticket) => queueType(ticket.id) === 'practice' || !isOpenTicket(ticket),
  );
  const visibleCount = assignedTickets.length + practiceTickets.length;
  const allOpenCount = tickets.filter(isOpenTicket).length;

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 md:space-y-6">
      <header className="flex flex-col gap-2 border-b border-zinc-800 pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-label text-xs font-extrabold uppercase tracking-widest text-sky-400">
            Support operations
          </p>
          <h1 className="mt-1 font-display text-2xl font-bold text-zinc-100 sm:text-3xl">
            My Service Desk
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-zinc-400">
            Start with the cases assigned to your shift. Completed and earlier
            cases stay available for practice.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-bold uppercase text-zinc-500">
          <IconTicket aria-hidden="true" className="h-4 w-4 text-sky-400" />
          {allOpenCount} active cases
        </div>
      </header>

      <TicketQueueFilters filters={filters} onChange={setFilters} />

      {assignedTickets.length > 0 ? (
        <TicketQueueSection
          icon={IconUser}
          label="Assigned"
          meta={`${assignedTickets.length} new or active`}
          tickets={assignedTickets}
          assignmentByTicket={assignmentByTicket}
        />
      ) : null}

      <section aria-labelledby="practice-title">
        <div className="mb-3 flex items-center gap-2">
          <h2
            className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-zinc-500"
            id="practice-title"
          >
            <IconClipboardList
              aria-hidden="true"
              className="h-4 w-4 text-sky-400"
            />
            Practice
          </h2>
          <span className="ml-auto text-right text-xs font-semibold text-zinc-500">
            Replay cases you have completed
          </span>
        </div>
        {practiceTickets.length > 0 ? (
          <TicketQueueSection
            icon={IconRefresh}
            label="Practice cases"
            meta={`${practiceTickets.length} unlocked`}
            tickets={practiceTickets}
            assignmentByTicket={assignmentByTicket}
          />
        ) : (
          <Card className="border-dashed border-zinc-800 px-4 py-4 text-sm text-zinc-500">
            No completed cases yet. Successfully complete an assigned case to
            add it here for replay.
          </Card>
        )}
      </section>

      {progression?.next_pack ? (
        <Card className="flex items-start gap-3 border-dashed border-zinc-700 p-4 sm:p-5">
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-zinc-700 bg-zinc-950 text-zinc-400">
            <IconLock aria-hidden="true" className="h-4 w-4" />
          </span>
          <div>
            <p className="text-xs font-extrabold uppercase tracking-wide text-zinc-500">
              Next case pack
            </p>
            <h2 className="mt-1 font-display text-base font-bold text-zinc-100">
              {progression.next_pack.name}
            </h2>
            <p className="mt-1 text-sm text-zinc-400">
              {progression.next_pack.reason} Continue your Nexus training to
              unlock these cases.
            </p>
          </div>
        </Card>
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
