'use client';

import { forwardRef, type ButtonHTMLAttributes } from 'react';

import { cn } from './lib/cn';

/**
 * Four semantic intents:
 *  - primary   : the one action to do now
 *  - secondary : a valid alternate action (equal weight, not dominant)
 *  - tertiary  : navigation / low-priority
 *  - danger    : destructive only
 *
 * The pre-token names (default/ghost/light/soft) are kept as aliases so
 * existing call sites keep working while the sweep completes; they resolve to
 * the token-based styles above.
 */
export type ButtonVariant =
  | 'primary'
  | 'secondary'
  | 'tertiary'
  | 'danger'
  | 'default'
  | 'ghost'
  | 'light'
  | 'soft';

const PRIMARY =
  'sd-button--primary border border-accent bg-accent text-accent-contrast hover:opacity-90';
const SECONDARY =
  'sd-button--secondary border border-border bg-surface-raised text-text hover:bg-surface-muted';
const TERTIARY =
  'sd-button--tertiary border border-transparent bg-transparent text-accent hover:bg-surface-muted';
const DANGER =
  'sd-button--danger border border-danger bg-danger text-accent-contrast hover:opacity-90';

const variants: Record<ButtonVariant, string> = {
  primary: PRIMARY,
  secondary: SECONDARY,
  tertiary: TERTIARY,
  danger: DANGER,
  // aliases
  default: TERTIARY,
  ghost: TERTIARY,
  light: SECONDARY,
  soft: SECONDARY,
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, type = 'button', variant = 'tertiary', ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(
        'sd-button sd-focus-ring inline-flex min-h-10 items-center justify-center gap-2 rounded-sm px-4 py-2 text-sm font-bold uppercase tracking-wide transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:cursor-not-allowed disabled:opacity-50',
        variants[variant],
        className,
      )}
      {...props}
    />
  ),
);

Button.displayName = 'Button';
