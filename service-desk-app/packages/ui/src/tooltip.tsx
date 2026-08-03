'use client';

import * as RadixTooltip from '@radix-ui/react-tooltip';
import type { ReactElement, ReactNode } from 'react';

import { cn } from './lib/cn';

export interface TooltipProps {
  children: ReactElement;
  className?: string;
  content: ReactNode;
  defaultOpen?: boolean;
  delayDuration?: number;
  side?: 'bottom' | 'left' | 'right' | 'top';
}

export function Tooltip({
  children,
  className,
  content,
  defaultOpen,
  delayDuration = 200,
  side = 'top',
}: TooltipProps) {
  return (
    <RadixTooltip.Provider delayDuration={delayDuration}>
      <RadixTooltip.Root defaultOpen={defaultOpen}>
        <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content
            className={cn(
              'sd-tooltip z-50 rounded-md bg-zinc-800 px-2.5 py-1.5 text-xs font-semibold text-zinc-200 shadow-lg ring-1 ring-zinc-700/60',
              className,
            )}
            side={side}
            sideOffset={6}
          >
            {content}
            <RadixTooltip.Arrow className="fill-zinc-800" />
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  );
}
