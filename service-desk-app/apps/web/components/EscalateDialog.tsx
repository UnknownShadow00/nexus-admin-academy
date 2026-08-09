'use client';

import { Button, Modal } from '@service-desk/ui';
import { IconAlertTriangle, IconArrowUpRight } from '@tabler/icons-react';
import { useState } from 'react';

interface EscalateDialogProps {
  escalated: boolean;
  onConfirm: () => void;
}

export function EscalateDialog({ escalated, onConfirm }: EscalateDialogProps) {
  const [open, setOpen] = useState(false);

  return (
    <Modal
      description="Flag the incident for specialist review."
      onOpenChange={setOpen}
      open={open}
      title="Escalate ticket"
      trigger={
        <Button disabled={escalated} variant="default">
          <IconArrowUpRight aria-hidden="true" className="h-4 w-4" />
          {escalated ? 'Escalated' : 'Escalate'}
        </Button>
      }
    >
      <div className="flex gap-3 rounded-sm border border-amber-400/30 bg-amber-400/10 p-3">
        <IconAlertTriangle
          aria-hidden="true"
          className="h-5 w-5 shrink-0 text-amber-400"
        />
        <p className="text-sm leading-relaxed text-zinc-300">
          This adds an escalation flag and timeline entry. No specialist queue
          or backend handoff is active in this fixture-only phase.
        </p>
      </div>
      <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button onClick={() => setOpen(false)}>Keep working</Button>
        <Button
          onClick={() => {
            onConfirm();
            setOpen(false);
          }}
          variant="primary"
        >
          Confirm escalation
        </Button>
      </div>
    </Modal>
  );
}
