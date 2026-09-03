'use client';

import { nextHintRevealCount } from '@service-desk/shared';
import { Button, Card, CardHeader } from '@service-desk/ui';
import { IconBulb, IconChevronRight } from '@tabler/icons-react';
import React, { useEffect, useState } from 'react';

export function HintPanel({
  experienceMode,
  hints,
  onReveal,
  revealedCount: persistedRevealedCount = 0,
}: {
  experienceMode: 'guided' | 'practice' | 'assessment';
  hints: readonly string[];
  onReveal: (step: number) => void;
  revealedCount?: number;
}) {
  const [open, setOpen] = useState(false);
  const [revealedCount, setRevealedCount] = useState(persistedRevealedCount);

  useEffect(() => {
    setRevealedCount((current) => Math.max(current, persistedRevealedCount));
  }, [persistedRevealedCount]);

  if (experienceMode === 'assessment') {
    return (
      <Card>
        <CardHeader title="Hints" />
        <p className="p-4 text-sm text-zinc-400 sm:p-5">
          Hints are not available during an assessment.
        </p>
      </Card>
    );
  }

  const revealNext = () => {
    const nextCount = nextHintRevealCount(revealedCount, hints.length);
    setRevealedCount(nextCount);
    if (nextCount > revealedCount) onReveal(nextCount);
  };

  return (
    <Card>
      <CardHeader
        title={
          <span className="flex items-center gap-2">
            <IconBulb aria-hidden="true" className="h-5 w-5 text-sky-400" />
            Hints
          </span>
        }
      />
      <div className="p-4 sm:p-5">
        {!open ? (
          <Button className="w-full" onClick={() => setOpen(true)} variant="ghost">
            Open hints
          </Button>
        ) : (
          <>
            {revealedCount ? (
              <ol className="space-y-3">
                {hints.slice(0, revealedCount).map((hint, index) => (
                  <li className="flex gap-3 text-sm text-zinc-300" key={`${index}-${hint}`}>
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 font-mono text-xs font-bold text-sky-400">
                      {index + 1}
                    </span>
                    <span>{hint}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-sm text-zinc-400">
                Hints are only used when you choose to reveal one.
              </p>
            )}
            <div className="mt-4 border-t border-zinc-800 pt-4">
              {revealedCount < hints.length ? (
                <Button onClick={revealNext} variant="ghost">
                  {revealedCount === 0
                    ? 'Reveal the next hint'
                    : `Reveal another hint (${revealedCount}/${hints.length})`}
                  <IconChevronRight aria-hidden="true" className="h-4 w-4" />
                </Button>
              ) : (
                <p className="text-xs font-semibold text-emerald-400">
                  All {hints.length} hints revealed
                </p>
              )}
              <p className="mt-2 text-xs text-zinc-500">
                {revealedCount} of {hints.length} revealed.{' '}
                {revealedCount < hints.length
                  ? 'Another hint is available.'
                  : 'No more hints are available.'}
              </p>
            </div>
          </>
        )}
      </div>
    </Card>
  );
}
