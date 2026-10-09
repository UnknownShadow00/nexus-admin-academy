import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { useDarkMode } from './useDarkMode';

beforeEach(() => { localStorage.clear(); document.documentElement.classList.remove('dark'); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); document.documentElement.classList.remove('dark'); });
it('honors system dark preference without saving an unsolicited preference', () => {
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })));
  const { result } = renderHook(() => useDarkMode());
  expect(result.current[0]).toBe(true);
  expect(document.documentElement).toHaveClass('dark');
  expect(localStorage.getItem('theme')).toBeNull();
});
it('saved light overrides system dark and explicit changes survive a remount', () => {
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })));
  localStorage.setItem('theme', 'light');
  const hook = renderHook(() => useDarkMode());
  expect(hook.result.current[0]).toBe(false);
  act(() => hook.result.current[1](true));
  expect(localStorage.getItem('theme')).toBe('dark');
  hook.unmount();
  const { result } = renderHook(() => useDarkMode());
  expect(result.current[0]).toBe(true);
  act(() => result.current[1]((dark) => !dark));
  expect(localStorage.getItem('theme')).toBe('light');
  expect(document.documentElement).not.toHaveClass('dark');
});
