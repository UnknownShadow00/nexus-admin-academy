import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Input } from './input';

describe('Input', () => {
  it('renders an input with the shared focus treatment', () => {
    render(<Input aria-label="Search" placeholder="Search records" />);

    expect(screen.getByRole('textbox', { name: 'Search' })).toHaveClass(
      'sd-input',
      'sd-focus-ring',
      'bg-zinc-950',
    );
  });
});
