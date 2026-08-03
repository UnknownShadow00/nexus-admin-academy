import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { IconButton } from './icon-button';
import { Tooltip } from './tooltip';

describe('Tooltip', () => {
  it('renders its floating content with the documented surface classes', () => {
    render(
      <Tooltip content="Helpful detail" defaultOpen delayDuration={0}>
        <IconButton aria-label="More information">?</IconButton>
      </Tooltip>,
    );

    // Radix renders the visible styled surface as a plain <div> and puts
    // role="tooltip" on a separate visually-hidden accessibility node with
    // no classes, so we target the styled surface by class, not by role.
    expect(
      screen.getByText('Helpful detail', { selector: '.sd-tooltip' }),
    ).toHaveClass('sd-tooltip', 'bg-zinc-800');
  });
});
