import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { IconButton } from './icon-button';

describe('IconButton', () => {
  it('renders an accessible square icon control', () => {
    render(<IconButton aria-label="Open tools">+</IconButton>);

    expect(screen.getByRole('button', { name: 'Open tools' })).toHaveClass(
      'sd-icon-btn',
      'h-8',
      'w-8',
      'rounded-sm',
    );
  });
});
