import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

const css = readFileSync(join(process.cwd(), 'src', 'styles.css'), 'utf8');

const TOKENS = [
  '--sd-surface',
  '--sd-surface-raised',
  '--sd-surface-muted',
  '--sd-text',
  '--sd-text-muted',
  '--sd-border',
  '--sd-accent',
  '--sd-accent-contrast',
  '--sd-success',
  '--sd-warning',
  '--sd-danger',
  '--sd-pending',
  '--sd-focus',
];

function blockFor(selector: string): string {
  const start = css.indexOf(selector);
  expect(start, `missing ${selector} block`).toBeGreaterThan(-1);
  const open = css.indexOf('{', start);
  const close = css.indexOf('}', open);
  return css.slice(open, close);
}

describe('semantic theme tokens', () => {
  it('defines every token in the dark (default) scope', () => {
    const dark = blockFor(":root,\n  [data-theme='dark']");
    for (const token of TOKENS) {
      expect(dark, `${token} missing from dark scope`).toContain(`${token}:`);
    }
  });

  it('overrides every token in the light scope - no token is dark-only', () => {
    const light = blockFor("[data-theme='light'] {");
    for (const token of TOKENS) {
      expect(light, `${token} missing from light scope`).toContain(`${token}:`);
    }
  });

  it('no longer ships the sci-fi display fonts', () => {
    expect(css).not.toMatch(/Orbitron|Rajdhani|Share Tech Mono/);
  });
});
