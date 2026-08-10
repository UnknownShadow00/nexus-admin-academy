'use client';

import { IconDeviceDesktop, IconHome } from '@tabler/icons-react';
import { Button } from '@service-desk/ui';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { NavCluster } from './NavCluster';
import { BackToNexusLink } from './BackToNexusLink';
import { LeaderboardModal } from './LeaderboardModal';
import { PastTicketsModal } from './PastTicketsModal';
import { ProfileMenuTrigger } from './ProfileMenuTrigger';
import { useAttemptScore, useSyncStatus } from './TicketSessionProvider';
import { ToolsPanel } from './ToolsPanel';

interface HeaderProps {
  currentPath: string;
}

export function Header({ currentPath }: HeaderProps) {
  const { pointsTotal } = useAttemptScore();
  const syncStatus = useSyncStatus();
  const [leaderboardOpen, setLeaderboardOpen] = useState(false);
  const [pastTicketsOpen, setPastTicketsOpen] = useState(false);
  const router = useRouter();
  const onToolPage = currentPath.startsWith('/tools/');

  return (
    <>
      <header className="border-b border-zinc-700 bg-zinc-900">
        <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-2 gap-y-1 px-2 pb-1 pt-2 sm:px-3 sm:pb-2 lg:grid-cols-[auto_minmax(0,1fr)_auto] lg:gap-3 lg:px-5 lg:py-2">
          <div className="col-start-1 row-start-1 flex min-w-0 items-center gap-2">
            <Link
              aria-current={currentPath === '/' ? 'page' : undefined}
              aria-label="Nexus Service Desk Dashboard"
              className="sd-focus-ring flex min-w-0 items-center gap-2 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
              href="/"
            >
              <span className="flex h-8 w-9 shrink-0 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 text-sky-300 md:h-10 md:w-11">
                <IconDeviceDesktop aria-hidden="true" className="h-5 w-5" />
              </span>
              <span className="hidden min-w-0 sm:block">
                <span className="block truncate font-display text-sm font-bold text-zinc-100">
                  Nexus Desk
                </span>
                <span className="block text-[10px] font-bold uppercase text-zinc-500">
                  Training Console
                </span>
              </span>
            </Link>
            <BackToNexusLink />
            {onToolPage ? (
              <Button
                className="hidden px-2 text-xs xl:inline-flex"
                onClick={() => router.push('/')}
                variant="ghost"
              >
                <IconHome aria-hidden="true" className="h-4 w-4" />
                Dashboard
              </Button>
            ) : null}
          </div>

          <div className="col-span-2 row-start-2 min-w-0 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden lg:col-span-1 lg:col-start-2 lg:row-start-1">
            <div className="flex min-w-max items-center">
              <ToolsPanel activePath={currentPath} />
              <span
                aria-hidden="true"
                className="mx-1.5 h-5 w-px bg-zinc-700/50 sm:mx-2.5"
              />
              <NavCluster
                activePath={currentPath}
                onLeaderboardOpen={() => setLeaderboardOpen(true)}
              />
            </div>
          </div>

          <div className="col-start-2 row-start-1 flex min-w-0 items-center justify-self-end gap-2 sm:gap-3 lg:col-start-3">
            {syncStatus !== 'saved' ? (
              <span
                className={`hidden rounded-sm px-2 py-1 text-[10px] font-bold uppercase sm:inline ${syncStatus === 'problem' ? 'bg-amber-400/15 text-amber-300' : 'bg-sky-400/10 text-sky-300'}`}
                role="status"
              >
                {syncStatus === 'problem' ? 'Sync problem — retrying' : 'Saving…'}
              </span>
            ) : null}
            <div
              aria-label="Account usage"
              className="hidden items-center gap-3 border-l border-zinc-700/50 pl-3 md:flex"
            >
              <div className="text-center leading-none">
                <span className="block text-base font-bold tabular-nums text-zinc-100">
                  {pointsTotal}
                </span>
                <span className="mt-1 block text-[9px] font-bold uppercase tracking-wide text-zinc-500">
                  Points
                </span>
              </div>
            </div>
            <ProfileMenuTrigger
              onPastTicketsOpen={() => setPastTicketsOpen(true)}
            />
          </div>
        </div>
      </header>
      <LeaderboardModal
        onOpenChange={setLeaderboardOpen}
        open={leaderboardOpen}
      />
      <PastTicketsModal
        onOpenChange={setPastTicketsOpen}
        open={pastTicketsOpen}
      />
    </>
  );
}
