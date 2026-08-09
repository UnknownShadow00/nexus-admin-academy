'use client';

import {
  initialHintRevealCount,
  nextHintRevealCount,
} from '@service-desk/shared';
import { Button, Modal } from '@service-desk/ui';
import {
  IconBulb,
  IconChevronRight,
  IconHelpCircle,
} from '@tabler/icons-react';
import { useEffect, useState } from 'react';

interface HintDialogProps {
  hints: readonly string[];
  onReveal: (step: number) => void;
  revealedCount?: number;
}

export function HintDialog({
  hints,
  onReveal,
  revealedCount: persistedRevealedCount = 0,
}: HintDialogProps) {
  const [open, setOpen] = useState(false);
  const [started, setStarted] = useState(persistedRevealedCount > 0);
  const [revealedCount, setRevealedCount] = useState(() =>
    persistedRevealedCount > 0
      ? persistedRevealedCount
      : initialHintRevealCount(hints.length),
  );

  // The persisted count only becomes accurate after TicketSessionProvider's
  // post-hydration localStorage restore, which lands a render or two after
  // this component's initial mount — so the lazy initializer above can be
  // stale. Catch up whenever the persisted value moves ahead of local state.
  useEffect(() => {
    if (persistedRevealedCount > revealedCount) {
      setRevealedCount(persistedRevealedCount);
    }
    if (persistedRevealedCount > 0) {
      setStarted(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [persistedRevealedCount]);

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    if (nextOpen && !started && revealedCount > 0) {
      setStarted(true);
      onReveal(1);
    }
  }

  function revealNext() {
    const nextCount = nextHintRevealCount(revealedCount, hints.length);
    setRevealedCount(nextCount);
    if (nextCount > revealedCount) {
      onReveal(nextCount);
    }
  }

  return (
    <Modal
      closeLabel="Hide hints"
      description="Reveal one guided step at a time."
      onOpenChange={handleOpenChange}
      open={open}
      title="How to resolve this"
      trigger={
        <Button className="w-full sm:w-auto" variant="ghost">
          <IconHelpCircle aria-hidden="true" className="h-5 w-5" />I don&apos;t
          know how to fix this
        </Button>
      }
    >
      <div className="rounded-sm border border-sky-400/30 bg-zinc-950 p-4">
        <div className="flex items-center gap-2">
          <IconBulb aria-hidden="true" className="h-5 w-5 text-sky-400" />
          <p className="text-sm font-bold text-zinc-100">Guided steps</p>
        </div>
        <ol className="mt-4 space-y-3">
          {hints.slice(0, revealedCount).map((hint, index) => (
            <li className="flex gap-3 text-sm text-zinc-300" key={hint}>
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 font-mono text-xs font-bold text-sky-400">
                {index + 1}
              </span>
              <span className="pt-0.5 leading-relaxed">{hint}</span>
            </li>
          ))}
        </ol>
        <div className="mt-5 flex flex-col-reverse gap-2 border-t border-zinc-800 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <Button onClick={() => setOpen(false)}>Hide hints</Button>
          {revealedCount < hints.length ? (
            <Button onClick={revealNext} variant="ghost">
              Reveal next step ({revealedCount}/{hints.length})
              <IconChevronRight aria-hidden="true" className="h-4 w-4" />
            </Button>
          ) : (
            <p className="text-xs font-semibold text-emerald-400">
              All {hints.length} steps revealed
            </p>
          )}
        </div>
      </div>
    </Modal>
  );
}
