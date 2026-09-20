import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { V2Error } from './V2PageState';

describe('V2Error recovery', () => {
  it('offers retry, module, and Today recovery routes', async () => {
    const retry = vi.fn();
    render(<MemoryRouter><V2Error message="We couldn't save your answer. Your work is still here." moduleRoute="/learning-v2/modules/example" onRetry={retry} /></MemoryRouter>);
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(retry).toHaveBeenCalledOnce();
    expect(screen.getByRole('link', { name: 'Back to module' })).toHaveAttribute('href', '/learning-v2/modules/example');
    expect(screen.getByRole('link', { name: 'Back to Today' })).toHaveAttribute('href', '/');
  });
});
