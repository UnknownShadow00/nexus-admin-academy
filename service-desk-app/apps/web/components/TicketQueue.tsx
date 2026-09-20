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
      <header className="flex flex-col gap-2 border-b border-border pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-label text-xs font-extrabold uppercase tracking-widest text-accent">
            Support operations
          </p>
          <h1 className="mt-1 font-display text-2xl font-bold text-text sm:text-3xl">
            My Service Desk
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-text-muted">
            Start with the cases assigned to your shift. Assessment passes
            demonstrate mastery; passed cases remain replayable without
            curriculum stakes.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-bold uppercase text-text-muted">
          <IconTicket aria-hidden="true" className="h-4 w-4 text-accent" />
          {allOpenCount} active cases
        </div>
      </header>

      <TicketQueueFilters filters={filters} onChange={setFilters} />

      {progression && progression.current_pack === null ? (
        <Card className="border-accent/20 bg-accent/5 p-5 sm:p-6">
          <p className="text-xs font-extrabold uppercase tracking-wide text-accent">
            Your first shift is almost ready
          </p>
          <h2 className="mt-2 font-display text-xl font-bold text-text">
            {progression.next_pack?.reason ||
              'Complete your first A+ troubleshooting topics to unlock tickets.'}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-text-muted">
            Finish the current lesson and its low-stakes quiz. A related
            beginner case will appear here when that foundation is complete.
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

      {visibleCount > 0 ? (
        <section aria-labelledby="practice-title">
        <div className="mb-3 flex items-center gap-2">
          <h2
            className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-text-muted"
            id="practice-title"
          >
            <IconClipboardList
              aria-hidden="true"
              className="h-4 w-4 text-accent"
            />
            Practice
          </h2>
          <span className="ml-auto text-right text-xs font-semibold text-text-muted">
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
          <Card className="border-dashed border-border px-4 py-4 text-sm text-text-muted">
            No mastered cases yet. Pass an assessment to add it here for
            independent replay.
          </Card>
        )}
        </section>
      ) : null}

      {earlierTickets.length > 0 ? (
        <details className="group rounded-md border border-border bg-surface-raised/40">
          <summary className="sd-focus-ring flex cursor-pointer list-none items-center gap-2 rounded-md px-4 py-3 text-sm font-bold text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus">
            <IconHistory aria-hidden="true" className="h-4 w-4 text-text-muted" />
            More unlocked cases
            <span className="ml-auto text-xs font-semibold text-text-muted">
              {earlierTickets.length} unfinished
            </span>
          </summary>
          <div className="border-t border-border p-3 sm:p-4">
            <p className="mb-3 text-sm text-text-muted">
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
        <Card className="flex items-start gap-3 border-dashed border-border p-4 sm:p-5">
          <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-surface text-text-muted">
            <IconLock aria-hidden="true" className="h-4 w-4" />
          </span>
          <div>
            <p className="text-xs font-extrabold uppercase tracking-wide text-text-muted">
              Next case pack
            </p>
            <h2 className="mt-1 font-display text-base font-bold text-text">
              {progression.next_pack.name}
            </h2>
            <div className="mt-3 space-y-2 text-sm text-text-muted">
              <p
                className={
                  progression.next_pack.requirements.week.met
                    ? 'text-success'
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
                      ? 'text-success'
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

      {visibleCount === 0 &&
      tickets.length === 0 &&
      progression?.current_pack ? (
        <Card className="flex min-h-56 flex-col items-center justify-center px-5 py-10 text-center">
          <IconLock aria-hidden="true" className="h-9 w-9 text-accent" />
          <h2 className="mt-4 text-base font-bold text-text">
            Complete your first A+ troubleshooting topics to unlock tickets.
          </h2>
          <p className="mt-2 max-w-md text-sm text-text-muted">
            Keep going from Today. Tickets appear here only after you have
            learned the related foundation.
          </p>
        </Card>
      ) : null}

      {visibleCount === 0 && tickets.length > 0 ? (
        <Card className="flex min-h-56 flex-col items-center justify-center px-5 py-10 text-center">
          <IconFilterOff aria-hidden="true" className="h-9 w-9 text-text-muted" />
          <h2 className="mt-4 text-base font-bold text-text">No tickets match these filters</h2>
          <p className="mt-2 max-w-md text-sm text-text-muted">
            Clear the filters to return to your unlocked cases.
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
