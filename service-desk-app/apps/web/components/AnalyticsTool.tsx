'use client';

import { RANK_TIERS } from '@service-desk/shared';
import {
  IconActivity,
  IconBulb,
  IconChartBar,
  IconClock,
  IconTarget,
  IconTicket,
} from '@tabler/icons-react';
import { Badge, Card, CardHeader } from '@service-desk/ui';
import type { ReactNode } from 'react';

import { useAnalyticsSummary } from './TicketSessionProvider';

function formatDuration(durationMs: number) {
  if (durationMs <= 0) {
    return '0m';
  }

  const totalSeconds = Math.round(durationMs / 1_000);
  const hours = Math.floor(totalSeconds / 3_600);
  const minutes = Math.floor((totalSeconds % 3_600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

interface StatCardProps {
  icon: ReactNode;
  label: string;
  value: string;
}

function StatCard({ icon, label, value }: StatCardProps) {
  return (
    <Card className="flex items-center gap-3 p-4">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-sky-400/30 bg-sky-400/10 text-sky-400">
        {icon}
      </span>
      <span>
        <span className="block font-display text-xl font-bold tabular-nums text-zinc-100">
          {value}
        </span>
        <span className="block text-xs font-bold uppercase tracking-wide text-zinc-500">
          {label}
        </span>
      </span>
    </Card>
  );
}

interface BreakdownProps {
  items: readonly {
    count: number;
    key: string;
    label: string;
    percentage: number;
  }[];
  title: string;
  total: number;
}

function Breakdown({ items, title, total }: BreakdownProps) {
  return (
    <Card>
      <CardHeader title={title} meta={`${total} resolved`} />
      <div className="space-y-4 p-4">
        {items.map((item) => (
          <div key={item.key}>
            <div className="mb-1.5 flex items-center justify-between gap-3 text-sm">
              <span className="font-semibold text-zinc-200">{item.label}</span>
              <span className="tabular-nums text-zinc-400">
                {item.count} · {item.percentage.toFixed(1)}%
              </span>
            </div>
            <div
              aria-label={`${item.label}: ${item.percentage.toFixed(1)} percent`}
              className="h-2 overflow-hidden rounded-full bg-zinc-800"
              role="progressbar"
              aria-valuemax={100}
              aria-valuemin={0}
              aria-valuenow={item.percentage}
            >
              <div
                className="h-full rounded-full bg-sky-400"
                style={{ width: `${item.percentage}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function AnalyticsTool() {
  const analytics = useAnalyticsSummary();

  if (!analytics.isHydrated) {
    return (
      <Card className="mx-auto max-w-6xl p-8 text-center text-sm text-zinc-400">
        Loading your saved analytics…
      </Card>
    );
  }

  const { currentTier, nextTier, pointsRemaining } = analytics.rank;
  const currentTierDefinition = RANK_TIERS.find(
    (tier) => tier.name === currentTier,
  )!;
  const nextTierDefinition = RANK_TIERS.find((tier) => tier.name === nextTier);
  const tierSpan = nextTierDefinition
    ? nextTierDefinition.points - currentTierDefinition.points
    : 1;
  const tierProgress = nextTierDefinition
    ? Math.min(
        100,
        Math.max(
          0,
          ((analytics.pointsTotal - currentTierDefinition.points) / tierSpan) *
            100,
        ),
      )
    : 100;

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 md:space-y-6">
      <header className="border-b border-zinc-800 pb-4">
        <p className="font-label text-xs font-extrabold uppercase tracking-widest text-sky-400">
          Personal performance
        </p>
        <h1 className="mt-1 font-display text-2xl font-bold text-zinc-100 sm:text-3xl">
          Analytics
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          Track your support performance and identify training opportunities.
          Every metric reflects this browser&apos;s current simulation attempt.
        </p>
      </header>

      {analytics.ticketsAttempted === 0 ? (
        <Card className="border-sky-400/20 bg-sky-400/5 p-4 text-sm text-sky-200">
          Complete a ticket to populate score, accuracy, category, priority, and
          timing analytics. Recorded tool actions will appear immediately.
        </Card>
      ) : null}

      <section
        aria-label="Performance summary"
        className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
      >
        <StatCard
          icon={<IconChartBar aria-hidden="true" className="h-5 w-5" />}
          label="Score"
          value={analytics.pointsTotal.toLocaleString()}
        />
        <StatCard
          icon={<IconTarget aria-hidden="true" className="h-5 w-5" />}
          label="Accuracy"
          value={`${analytics.accuracyPercent.toFixed(1)}%`}
        />
        <StatCard
          icon={<IconTicket aria-hidden="true" className="h-5 w-5" />}
          label="Tickets resolved"
          value={analytics.ticketsResolved.toLocaleString()}
        />
        <StatCard
          icon={<IconActivity aria-hidden="true" className="h-5 w-5" />}
          label="Actions performed"
          value={analytics.actionsPerformed.toLocaleString()}
        />
      </section>

      <Card>
        <CardHeader
          title="Tier Progress"
          meta={
            nextTier
              ? `${pointsRemaining.toLocaleString()} pts to ${nextTier}`
              : 'Maximum tier reached'
          }
        />
        <div className="p-4 sm:p-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <Badge variant="amber">{currentTier}</Badge>
              <p className="mt-2 text-sm text-zinc-400">
                {analytics.pointsTotal.toLocaleString()} total points
              </p>
            </div>
            <span className="text-xs font-semibold uppercase text-zinc-500">
              {tierProgress.toFixed(0)}% through current tier
            </span>
          </div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-zinc-800">
            <div
              className="h-full rounded-full bg-amber-400"
              style={{ width: `${tierProgress}%` }}
            />
          </div>
          <ol className="mt-5 grid gap-2 sm:grid-cols-4 lg:grid-cols-11">
            {RANK_TIERS.map((tier) => {
              const isCurrent = tier.name === currentTier;
              const isReached = analytics.pointsTotal >= tier.points;
              return (
                <li
                  className={`rounded-sm border px-2 py-2 text-center ${
                    isCurrent
                      ? 'border-amber-400 bg-amber-400/10 text-amber-300'
                      : isReached
                        ? 'border-sky-400/30 bg-sky-400/5 text-sky-300'
                        : 'border-zinc-800 bg-zinc-950 text-zinc-500'
                  }`}
                  key={tier.name}
                >
                  <span className="block text-[10px] font-extrabold uppercase">
                    {tier.name}
                  </span>
                  <span className="mt-1 block text-[10px] tabular-nums">
                    {tier.points.toLocaleString()}
                  </span>
                  {isCurrent ? (
                    <span className="mt-1 block text-[9px] font-black uppercase">
                      You
                    </span>
                  ) : null}
                </li>
              );
            })}
          </ol>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Breakdown
          items={analytics.categoryBreakdown}
          title="Category Breakdown"
          total={analytics.ticketsResolved}
        />
        <Breakdown
          items={analytics.priorityDistribution}
          title="Priority Distribution"
          total={analytics.ticketsResolved}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Hint Usage" />
          <div className="grid grid-cols-2 gap-3 p-4">
            <div className="rounded-md border border-zinc-800 bg-zinc-950 p-4">
              <IconBulb
                aria-hidden="true"
                className="mb-3 h-5 w-5 text-amber-400"
              />
              <p className="font-display text-2xl font-bold tabular-nums text-zinc-100">
                {analytics.hintsUsed}
              </p>
              <p className="mt-1 text-xs font-bold uppercase text-zinc-500">
                Hints revealed
              </p>
            </div>
            <div className="rounded-md border border-zinc-800 bg-zinc-950 p-4">
              <IconTarget
                aria-hidden="true"
                className="mb-3 h-5 w-5 text-red-400"
              />
              <p className="font-display text-2xl font-bold tabular-nums text-zinc-100">
                {analytics.hintPenaltyPoints}
              </p>
              <p className="mt-1 text-xs font-bold uppercase text-zinc-500">
                Hint points lost
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Time Spent"
            meta={`${analytics.timeSpentTicketCount} timed tickets`}
          />
          <div className="grid grid-cols-2 gap-3 p-4">
            <div className="rounded-md border border-zinc-800 bg-zinc-950 p-4">
              <IconClock
                aria-hidden="true"
                className="mb-3 h-5 w-5 text-sky-400"
              />
              <p className="font-display text-2xl font-bold tabular-nums text-zinc-100">
                {formatDuration(analytics.timeSpentTotalMs)}
              </p>
              <p className="mt-1 text-xs font-bold uppercase text-zinc-500">
                Total recorded
              </p>
            </div>
            <div className="rounded-md border border-zinc-800 bg-zinc-950 p-4">
              <IconClock
                aria-hidden="true"
                className="mb-3 h-5 w-5 text-emerald-400"
              />
              <p className="font-display text-2xl font-bold tabular-nums text-zinc-100">
                {formatDuration(analytics.timeSpentAverageMs)}
              </p>
              <p className="mt-1 text-xs font-bold uppercase text-zinc-500">
                Average per ticket
              </p>
            </div>
          </div>
          {analytics.timeSpentTicketCount === 0 ? (
            <p className="border-t border-zinc-800 px-4 py-3 text-xs text-zinc-500">
              Timing starts with the first recorded ticket action. Tickets with
              no event timestamps are omitted from the average.
            </p>
          ) : null}
        </Card>
      </div>
    </div>
  );
}
