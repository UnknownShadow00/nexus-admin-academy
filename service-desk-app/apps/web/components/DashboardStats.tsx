'use client';

import { TicketStatus } from '@service-desk/shared';
import {
  IconBriefcase,
  IconChecks,
  IconPlayerPlay,
  IconRefresh,
} from '@tabler/icons-react';
import { Card } from '@service-desk/ui';

import { useTicketSession } from './TicketSessionProvider';

export function DashboardStats() {
  const { progression, tickets } = useTicketSession();
  const fallbackCompleted = tickets.filter(
    (ticket) => ticket.status === TicketStatus.Resolved,
  ).length;
  const stats = [
    {
      icon: IconBriefcase,
      label: 'Available',
      value:
        progression?.counts.available ?? tickets.length - fallbackCompleted,
    },
    {
      icon: IconPlayerPlay,
      label: 'In progress',
      value: progression?.counts.in_progress ?? 0,
    },
    {
      icon: IconChecks,
      label: 'Completed',
      value: progression?.counts.completed ?? fallbackCompleted,
    },
    {
      icon: IconRefresh,
      label: 'Practice',
      value: progression?.counts.practice ?? fallbackCompleted,
    },
  ];

  return (
    <section
      aria-label="Training progress"
      className="mx-auto grid w-full max-w-6xl grid-cols-2 gap-3 lg:grid-cols-4"
    >
      {stats.map(({ icon: Icon, label, value }) => (
        <Card className="flex items-center gap-3 p-4" key={label}>
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-sky-400/30 bg-sky-400/10 text-sky-400">
            <Icon aria-hidden="true" className="h-5 w-5" />
          </span>
          <span>
            <span className="block font-display text-lg font-bold text-zinc-100">
              {value}
            </span>
            <span className="block text-xs font-bold uppercase tracking-wide text-zinc-500">
              {label}
            </span>
          </span>
        </Card>
      ))}
    </section>
  );
}
