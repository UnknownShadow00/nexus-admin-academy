'use client';

import { TicketCategory } from '@service-desk/shared';
import { IconHistory, IconSearch } from '@tabler/icons-react';
import { Badge, Input, Modal, PriorityBadge, Select } from '@service-desk/ui';
import { useMemo, useState } from 'react';

import { usePastTickets } from './TicketSessionProvider';

interface PastTicketsModalProps {
  onOpenChange: (open: boolean) => void;
  open: boolean;
}

type ResolutionFilter = 'all' | 'resolved' | 'not-resolved';

function formatClosedDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function PastTicketsModal({
  onOpenChange,
  open,
}: PastTicketsModalProps) {
  const { isHydrated, pastTickets } = usePastTickets();
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<'all' | TicketCategory>('all');
  const [resolution, setResolution] = useState<ResolutionFilter>('all');
  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return pastTickets.filter((ticket) => {
      const matchesQuery =
        normalizedQuery.length === 0 ||
        ticket.id.toLowerCase().includes(normalizedQuery) ||
        ticket.title.toLowerCase().includes(normalizedQuery);
      const matchesCategory =
        category === 'all' || ticket.category === category;
      const matchesResolution =
        resolution === 'all' ||
        (resolution === 'resolved' ? ticket.resolved : !ticket.resolved);
      return matchesQuery && matchesCategory && matchesResolution;
    });
  }, [category, pastTickets, query, resolution]);

  return (
    <Modal
      className="max-w-4xl"
      closeLabel="Close past tickets"
      description="Read-only history from your current simulation attempt"
      onOpenChange={onOpenChange}
      open={open}
      title="Past Tickets"
    >
      {!isHydrated ? (
        <p className="py-8 text-center text-sm text-zinc-400">
          Loading your saved ticket history…
        </p>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_11rem_11rem]">
            <label className="relative block">
              <span className="sr-only">Search past tickets</span>
              <IconSearch
                aria-hidden="true"
                className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-zinc-500"
              />
              <Input
                className="pl-9"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search ID or title"
                value={query}
              />
            </label>
            <label>
              <span className="sr-only">Filter by category</span>
              <Select
                onChange={(event) =>
                  setCategory(event.target.value as 'all' | TicketCategory)
                }
                value={category}
              >
                <option value="all">All categories</option>
                {Object.values(TicketCategory).map((value) => (
                  <option key={value} value={value}>
                    {value.charAt(0).toUpperCase() + value.slice(1)}
                  </option>
                ))}
              </Select>
            </label>
            <label>
              <span className="sr-only">Filter by resolution</span>
              <Select
                onChange={(event) =>
                  setResolution(event.target.value as ResolutionFilter)
                }
                value={resolution}
              >
                <option value="all">All outcomes</option>
                <option value="resolved">Resolved</option>
                <option value="not-resolved">Not resolved</option>
              </Select>
            </label>
          </div>

          {pastTickets.length === 0 ? (
            <div className="py-12 text-center">
              <IconHistory
                aria-hidden="true"
                className="mx-auto h-9 w-9 text-zinc-600"
              />
              <p className="mt-3 font-semibold text-zinc-200">
                No past tickets yet
              </p>
              <p className="mt-1 text-sm text-zinc-500">
                Closed and resolved ticket grades will appear here.
              </p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-10 text-center text-sm text-zinc-500">
              No past tickets match these filters.
            </div>
          ) : (
            <ul className="mt-4 space-y-3">
              {filtered.map((ticket) => (
                <li
                  className="rounded-md border border-zinc-800 bg-zinc-950/70 p-4"
                  key={ticket.id}
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-bold text-sky-400">
                          {ticket.id}
                        </span>
                        <Badge>{ticket.category}</Badge>
                        <PriorityBadge pill priority={ticket.priority} />
                      </div>
                      <h3 className="mt-2 font-semibold text-zinc-100">
                        {ticket.title}
                      </h3>
                      <p className="mt-2 text-xs text-zinc-500">
                        Closed {formatClosedDate(ticket.closedAt)}
                      </p>
                    </div>
                    <div className="shrink-0 text-left sm:text-right">
                      <Badge variant={ticket.resolved ? 'success' : 'amber'}>
                        {ticket.resolved ? 'Resolved' : 'Not resolved'}
                      </Badge>
                      <p className="mt-2 font-display text-sm font-bold tabular-nums text-zinc-100">
                        {ticket.pointsAwarded} / {ticket.pointsPossible} pts
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </Modal>
  );
}
