'use client';

import {
  Priority,
  TicketStatus,
  type TicketFilters,
} from '@service-desk/shared';
import { Input, Select } from '@service-desk/ui';
import { IconAdjustments, IconSearch } from '@tabler/icons-react';

import { TICKET_STATUS_LABELS } from './ticket-labels';

interface TicketQueueFiltersProps {
  filters: TicketFilters;
  onChange: (filters: TicketFilters) => void;
}

export function TicketQueueFilters({
  filters,
  onChange,
}: TicketQueueFiltersProps) {
  return (
    <section
      aria-label="Filter ticket queue"
      className="grid gap-3 rounded-md border border-zinc-800 bg-zinc-900 p-3 sm:grid-cols-[minmax(0,1fr)_11rem_11rem] sm:p-4"
    >
      <label className="relative min-w-0">
        <span className="sr-only">Search tickets</span>
        <IconSearch
          aria-hidden="true"
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500"
        />
        <Input
          className="pl-9"
          onChange={(event) =>
            onChange({ ...filters, query: event.target.value })
          }
          placeholder="Search ID, title, or requester"
          type="search"
          value={filters.query}
        />
      </label>
      <label>
        <span className="sr-only">Filter by priority</span>
        <Select
          aria-label="Filter by priority"
          onChange={(event) =>
            onChange({
              ...filters,
              priority: event.target.value as Priority | 'all',
            })
          }
          value={filters.priority}
        >
          <option value="all">All priorities</option>
          {Object.values(Priority).map((priority) => (
            <option key={priority} value={priority}>
              {priority[0]?.toUpperCase()}
              {priority.slice(1)}
            </option>
          ))}
        </Select>
      </label>
      <label className="relative">
        <span className="sr-only">Filter by status</span>
        <IconAdjustments
          aria-hidden="true"
          className="pointer-events-none absolute right-8 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600"
        />
        <Select
          aria-label="Filter by status"
          onChange={(event) =>
            onChange({
              ...filters,
              status: event.target.value as TicketStatus | 'all',
            })
          }
          value={filters.status}
        >
          <option value="all">All statuses</option>
          {Object.values(TicketStatus).map((status) => (
            <option key={status} value={status}>
              {TICKET_STATUS_LABELS[status]}
            </option>
          ))}
        </Select>
      </label>
    </section>
  );
}
