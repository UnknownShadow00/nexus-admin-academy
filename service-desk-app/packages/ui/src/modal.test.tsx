import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Button } from './button';
import { Modal } from './modal';

describe('Modal', () => {
  it('opens from its trigger and renders the documented modal classes', () => {
    render(
      <Modal
        description="Review the preview."
        title="Confirm action"
        trigger={<Button>Open modal</Button>}
      >
        Modal body
      </Modal>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Open modal' }));

    expect(screen.getByRole('dialog')).toHaveClass(
      'sd-modal-card',
      'bg-zinc-900',
    );
    expect(screen.getByText('Confirm action')).toBeVisible();
    expect(screen.getByText('Modal body')).toBeVisible();
  });

  it('closes with Escape and restores focus to its trigger', async () => {
    render(
      <Modal
        description="Keyboard behavior preview."
        title="Keyboard behavior"
        trigger={<Button>Launch tools</Button>}
      >
        <Button>First tool</Button>
      </Modal>,
    );

    const trigger = screen.getByRole('button', { name: 'Launch tools' });
    fireEvent.click(trigger);
    expect(screen.getByRole('dialog')).toBeVisible();

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });
});
