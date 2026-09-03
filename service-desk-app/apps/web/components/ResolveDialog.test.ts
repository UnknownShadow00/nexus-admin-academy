import type { ActionEvent } from '@service-desk/simulation-engine';
import { describe, expect, it } from 'vitest';
import { closeRejectionMessage } from './ResolveDialog';

describe('ResolveDialog close feedback', () => {
  it('surfaces the exact trusted workflow rejection in the open dialog', () => {
    const event = { success: false, rejectReason: 'Verify the fix before closing.' } as ActionEvent;
    expect(closeRejectionMessage(event)).toBe('Verify the fix before closing.');
  });
});
