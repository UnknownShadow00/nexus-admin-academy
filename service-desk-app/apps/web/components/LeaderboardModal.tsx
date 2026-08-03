'use client';

import { LEADERBOARD_FIXTURES, getRankForPoints } from '@service-desk/shared';
import { IconTrophy } from '@tabler/icons-react';
import { Badge, Modal } from '@service-desk/ui';

import { useAnalyticsSummary, useAttemptScore } from './TicketSessionProvider';

interface LeaderboardModalProps {
  onOpenChange: (open: boolean) => void;
  open: boolean;
}

export function LeaderboardModal({
  onOpenChange,
  open,
}: LeaderboardModalProps) {
  const { pointsTotal } = useAttemptScore();
  const { isHydrated } = useAnalyticsSummary();
  const rows = [
    ...LEADERBOARD_FIXTURES.map((row) => ({ ...row, isStudent: false })),
    {
      id: 'current-student',
      name: 'You',
      points: pointsTotal,
      isStudent: true,
    },
  ].sort(
    (left, right) =>
      right.points - left.points ||
      Number(right.isStudent) - Number(left.isStudent),
  );

  return (
    <Modal
      className="max-w-2xl"
      closeLabel="Close leaderboard"
      description="Global practice ranking"
      onOpenChange={onOpenChange}
      open={open}
      title="Leaderboard"
    >
      {!isHydrated ? (
        <p className="py-8 text-center text-sm text-zinc-400">
          Loading your saved score…
        </p>
      ) : (
        <>
          <div className="mb-4 flex items-center justify-between gap-3">
            <Badge variant="sky">Global</Badge>
            <p className="text-xs text-zinc-500">
              Your highlighted row is live. Cohort names are illustrative.
            </p>
          </div>
          <ol className="space-y-2">
            {rows.map((row, index) => {
              const tier = getRankForPoints(row.points).currentTier;
              return (
                <li
                  className={`grid grid-cols-[2.5rem_minmax(0,1fr)_auto] items-center gap-3 rounded-md border px-3 py-3 ${
                    row.isStudent
                      ? 'border-sky-400/40 bg-sky-400/10'
                      : 'border-zinc-800 bg-zinc-950/70'
                  }`}
                  key={row.id}
                >
                  <span
                    className={`font-display text-sm font-bold ${
                      index === 0 ? 'text-amber-400' : 'text-zinc-500'
                    }`}
                  >
                    #{index + 1}
                  </span>
                  <span className="min-w-0">
                    <span
                      className={`block truncate font-semibold ${
                        row.isStudent ? 'text-sky-200' : 'text-zinc-200'
                      }`}
                    >
                      {row.name}
                    </span>
                    <Badge
                      className="mt-1"
                      variant={row.isStudent ? 'sky' : 'default'}
                    >
                      {tier}
                    </Badge>
                  </span>
                  <span className="flex items-center gap-1.5 font-display text-sm font-bold tabular-nums text-zinc-100">
                    <IconTrophy
                      aria-hidden="true"
                      className="h-4 w-4 text-amber-400"
                    />
                    {row.points.toLocaleString()}
                  </span>
                </li>
              );
            })}
          </ol>
        </>
      )}
    </Modal>
  );
}
