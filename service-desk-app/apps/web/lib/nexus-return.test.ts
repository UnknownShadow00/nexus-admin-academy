import { describe, expect, it } from 'vitest';

import { isSafeNexusReturnPath, nexusReturnLabel } from './nexus-return';

describe('isSafeNexusReturnPath', () => {
  it('accepts allowlisted Nexus training routes', () => {
    expect(isSafeNexusReturnPath('/training/week/1')).toBe(true);
    expect(isSafeNexusReturnPath('/training/week/24')).toBe(true);
    expect(isSafeNexusReturnPath('/training')).toBe(true);
  });

  it('rejects absolute and protocol-relative URLs', () => {
    expect(isSafeNexusReturnPath('https://evil.example.com')).toBe(false);
    expect(isSafeNexusReturnPath('//evil.example.com')).toBe(false);
    expect(isSafeNexusReturnPath('http://evil.example.com/training/week/1')).toBe(false);
  });

  it('rejects javascript: and other unsafe schemes', () => {
    expect(isSafeNexusReturnPath('javascript:alert(1)')).toBe(false);
    expect(isSafeNexusReturnPath('data:text/html,evil')).toBe(false);
  });

  it('rejects paths outside the training allowlist', () => {
    expect(isSafeNexusReturnPath('/admin')).toBe(false);
    expect(isSafeNexusReturnPath('/training/week/1/../../admin')).toBe(false);
    expect(isSafeNexusReturnPath('/training/week/abc')).toBe(false);
    expect(isSafeNexusReturnPath('/training/week/0')).toBe(false);
  });

  it('rejects empty, null, and undefined values', () => {
    expect(isSafeNexusReturnPath('')).toBe(false);
    expect(isSafeNexusReturnPath(null)).toBe(false);
    expect(isSafeNexusReturnPath(undefined)).toBe(false);
  });
});

describe('nexusReturnLabel', () => {
  it('builds a week-specific label for week routes', () => {
    expect(nexusReturnLabel('/training/week/1')).toBe('Back to Week 1');
    expect(nexusReturnLabel('/training/week/12')).toBe('Back to Week 12');
  });

  it('falls back to a generic label for the training root', () => {
    expect(nexusReturnLabel('/training')).toBe('Back to Training');
  });
});
