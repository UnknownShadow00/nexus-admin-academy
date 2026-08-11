import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { BackToNexusLink } from './BackToNexusLink';

describe('BackToNexusLink', () => {
  it('uses a same-origin, history-independent and accessible Nexus destination', () => {
    const markup = renderToStaticMarkup(<BackToNexusLink />);

    expect(markup).toContain('href="/"');
    expect(markup).toContain('aria-label="Back to Nexus"');
    expect(markup).toContain('Back to Nexus');
    expect(markup).not.toContain('javascript:history');
  });
});
