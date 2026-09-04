'use client';

import {
  getCloseReview,
  TicketStatus,
  type CloseReview,
} from '@service-desk/shared';
import { Button, Modal } from '@service-desk/ui';
import {
  IconAlertTriangle,
  IconCircleCheck,
  IconLock,
  IconNote,
} from '@tabler/icons-react';
import React, { useState } from 'react';
import type { ActionEvent } from '@service-desk/simulation-engine';

interface ResolveDialogProps {
  /**
   * The latest note from the ONE editable documentation surface
   * (ResolutionNotePanel). Resolve never edits or re-submits it: this dialog is
   * a read-only summary, so a second, ungraded note store cannot exist.
   */
  documentationNote: string;
  onConfirm: (options: {
    resolutionNote: string;
    verifiedResolved: boolean;
  }) => ActionEvent;
  status: TicketStatus;
}

export function closeRejectionMessage(event: ActionEvent): string {
  return (
    event.rejectReason ||
    'This ticket is not ready to close. Review the required steps and try again.'
  );
}

/**
 * Read-only view of the ONE editable documentation surface. Resolve never
 * offers a second textarea, so it cannot create an ungraded duplicate note.
 * Rendered separately from the modal shell so it can be asserted without a DOM.
 */
export function DocumentationSummary({ note }: { note: string }) {
  const trimmed = note.trim();
  const hasDocumentation = trimmed.length > 0;
  return (
    <div
      className={`flex gap-3 rounded-sm border p-3 ${
        hasDocumentation
          ? 'border-border bg-surface-muted'
          : 'border-warning/40 bg-warning/10'
      }`}
    >
      <IconNote
        aria-hidden="true"
        className={`mt-0.5 h-5 w-5 shrink-0 ${
          hasDocumentation ? 'text-success' : 'text-warning'
        }`}
      />
      <div className="min-w-0">
        <p className="text-sm font-bold text-text">
          {hasDocumentation ? 'Documentation recorded' : 'Documentation required'}
        </p>
        {hasDocumentation ? (
          <p className="mt-1 whitespace-pre-wrap text-sm text-text-muted">
            {trimmed}
          </p>
        ) : (
          <p className="mt-1 text-sm text-text-muted">
            Add your internal resolution note in the workspace
            Resolution&nbsp;notes panel before closing. Notes written there are
            the ones Nexus grades.
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * Outcome notice for the review step.
 *
 * Deliberately carries NO points or pass preview: the browser cannot predict
 * every server outcome (escalation profiles, prohibited actions), so a
 * predicted score could contradict the authoritative grade.
 */
export function CloseReviewNotice({ review }: { review: CloseReview }) {
  const unresolved = review.kind === 'unresolved-warning';
  return (
    <div
      className={`flex gap-3 rounded-sm border p-4 ${
        unresolved
          ? 'border-warning/40 bg-warning/10'
          : 'border-success/40 bg-success/10'
      }`}
      role="alert"
    >
      {unresolved ? (
        <IconAlertTriangle
          aria-hidden="true"
          className="h-5 w-5 shrink-0 text-warning"
        />
      ) : (
        <IconLock aria-hidden="true" className="h-5 w-5 shrink-0 text-success" />
      )}
      <div>
        <p className="text-sm font-bold text-text">
          {unresolved ? 'Unresolved close warning' : 'Ready to resolve'}
        </p>
        <p className="mt-1 text-sm leading-relaxed text-text-muted">
          {review.message}
        </p>
        <p className="mt-2 text-xs font-semibold text-text-muted">
          Nexus will check your investigation, diagnosis, action, verification,
          and documentation after you submit.
        </p>
      </div>
    </div>
  );
}

export function ResolveDialog({
  documentationNote,
  onConfirm,
  status,
}: ResolveDialogProps) {
  const [open, setOpen] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [verifiedResolved, setVerifiedResolved] = useState(false);
  const [rejection, setRejection] = useState('');
  const note = documentationNote.trim();
  const effectiveVerified =
    verifiedResolved || status === TicketStatus.Resolved;
  const review = getCloseReview(status, effectiveVerified);

  function reset() {
    setReviewing(false);
    setVerifiedResolved(false);
    setRejection('');
  }

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    reset();
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
          Resolve
        </Button>
      }
    >
      {!reviewing ? (
        <>
          <DocumentationSummary note={note} />
          <label className="mt-4 flex cursor-pointer items-start gap-3 rounded-sm border border-border bg-surface-muted p-3">
            <input
              checked={verifiedResolved}
              className="mt-0.5 h-4 w-4 accent-accent"
              onChange={(event) => setVerifiedResolved(event.target.checked)}
              type="checkbox"
            />
            <span>
              <span className="block text-sm font-semibold text-text">
                I verified the requester has a working outcome
              </span>
              <span className="mt-1 block text-xs leading-relaxed text-text-muted">
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
          <CloseReviewNotice review={review} />
          {note ? (
            <div className="mt-4 rounded-sm border border-border bg-surface-muted p-3">
              <p className="text-[11px] font-bold uppercase tracking-wide text-text-muted">
                Final note
              </p>
              <p className="mt-1 whitespace-pre-wrap text-sm text-text">
                {note}
              </p>
            </div>
          ) : null}
          <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button onClick={() => setReviewing(false)}>Back</Button>
            <Button
              onClick={() => {
                const event = onConfirm({
                  resolutionNote: note,
                  verifiedResolved: effectiveVerified,
                });
                if (!event.success) {
                  setRejection(closeRejectionMessage(event));
                  return;
                }
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
          {rejection ? (
            <p
              className="mt-3 rounded-sm border border-warning/40 bg-warning/10 p-3 text-sm font-semibold text-text"
              role="alert"
            >
              {rejection}
            </p>
          ) : null}
        </>
      )}
    </Modal>
  );
}
