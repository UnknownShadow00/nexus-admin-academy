'use client';

import * as Dialog from '@radix-ui/react-dialog';
import type { ReactNode } from 'react';

import { cn } from './lib/cn';

export interface ModalProps {
  children: ReactNode;
  className?: string;
  closeLabel?: string;
  defaultOpen?: boolean;
  description?: string;
  onOpenChange?: (open: boolean) => void;
  open?: boolean;
  title: string;
  trigger?: ReactNode;
}

export function Modal({
  children,
  className,
  closeLabel = 'Close modal',
  defaultOpen,
  description,
  onOpenChange,
  open,
  title,
  trigger,
}: ModalProps) {
  return (
    <Dialog.Root
      defaultOpen={defaultOpen}
      onOpenChange={onOpenChange}
      open={open}
    >
      {trigger ? <Dialog.Trigger asChild>{trigger}</Dialog.Trigger> : null}
      <Dialog.Portal>
        <Dialog.Overlay className="sd-modal-backdrop fixed inset-0 z-40 bg-zinc-950/80" />
        <Dialog.Content
          className={cn(
            'sd-modal-card fixed left-1/2 top-1/2 z-50 max-h-[85vh] w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-auto rounded-md border border-zinc-700 bg-zinc-900 text-zinc-300 shadow-lg ring-1 ring-zinc-700/60 focus:outline-none',
            className,
          )}
        >
          <header className="sd-modal-header flex items-start justify-between gap-4 border-b border-zinc-800 px-5 py-4">
            <div>
              <Dialog.Title className="text-base font-extrabold uppercase text-zinc-100">
                {title}
              </Dialog.Title>
              {description ? (
                <Dialog.Description className="mt-1 text-sm text-zinc-400">
                  {description}
                </Dialog.Description>
              ) : null}
            </div>
            <Dialog.Close
              aria-label={closeLabel}
              className="sd-icon-btn sd-focus-ring inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-sm text-xl text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            >
              <span aria-hidden="true">×</span>
            </Dialog.Close>
          </header>
          <div className="p-5">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
