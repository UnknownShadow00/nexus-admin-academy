import type { HTMLAttributes, ReactNode } from 'react';

import { cn } from './lib/cn';

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <section
      className={cn(
        'sd-card overflow-hidden rounded-md border border-border bg-surface-raised text-text',
        className,
      )}
      {...props}
    />
  );
}

export interface CardHeaderProps
  extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  title: ReactNode;
  meta?: ReactNode;
}

export function CardHeader({
  className,
  meta,
  title,
  ...props
}: CardHeaderProps) {
  return (
    <header
      className={cn(
        'sd-card-header flex items-center justify-between gap-3 border-b border-border bg-surface-muted px-4 py-3',
        className,
      )}
      {...props}
    >
      <span className="sd-card-header__title text-sm font-extrabold uppercase text-text">
        {title}
      </span>
      {meta ? (
        <span className="sd-card-header__meta text-xs font-semibold text-text-muted">
          {meta}
        </span>
      ) : null}
    </header>
  );
}
