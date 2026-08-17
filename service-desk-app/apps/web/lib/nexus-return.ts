const STORAGE_KEY = 'sd:nexusReturnTo';

// Only same-origin Nexus training routes are ever accepted as a return
// destination. Reject anything that could be turned into an open redirect
// (absolute URLs, protocol-relative paths, javascript: links, etc.).
const SAFE_RETURN_PATTERN = /^\/training(\/week\/[1-9][0-9]*)?$/;

export function isSafeNexusReturnPath(
  value: string | null | undefined,
): value is string {
  if (!value) return false;
  if (!value.startsWith('/') || value.startsWith('//')) return false;
  if (value.includes('://') || value.includes('\\')) return false;
  return SAFE_RETURN_PATTERN.test(value);
}

export function nexusReturnLabel(path: string): string {
  const match = path.match(/^\/training\/week\/(\d+)$/);
  return match ? `Back to Week ${match[1]}` : 'Back to Training';
}

export function readStoredNexusReturn(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const stored = window.sessionStorage.getItem(STORAGE_KEY);
    return isSafeNexusReturnPath(stored) ? stored : null;
  } catch {
    return null;
  }
}

export function storeNexusReturn(path: string): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, path);
  } catch {
    // Ignore storage failures (private browsing, quota) — the link just
    // falls back to the generic Nexus destination.
  }
}
