'use client';

import { forwardRef, type ButtonHTMLAttributes } from 'react';

import { cn } from './lib/cn';

export type ButtonVariant = 'default' | 'ghost' | 'light' | 'primary' | 'soft';

const variants: Record<ButtonVariant, string> = {
  default:
    'sd-button--default border border-zinc-700 bg-zinc-900 text-zinc-200 hover:bg-zinc-800',
  ghost:
    'sd-button--ghost border border-transparent bg-transparent text-sky-400 hover:bg-zinc-800 hover:text-sky-300',
  light:
    'sd-button--light border border-zinc-300 bg-zinc-100 text-zinc-900 hover:bg-zinc-300',
  primary:
    'sd-button--primary border border-sky-500 bg-sky-600 text-zinc-100 hover:bg-sky-500',
  soft: 'sd-soft-btn border border-sky-400/30 bg-sky-400/10 text-sky-300 hover:bg-sky-400/20',
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, type = 'button', variant = 'default', ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(
        'sd-button sd-focus-ring inline-flex min-h-10 items-center justify-center gap-2 rounded-sm px-4 py-2 text-sm font-extrabold uppercase transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950 disabled:cursor-not-allowed disabled:opacity-50',
        variants[variant],
        className,
      )}
      {...props}
    />
  ),
);

Button.displayName = 'Button';
