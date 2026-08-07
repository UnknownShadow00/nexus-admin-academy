'use client';

import { IconMessages, IconTrophy } from '@tabler/icons-react';
import { Button } from '@service-desk/ui';
import { useRouter } from 'next/navigation';

import { useCompanyChatSession } from './TicketSessionProvider';

interface NavClusterProps {
  activePath: string;
  onLeaderboardOpen: () => void;
}

export function NavCluster({ activePath, onLeaderboardOpen }: NavClusterProps) {
  const router = useRouter();
  const { unreadThreadCount } = useCompanyChatSession();

  return (
    <nav
      aria-label="Support actions"
      className="flex min-w-max items-center gap-0.5 pr-1 sm:gap-1"
    >
      <Button
        aria-current={activePath === '/tools/company-chat' ? 'page' : undefined}
        aria-label={
          unreadThreadCount > 0
            ? `Company Chat, ${unreadThreadCount} unread ${
                unreadThreadCount === 1 ? 'conversation' : 'conversations'
              }`
            : 'Company Chat'
        }
        className="relative px-2"
        onClick={() => router.push('/tools/company-chat')}
        variant="ghost"
      >
        <IconMessages aria-hidden="true" className="h-4 w-4" />
        {unreadThreadCount > 0 ? (
          <span
            aria-hidden="true"
            className="absolute right-0.5 top-0.5 inline-flex min-h-4 min-w-4 items-center justify-center rounded-full border border-zinc-900 bg-sky-400 px-1 text-[9px] font-black leading-none text-zinc-950"
          >
            {unreadThreadCount > 9 ? '9+' : unreadThreadCount}
          </span>
        ) : null}
      </Button>
      <Button
        aria-label="Leaderboard"
        className="px-2 text-amber-400 hover:text-amber-300"
        onClick={onLeaderboardOpen}
        variant="ghost"
      >
        <IconTrophy aria-hidden="true" className="h-4 w-4" />
      </Button>
    </nav>
  );
}
