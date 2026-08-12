'use client';

import { Button, Modal } from '@service-desk/ui';
import { IconKey, IconShieldCheck } from '@tabler/icons-react';
import { useState } from 'react';

interface PasswordResetDialogProps {
  disabled: boolean;
  fullName: string;
  onConfirm: (requireChangeAtNextSignIn: boolean) => void;
}

export function PasswordResetDialog({
  disabled,
  fullName,
  onConfirm,
}: PasswordResetDialogProps) {
  const [open, setOpen] = useState(false);
  const [requireChange, setRequireChange] = useState(true);

  return (
    <Modal
      description="Choose the training-safe reset options before issuing a temporary credential."
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
        if (!nextOpen) setRequireChange(true);
      }}
      open={open}
      title="Reset password"
      trigger={
        <Button disabled={disabled}>
          <IconKey aria-hidden="true" className="h-4 w-4" />
          Reset password
        </Button>
      }
    >
      <div className="space-y-4">
        <div className="rounded-sm border border-zinc-700 bg-zinc-950/60 p-4">
          <p className="text-sm font-bold text-zinc-100">{fullName}</p>
          <p className="mt-1 text-xs leading-relaxed text-zinc-400">
            A simulated temporary credential will be issued. The value is never
            generated, displayed, copied, or stored.
          </p>
        </div>

        <label className="flex cursor-pointer items-start gap-3 rounded-sm border border-sky-400/30 bg-sky-400/10 p-3">
          <input
            checked={requireChange}
            className="mt-0.5 h-4 w-4 accent-sky-500"
            onChange={(event) => setRequireChange(event.target.checked)}
            type="checkbox"
          />
          <span>
            <span className="flex items-center gap-2 text-sm font-bold text-zinc-100">
              <IconShieldCheck
                aria-hidden="true"
                className="h-4 w-4 text-sky-400"
              />
              Require change at next sign-in
            </span>
            <span className="mt-1 block text-xs leading-relaxed text-zinc-400">
              The requester must replace the temporary credential during the
              simulated sign-in handoff.
            </span>
          </span>
        </label>

        {!requireChange ? (
          <p className="rounded-sm border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-xs text-amber-300">
            This leaves a temporary credential usable after first sign-in and
            does not meet the Starter Support reset policy.
          </p>
        ) : null}

        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            onClick={() => {
              onConfirm(requireChange);
              setOpen(false);
            }}
            variant="primary"
          >
            Issue temporary credential
          </Button>
        </div>
      </div>
    </Modal>
  );
}
