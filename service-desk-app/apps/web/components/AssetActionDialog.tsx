'use client';

import { Button, Modal, type ButtonVariant } from '@service-desk/ui';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useState, type ReactNode } from 'react';

interface AssetActionDialogProps {
  confirmLabel: string;
  description: string;
  onConfirm: () => void;
  title: string;
  trigger: ReactNode;
  variant?: ButtonVariant;
}

export function AssetActionDialog({
  confirmLabel,
  description,
  onConfirm,
  title,
  trigger,
  variant = 'primary',
}: AssetActionDialogProps) {
  const [open, setOpen] = useState(false);

  return (
    <Modal
      description="Confirm this inventory change before it is recorded."
      onOpenChange={setOpen}
      open={open}
      title={title}
      trigger={trigger}
    >
      <div className="flex gap-3 rounded-sm border border-amber-400/30 bg-amber-400/10 p-3">
        <IconAlertTriangle
          aria-hidden="true"
          className="h-5 w-5 shrink-0 text-amber-400"
        />
        <p className="text-sm leading-relaxed text-zinc-300">{description}</p>
      </div>
      <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button onClick={() => setOpen(false)}>Cancel</Button>
        <Button
          onClick={() => {
            onConfirm();
            setOpen(false);
          }}
          variant={variant}
        >
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
