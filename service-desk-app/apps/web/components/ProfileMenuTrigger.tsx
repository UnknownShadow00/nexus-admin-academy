'use client';

import { IconChevronDown } from '@tabler/icons-react';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

import { useSessionIdentity } from './TicketSessionProvider';

interface ProfileMenuTriggerProps {
  onPastTicketsOpen: () => void;
}

const PROFILE_ITEMS = ['Analytics', 'Achievements', 'Past Tickets'] as const;

export function ProfileMenuTrigger({
  onPastTicketsOpen,
}: ProfileMenuTriggerProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { isAdmin, isMentor, name } = useSessionIdentity();
  const roleLabel = isMentor ? 'Mentor' : isAdmin ? 'Admin' : 'Trainee';

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    }

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  return (
    <div className="relative" ref={rootRef}>
      <button
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label="Open profile menu"
        className="sd-focus-ring flex min-h-10 items-center gap-1.5 border-l border-zinc-700/50 pl-2 text-left transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 sm:gap-2.5 sm:pl-3"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <IconChevronDown
          aria-hidden="true"
          className={`h-4 w-4 shrink-0 text-zinc-400 transition-transform ${
            open ? 'rotate-180' : ''
          }`}
        />
        <span className="text-xl leading-none" aria-hidden="true">
          🧑‍💻
        </span>
        <span className="hidden min-w-0 flex-col items-start sm:flex">
          <span className="max-w-24 truncate text-sm font-semibold leading-tight text-zinc-100">
            {name}
          </span>
          <span className="text-[11px] font-bold uppercase text-zinc-500">
            {roleLabel}
          </span>
        </span>
      </button>

      {open ? (
        <div
          aria-label="Profile menu"
          className="absolute right-0 top-full z-30 mt-2 w-48 rounded-md border border-zinc-700 bg-zinc-900 p-1.5 shadow-lg ring-1 ring-zinc-700/60"
          role="menu"
        >
          {PROFILE_ITEMS.map((item) => (
            <button
              className="sd-focus-ring flex w-full rounded-sm px-3 py-2 text-left text-sm font-semibold text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              key={item}
              onClick={() => {
                setOpen(false);
                if (item === 'Analytics') {
                  router.push('/analytics');
                } else if (item === 'Achievements') {
                  router.push('/achievements');
                } else {
                  onPastTicketsOpen();
                }
              }}
              role="menuitem"
              type="button"
            >
              {item}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
