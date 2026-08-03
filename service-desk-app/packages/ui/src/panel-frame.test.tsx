import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PanelFrame, type PanelFrameVariant } from './panel-frame';

describe('PanelFrame', () => {
  it.each([
    ['default', 'bg-zinc-900'],
    ['ad', 'sd-panel-frame--ad'],
    ['assets', 'sd-panel-frame--assets'],
    ['contained', 'sd-panel-frame--contained'],
    ['fab-clearance', 'sd-panel-frame--fab-clearance'],
  ] satisfies Array<[PanelFrameVariant, string]>)(
    'applies the %s variant classes',
    (variant, variantClass) => {
      render(<PanelFrame variant={variant}>{variant} frame</PanelFrame>);

      expect(screen.getByText(`${variant} frame`)).toHaveClass(
        'sd-panel-frame',
        variantClass,
      );
    },
  );
});
