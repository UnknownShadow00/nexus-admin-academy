'use client';

import { getCloseReview, TicketStatus } from '@service-desk/shared';
import { Button, Modal, Textarea } from '@service-desk/ui';
import {
  IconAlertTriangle,
  IconCircleCheck,
  IconLock,
} from '@tabler/icons-react';
import { useState } from 'react';

interface GradePreview {
  penaltyPoints: number;
  pointsAwarded: number;
  pointsPossible: number;
}

interface ResolveDialogProps {
  onConfirm: (options: {
    resolutionNote: string;
    verifiedResolved: boolean;
  }) => void;
  readyGrade: GradePreview | null;
  status: TicketStatus;
  unresolvedGrade: GradePreview | null;
}

export function ResolveDialog({
  onConfirm,
  readyGrade,
  status,
  unresolvedGrade,
}: ResolveDialogProps) {
  const [open, setOpen] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [resolutionNote, setResolutionNote] = useState('');
  const [verifiedResolved, setVerifiedResolved] = useState(false);
  const effectiveVerified =
    verifiedResolved || status === TicketStatus.Resolved;
  const review = getCloseReview(status, effectiveVerified);
  const grade =
    review.kind === 'unresolved-warning' ? unresolvedGrade : readyGrade;

  function reset() {
    setReviewing(false);
    setResolutionNote('');
    setVerifiedResolved(false);
  }

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    if (!nextOpen) {
      reset();
    }
  }

  return (
    <Modal
      description="Review the outcome before ending work on this incident."
      onOpenChange={handleOpenChange}
      open={open}
      title="Resolve or close ticket"
      trigger={
        <Button variant="primary">
          <IconCircleCheck aria-hidden="true" className="h-4 w-4" />
          Resolve / close
        </Button>
      }
    >
      {!reviewing ? (
        <>
          <label
            className="text-xs font-extrabold uppercase tracking-wide text-zinc-500"
            htmlFor="resolution-note"
          >
            Resolution note
          </label>
          <Textarea
            className="mt-2"
            id="resolution-note"
            onChange={(event) => setResolutionNote(event.target.value)}
            placeholder="Summarize the outcome or remaining risk…"
            value={resolutionNote}
          />
          <label className="mt-4 flex cursor-pointer items-start gap-3 rounded-sm border border-zinc-800 bg-zinc-950 p-3">
            <input
              checked={verifiedResolved}
              className="mt-0.5 h-4 w-4 accent-sky-500"
              onChange={(event) => setVerifiedResolved(event.target.checked)}
              type="checkbox"
            />
            <span>
              <span className="block text-sm font-semibold text-zinc-200">
                I verified the requester has a working outcome
              </span>
              <span className="mt-1 block text-xs leading-relaxed text-zinc-500">
                Leave this unchecked to review the unresolved-close warning
                path.
              </span>
            </span>
          </label>
          <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button onClick={() => handleOpenChange(false)}>Cancel</Button>
            <Button onClick={() => setReviewing(true)} variant="soft">
              Continue to review
            </Button>
          </div>
        </>
      ) : (
        <>
          <div
            className={`flex gap-3 rounded-sm border p-4 ${
              review.kind === 'unresolved-warning'
                ? 'border-amber-400/30 bg-amber-400/10'
                : 'border-emerald-500/30 bg-emerald-500/10'
            }`}
            role="alert"
          >
            {review.kind === 'unresolved-warning' ? (
              <IconAlertTriangle
                aria-hidden="true"
                className="h-5 w-5 shrink-0 text-amber-400"
              />
            ) : (
              <IconLock
                aria-hidden="true"
                className="h-5 w-5 shrink-0 text-emerald-400"
              />
            )}
            <div>
              <p className="text-sm font-bold text-zinc-100">
                {review.kind === 'unresolved-warning'
                  ? 'Unresolved close warning'
                  : 'Ready to resolve'}
              </p>
              <p className="mt-1 text-sm leading-relaxed text-zinc-300">
                {review.message}
              </p>
              {grade ? (
                <p className="mt-2 text-xs font-semibold text-zinc-400">
                  {review.kind === 'unresolved-warning'
                    ? `Closing now deducts ${grade.penaltyPoints} points and awards ${grade.pointsAwarded} of ${grade.pointsPossible} available points.`
                    : grade.penaltyPoints > 0
                      ? `A verified resolution awards ${grade.pointsAwarded} of ${grade.pointsPossible} points after ${grade.penaltyPoints} points in hint deductions.`
                      : `A verified resolution awards the full ${grade.pointsAwarded} points.`}
                </p>
              ) : (
                <p className="mt-2 text-xs text-zinc-500">
                  This ticket already has a recorded outcome, so no new score
                  will be added.
                </p>
              )}
            </div>
          </div>
          {resolutionNote.trim() ? (
            <div className="mt-4 rounded-sm border border-zinc-800 bg-zinc-950 p-3">
              <p className="text-[11px] font-bold uppercase tracking-wide text-zinc-500">
                Final note
              </p>
              <p className="mt-1 whitespace-pre-wrap text-sm text-zinc-300">
                {resolutionNote.trim()}
              </p>
            </div>
          ) : null}
          <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button onClick={() => setReviewing(false)}>Back</Button>
            <Button
              onClick={() => {
                onConfirm({
                  resolutionNote,
                  verifiedResolved: effectiveVerified,
                });
                setOpen(false);
                reset();
              }}
              variant={
                review.kind === 'unresolved-warning' ? 'default' : 'primary'
              }
            >
              {review.kind === 'unresolved-warning'
                ? 'Close anyway'
                : 'Resolve ticket'}
            </Button>
          </div>
        </>
      )}
    </Modal>
  );
}
