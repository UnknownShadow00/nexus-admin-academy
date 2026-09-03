import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Button, type ButtonVariant } from './button';

describe('Button', () => {
  it('defaults to the tertiary (low-priority) intent', () => {
    render(<Button>Continue</Button>);
    expect(screen.getByRole('button', { name: 'Continue' })).toHaveClass(
      'sd-button',
      'sd-button--tertiary',
    );
  });

  it.each([
    ['primary', 'sd-button--primary', 'bg-accent'],
    ['secondary', 'sd-button--secondary', 'bg-surface-raised'],
    ['tertiary', 'sd-button--tertiary', 'bg-transparent'],
    ['danger', 'sd-button--danger', 'bg-danger'],
  ] satisfies Array<[ButtonVariant, string, string]>)(
    'applies the %s intent classes',
    (variant, variantClass, colorClass) => {
      render(<Button variant={variant}>{variant}</Button>);
      expect(screen.getByRole('button', { name: variant })).toHaveClass(
        variantClass,
        colorClass,
      );
    },
  );

  it.each([
    ['light', 'sd-button--secondary'],
    ['soft', 'sd-button--secondary'],
    ['ghost', 'sd-button--tertiary'],
    ['default', 'sd-button--tertiary'],
  ] satisfies Array<[ButtonVariant, string]>)(
    'maps the legacy %s name onto a canonical intent',
    (variant, canonicalClass) => {
      render(<Button variant={variant}>{variant}</Button>);
      expect(screen.getByRole('button', { name: variant })).toHaveClass(
        canonicalClass,
      );
    },
  );
});
