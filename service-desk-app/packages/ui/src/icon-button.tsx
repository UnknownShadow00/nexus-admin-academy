'use client';

import { forwardRef, type ButtonHTMLAttributes } from 'react';

import { cn } from './lib/cn';

export interface IconButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement> {
  'aria-label': string;
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ className, type = 'button', ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(
        'sd-icon-btn sd-focus-ring inline-flex h-8 w-8 items-center justify-center rounded-sm border border-border bg-surface-raised text-text transition-colors hover:bg-surface-muted hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    />
  ),
);

IconButton.displayName = 'IconButton';
