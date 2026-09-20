import type { HTMLAttributes } from 'react';

import { cn } from './lib/cn';

export type PanelFrameVariant =
  | 'ad'
  | 'assets'
  | 'contained'
  | 'default'
  | 'fab-clearance';

const variants: Record<PanelFrameVariant, string> = {
  ad: 'sd-panel-frame--ad border-border bg-surface',
  assets: 'sd-panel-frame--assets border-border bg-surface-raised',
  contained:
    'sd-panel-frame--contained mx-auto max-w-5xl border-border bg-surface-raised',
  default: 'border-border bg-surface-raised',
  'fab-clearance':
    'sd-panel-frame--fab-clearance border-border bg-surface-raised pb-24',
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
        'sd-panel-frame min-h-28 rounded-md border p-4 text-text',
        variants[variant],
        className,
      )}
      data-variant={variant}
      {...props}
    />
  );
}
