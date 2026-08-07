import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Priority } from '@service-desk/shared';

import { Badge, type BadgeVariant, PriorityBadge } from './badge';

describe('Badge', () => {
  it.each([
    ['default', 'text-zinc-300'],
    ['sky', 'text-sky-300'],
    ['amber', 'text-amber-300'],
    ['success', 'text-emerald-400'],
  ] satisfies Array<[BadgeVariant, string]>)(
    'applies the %s visual variant',
    (variant, colorClass) => {
      render(<Badge variant={variant}>{variant}</Badge>);

      expect(screen.getByText(variant)).toHaveClass('sd-badge', colorClass);
    },
  );
});

describe('PriorityBadge', () => {
  it.each([
    [Priority.Critical, 'text-red-500'],
    [Priority.High, 'text-red-400'],
    [Priority.Medium, 'text-orange-400'],
    [Priority.Low, 'text-amber-500'],
  ])('applies the %s priority color', (priority, colorClass) => {
    render(<PriorityBadge priority={priority} />);

    expect(screen.getByText(priority)).toHaveClass(
      'sd-priority-badge',
      colorClass,
    );
  });

  it('supports the optional pill treatment', () => {
    render(<PriorityBadge pill priority={Priority.High} />);

    expect(screen.getByText(Priority.High)).toHaveClass('rounded-sm', 'border');
  });
});
