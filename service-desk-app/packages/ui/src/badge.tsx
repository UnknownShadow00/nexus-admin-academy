import type { HTMLAttributes } from 'react';

import { Priority } from '@service-desk/shared';

import { cn } from './lib/cn';

export type BadgeVariant = 'amber' | 'default' | 'sky' | 'success';

const badgeVariants: Record<BadgeVariant, string> = {
  amber: 'border-warning/30 bg-warning/10 text-warning',
  default: 'border-border bg-surface-muted text-text',
  sky: 'border-accent/30 bg-accent/10 text-accent',
  success: 'border-success/30 bg-success/10 text-success',
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

// A four-step severity ramp built from the semantic tokens, so it stays legible
// in both themes: danger for the two red tiers, warning for the two amber ones.
const priorityClasses: Record<Priority, string> = {
  [Priority.Critical]: 'text-danger',
  [Priority.High]: 'text-danger/85',
  [Priority.Medium]: 'text-warning',
  [Priority.Low]: 'text-warning/85',
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
        pill && 'rounded-sm border border-current/30 bg-surface px-2 py-0.5',
        className,
      )}
      data-priority={priority}
      {...props}
    >
      {children ?? priority}
    </span>
  );
}
