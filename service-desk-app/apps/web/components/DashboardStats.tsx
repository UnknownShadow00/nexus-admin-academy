'use client';

import { IconChartBar, IconProgress, IconSparkles } from '@tabler/icons-react';
import { Card } from '@service-desk/ui';

import { useAnalyticsSummary, useAttemptScore } from './TicketSessionProvider';

export function DashboardStats() {
  const { pointsTotal } = useAttemptScore();
  const analytics = useAnalyticsSummary();
  const stats = [
    {
      icon: IconSparkles,
      label: 'Practice points',
      value: analytics.isHydrated ? pointsTotal.toLocaleString() : '…',
    },
    {
      icon: IconProgress,
      label: 'Current rank',
      value: analytics.isHydrated ? analytics.rank.currentTier : '…',
    },
    {
      icon: IconChartBar,
      label: 'Accuracy',
      value: analytics.isHydrated
        ? `${analytics.accuracyPercent.toFixed(1)}%`
        : '…',
    },
  ];

  return (
    <section
      aria-label="Training progress"
      className="mx-auto grid w-full max-w-6xl gap-3 sm:grid-cols-3"
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
