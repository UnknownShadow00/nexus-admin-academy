import type { HTMLAttributes } from 'react';

import { Priority } from '@service-desk/shared';

import { cn } from './lib/cn';

export type BadgeVariant = 'amber' | 'default' | 'sky' | 'success';

const badgeVariants: Record<BadgeVariant, string> = {
  amber: 'border-amber-400/30 bg-amber-400/10 text-amber-300',
  default: 'border-zinc-700 bg-zinc-800 text-zinc-300',
  sky: 'border-sky-400/30 bg-sky-400/10 text-sky-300',
  success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
};

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export function Badge({
  className,
  variant = 'default',
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        'sd-badge inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-extrabold uppercase',
        badgeVariants[variant],
        className,
      )}
      {...props}
    />
  );
}

const priorityClasses: Record<Priority, string> = {
  [Priority.Critical]: 'text-red-500',
  [Priority.High]: 'text-red-400',
  [Priority.Medium]: 'text-orange-400',
  [Priority.Low]: 'text-amber-500',
};

export interface PriorityBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  pill?: boolean;
  priority: Priority;
}

export function PriorityBadge({
  children,
  className,
  pill = false,
  priority,
  ...props
}: PriorityBadgeProps) {
  return (
    <span
      className={cn(
        'sd-priority-badge inline-flex items-center text-xs font-extrabold uppercase',
        priorityClasses[priority],
        pill && 'rounded-sm border border-current/30 bg-zinc-950 px-2 py-0.5',
        className,
      )}
      data-priority={priority}
      {...props}
    >
      {children ?? priority}
    </span>
  );
}
