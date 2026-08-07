import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Textarea } from './textarea';

describe('Textarea', () => {
  it('renders a multiline input with the shared focus treatment', () => {
    render(<Textarea aria-label="Internal note" />);

    expect(screen.getByRole('textbox', { name: 'Internal note' })).toHaveClass(
      'sd-textarea',
      'sd-focus-ring',
      'bg-zinc-950',
    );
  });
});
