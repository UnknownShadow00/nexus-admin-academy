import { describe, expect, it, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

import { buildStudentNavItems } from '../App';

vi.mock('../services/api', () => ({ getV2Access: vi.fn() }));

const { getV2Access } = await import('../services/api');
const { useV2Access } = await import('./useV2Access');

describe('per-student V2 pilot visibility', () => {
  beforeEach(() => {
    getV2Access.mockReset();
  });

  it('hides My Course from a student who is not in the pilot', async () => {
    getV2Access.mockResolvedValue({
      data: { master_enabled: true, student_enabled: false, mode: 'not_enrolled' },
    });
    const { result } = renderHook(() => useV2Access(true));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.studentEnabled).toBe(false);
    const labels = buildStudentNavItems(result.current.studentEnabled).map((item) => item.label);
    expect(labels).not.toContain('My Course');
  });

  it('shows My Course to an enrolled pilot student', async () => {
    getV2Access.mockResolvedValue({
      data: { master_enabled: true, student_enabled: true, mode: 'pilot' },
    });
    const { result } = renderHook(() => useV2Access(true));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.studentEnabled).toBe(true);
    expect(buildStudentNavItems(result.current.studentEnabled).map((item) => item.label))
      .toContain('My Course');
  });

  it('fails closed when the access check errors', async () => {
    getV2Access.mockRejectedValue(new Error('network down'));
    const { result } = renderHook(() => useV2Access(true));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.studentEnabled).toBe(false);
    expect(result.current.masterEnabled).toBe(false);
  });

  it('does not ask on behalf of an unauthenticated visitor', async () => {
    const { result } = renderHook(() => useV2Access(false));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(getV2Access).not.toHaveBeenCalled();
    expect(result.current.studentEnabled).toBe(false);
  });
});
