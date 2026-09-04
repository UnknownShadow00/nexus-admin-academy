import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Priority } from '@service-desk/shared';

import { Badge, type BadgeVariant, PriorityBadge } from './badge';

describe('Badge', () => {
  it.each([
    ['default', 'text-text'],
    ['sky', 'text-accent'],
    ['amber', 'text-warning'],
    ['success', 'text-success'],
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
    [Priority.Critical, 'text-danger'],
    [Priority.High, 'text-danger/85'],
    [Priority.Medium, 'text-warning'],
    [Priority.Low, 'text-warning/85'],
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
