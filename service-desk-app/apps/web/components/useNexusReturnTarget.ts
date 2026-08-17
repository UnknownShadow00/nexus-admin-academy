'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import {
  isSafeNexusReturnPath,
  nexusReturnLabel,
  readStoredNexusReturn,
  storeNexusReturn,
} from '../lib/nexus-return';

export interface NexusReturnTarget {
  href: string;
  label: string;
}

// Captures a `returnTo` launch param once and remembers it (in-memory and in
// sessionStorage) so the "Back to Week N" link keeps working after
// navigating from the ticket into a tool and back, or after a page reload.
// Only same-origin Nexus training routes are ever accepted — see
// isSafeNexusReturnPath in lib/nexus-return.ts.
export function useNexusReturnTarget(): NexusReturnTarget | null {
  const searchParams = useSearchParams();
  const [target, setTarget] = useState<NexusReturnTarget | null>(() => {
    const stored = readStoredNexusReturn();
    return stored ? { href: stored, label: nexusReturnLabel(stored) } : null;
  });

  useEffect(() => {
    const raw = searchParams.get('returnTo');
    if (isSafeNexusReturnPath(raw)) {
      storeNexusReturn(raw);
      setTarget({ href: raw, label: nexusReturnLabel(raw) });
    }
  }, [searchParams]);

  return target;
}
