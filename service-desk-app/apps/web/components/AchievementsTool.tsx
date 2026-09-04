'use client';

import { IconLock, IconRosetteDiscountCheck } from '@tabler/icons-react';
import { Badge, Card, CardHeader } from '@service-desk/ui';

import { useAchievements, useAnalyticsSummary } from './TicketSessionProvider';

function formatEarnedDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
  }).format(new Date(value));
}

export function AchievementsTool() {
  const { achievements, isHydrated } = useAchievements();
  const analytics = useAnalyticsSummary();

  if (!isHydrated || !analytics.isHydrated) {
    return (
      <Card className="mx-auto max-w-6xl p-8 text-center text-sm text-text-muted">
        Loading your saved achievements…
      </Card>
    );
  }

  const earned = achievements.filter((achievement) => achievement.earned);
  const locked = achievements.filter((achievement) => !achievement.earned);
  const rank = analytics.rank;

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 md:space-y-6">
      <header className="border-b border-border pb-4">
        <p className="font-label text-xs font-extrabold uppercase tracking-widest text-accent">
          Career progression
        </p>
        <h1 className="mt-1 font-display text-2xl font-bold text-text sm:text-3xl">
          Achievements
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-text-muted">
          Milestones are evaluated live from ticket grades, hint usage, and
          recorded ticket-action timing in this attempt.
        </p>
      </header>

      <Card className="border-warning/20 bg-gradient-to-r from-warning/10 to-surface-raised">
        <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-extrabold uppercase tracking-widest text-warning">
              Current rank
            </p>
            <h2 className="mt-2 font-display text-2xl font-bold text-text">
              {rank.currentTier}
            </h2>
            <p className="mt-1 text-sm text-text-muted">
              {analytics.pointsTotal.toLocaleString()} practice points
            </p>
          </div>
          <div className="rounded-md border border-border bg-surface/70 px-4 py-3 text-sm">
            {rank.nextTier ? (
              <>
                <span className="block font-bold text-text">
                  Next: {rank.nextTier}
                </span>
                <span className="mt-1 block text-text-muted">
                  {rank.pointsRemaining.toLocaleString()} more points
                </span>
              </>
            ) : (
              <span className="font-bold text-warning">
                Maximum tier reached
              </span>
            )}
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Earned"
          meta={`${earned.length}/${achievements.length}`}
        />
        {earned.length > 0 ? (
          <div className="grid gap-3 p-4 md:grid-cols-2">
            {earned.map((achievement) => (
              <article
                className="flex gap-3 rounded-md border border-success/20 bg-success/5 p-4"
                key={achievement.code}
              >
                <IconRosetteDiscountCheck
                  aria-hidden="true"
                  className="h-6 w-6 shrink-0 text-success"
                />
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-bold text-text">
                      {achievement.name}
                    </h3>
                    <Badge variant="success">Earned</Badge>
                  </div>
                  <p className="mt-1 text-sm text-text-muted">
                    {achievement.description}
                  </p>
                  <p className="mt-2 text-xs font-semibold text-success">
                    Earned{' '}
                    {achievement.earnedAt
                      ? formatEarnedDate(achievement.earnedAt)
                      : ''}
                  </p>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center">
            <IconRosetteDiscountCheck
              aria-hidden="true"
              className="mx-auto h-8 w-8 text-text-muted"
            />
            <p className="mt-3 font-semibold text-text">
              No achievements earned yet
            </p>
            <p className="mt-1 text-sm text-text-muted">
              Resolve your first ticket to begin your collection.
            </p>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="Locked" meta={`${locked.length} remaining`} />
        <div className="grid gap-3 p-4 md:grid-cols-2">
          {locked.map((achievement) => (
            <article
              className="flex gap-3 rounded-md border border-border bg-surface/60 p-4"
              key={achievement.code}
            >
              <IconLock
                aria-hidden="true"
                className="h-5 w-5 shrink-0 text-text-muted"
              />
              <div>
                <h3 className="font-bold text-text">{achievement.name}</h3>
                <p className="mt-1 text-sm text-text-muted">
                  {achievement.description}
                </p>
                {achievement.thresholdType !== 'fast_resolution_seconds' ? (
                  <p className="mt-2 text-xs font-semibold tabular-nums text-text-muted">
                    Current: {achievement.currentValue.toLocaleString()} /{' '}
                    {achievement.threshold.toLocaleString()}
                  </p>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </Card>
    </div>
  );
}
