import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Button, type ButtonVariant } from './button';

describe('Button', () => {
  it('renders a button with the default variant', () => {
    render(<Button>Continue</Button>);

    expect(screen.getByRole('button', { name: 'Continue' })).toHaveClass(
      'sd-button',
      'sd-button--default',
    );
  });

  it.each([
    ['ghost', 'sd-button--ghost', 'bg-transparent'],
    ['primary', 'sd-button--primary', 'bg-sky-600'],
    ['light', 'sd-button--light', 'bg-zinc-100'],
    ['soft', 'sd-soft-btn', 'bg-sky-400/10'],
  ] satisfies Array<[ButtonVariant, string, string]>)(
    'applies the %s variant classes',
    (variant, variantClass, colorClass) => {
      render(<Button variant={variant}>{variant}</Button>);

      expect(screen.getByRole('button', { name: variant })).toHaveClass(
        variantClass,
        colorClass,
      );
    },
  );
});
