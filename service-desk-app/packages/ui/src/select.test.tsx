import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Select } from './select';

describe('Select', () => {
  it('renders the shared select treatment and accepts a value change', () => {
    render(
      <Select aria-label="Priority" defaultValue="all">
        <option value="all">All priorities</option>
        <option value="high">High</option>
      </Select>,
    );

    const select = screen.getByRole('combobox', { name: 'Priority' });
    fireEvent.change(select, { target: { value: 'high' } });

    expect(select).toHaveClass('sd-select', 'sd-focus-ring', 'bg-zinc-950');
    expect(select).toHaveValue('high');
  });
});
