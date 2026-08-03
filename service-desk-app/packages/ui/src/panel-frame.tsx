import type { HTMLAttributes } from 'react';

import { cn } from './lib/cn';

export type PanelFrameVariant =
  | 'ad'
  | 'assets'
  | 'contained'
  | 'default'
  | 'fab-clearance';

const variants: Record<PanelFrameVariant, string> = {
  ad: 'sd-panel-frame--ad border-zinc-800 bg-zinc-950',
  assets: 'sd-panel-frame--assets border-zinc-700 bg-zinc-900',
  contained:
    'sd-panel-frame--contained mx-auto max-w-5xl border-zinc-700 bg-zinc-900',
  default: 'border-zinc-800 bg-zinc-900',
  'fab-clearance':
    'sd-panel-frame--fab-clearance border-zinc-800 bg-zinc-900 pb-24',
};

export interface PanelFrameProps extends HTMLAttributes<HTMLDivElement> {
  variant?: PanelFrameVariant;
}

export function PanelFrame({
  className,
  variant = 'default',
  ...props
}: PanelFrameProps) {
  return (
    <section
      className={cn(
        'sd-panel-frame min-h-28 rounded-md border p-4 text-zinc-300',
        variants[variant],
        className,
      )}
      data-variant={variant}
      {...props}
    />
  );
}
