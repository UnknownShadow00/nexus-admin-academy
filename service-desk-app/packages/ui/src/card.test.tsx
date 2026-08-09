import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Card, CardHeader } from './card';

describe('Card', () => {
  it('renders card content with surface classes', () => {
    render(<Card>Card body</Card>);

    expect(screen.getByText('Card body')).toHaveClass('sd-card', 'bg-zinc-900');
  });
});

describe('CardHeader', () => {
  it('renders its title and trailing metadata', () => {
    render(<CardHeader title="Recent items" meta="4 open" />);

    expect(screen.getByText('Recent items')).toHaveClass(
      'sd-card-header__title',
    );
    expect(screen.getByText('4 open')).toHaveClass('sd-card-header__meta');
  });
});
