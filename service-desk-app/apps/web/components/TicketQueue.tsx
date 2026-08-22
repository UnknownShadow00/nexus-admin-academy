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
  IconHistory,
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
    (ticket) => queueType(ticket.id) === 'assigned',
  );
  const practiceTickets = filteredTickets.filter(
    (ticket) => queueType(ticket.id) === 'practice',
  );
  const earlierTickets = filteredTickets.filter(
    (ticket) => queueType(ticket.id) === 'earlier',
  );
  const visibleCount =
    assignedTickets.length + practiceTickets.length + earlierTickets.length;
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
            Start with the cases assigned to your shift. Assessment passes
            demonstrate mastery; passed cases remain replayable without
            curriculum stakes.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-bold uppercase text-zinc-500">
          <IconTicket aria-hidden="true" className="h-4 w-4 text-sky-400" />
          {allOpenCount} active cases
        </div>
      </header>

      <TicketQueueFilters filters={filters} onChange={setFilters} />

      {progression && progression.current_pack === null ? (
        <Card className="border-sky-400/20 bg-sky-400/5 p-5 sm:p-6">
          <p className="text-xs font-extrabold uppercase tracking-wide text-sky-400">
            Your first shift is almost ready
          </p>
          <h2 className="mt-2 font-display text-xl font-bold text-zinc-100">
            {progression.next_pack?.reason ||
              'Complete Nexus Orientation to begin your first Service Desk shift.'}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-zinc-400">
            Finish the Nexus orientation lesson and pass its checkpoint. Your
            four Starter Support cases will then appear here automatically.
          </p>
        </Card>
      ) : null}

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
            Independent replay · no mastery or XP
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
            No mastered cases yet. Pass an assessment to add it here for
            independent replay.
          </Card>
        )}
      </section>

      {earlierTickets.length > 0 ? (
        <details className="group rounded-md border border-zinc-800 bg-zinc-900/40">
          <summary className="sd-focus-ring flex cursor-pointer list-none items-center gap-2 rounded-md px-4 py-3 text-sm font-bold text-zinc-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400">
            <IconHistory aria-hidden="true" className="h-4 w-4 text-zinc-500" />
            More unlocked cases
            <span className="ml-auto text-xs font-semibold text-zinc-500">
              {earlierTickets.length} unfinished
            </span>
          </summary>
          <div className="border-t border-zinc-800 p-3 sm:p-4">
            <p className="mb-3 text-sm text-zinc-500">
              These unfinished cases remain available, but they are not part of
              your current shift queue.
            </p>
            <TicketQueueSection
              icon={IconHistory}
              label="Unlocked cases outside this shift"
              meta={`${earlierTickets.length} unfinished`}
              tickets={earlierTickets}
              assignmentByTicket={assignmentByTicket}
            />
          </div>
        </details>
      ) : null}

      {progression?.next_pack && progression.current_pack ? (
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
            <div className="mt-3 space-y-2 text-sm text-zinc-400">
              <p
                className={
                  progression.next_pack.requirements.week.met
                    ? 'text-emerald-300'
                    : ''
                }
              >
                {progression.next_pack.requirements.week.met ? '✓' : '○'}{' '}
                {progression.next_pack.requirements.week.label}
              </p>
              {progression.next_pack.requirements.passes ? (
                <p
                  className={
                    progression.next_pack.requirements.passes.met
                      ? 'text-emerald-300'
                      : ''
                  }
                >
                  {progression.next_pack.requirements.passes.met ? '✓' : '○'}{' '}
                  {progression.next_pack.requirements.passes.label} (
                  {progression.next_pack.requirements.passes.completed}/
                  {progression.next_pack.requirements.passes.required})
                </p>
              ) : null}
            </div>
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
