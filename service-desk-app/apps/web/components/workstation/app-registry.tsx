import type { RemoteDesktopAppId } from '@service-desk/shared';
import {
  IconAppWindow,
  IconFolder,
  IconKey,
  IconMail,
  IconMessageCircle,
  IconRefresh,
  IconSettings,
  IconShieldCheck,
  IconTerminal2,
  IconTrash,
  IconWorld,
} from '@tabler/icons-react';

export interface WorkstationAppMetadata {
  label: string;
  Icon: typeof IconAppWindow;
  tint: string;
}

export const WORKSTATION_APP_REGISTRY: Record<
  RemoteDesktopAppId,
  WorkstationAppMetadata
> = {
  explorer: {
    label: 'File Explorer',
    Icon: IconFolder,
    tint: 'text-amber-300',
  },
  vpn: {
    label: 'VPN Client',
    Icon: IconShieldCheck,
    tint: 'text-emerald-300',
  },
  settings: {
    label: 'Settings',
    Icon: IconSettings,
    tint: 'text-zinc-100',
  },
  services: {
    label: 'Services',
    Icon: IconTerminal2,
    tint: 'text-orange-300',
  },
  chat: {
    label: 'Company Chat',
    Icon: IconMessageCircle,
    tint: 'text-sky-300',
  },
  mail: { label: 'Mail', Icon: IconMail, tint: 'text-blue-300' },
  browser: { label: 'Web Browser', Icon: IconWorld, tint: 'text-cyan-300' },
  updates: {
    label: 'System Update',
    Icon: IconRefresh,
    tint: 'text-violet-300',
  },
  trash: { label: 'Recycle Bin', Icon: IconTrash, tint: 'text-zinc-300' },
  system: {
    label: 'System Information',
    Icon: IconTerminal2,
    tint: 'text-lime-300',
  },
  terminal: {
    label: 'Command Prompt',
    Icon: IconTerminal2,
    tint: 'text-emerald-300',
  },
  'credential-manager': {
    label: 'Credential Manager',
    Icon: IconKey,
    tint: 'text-amber-200',
  },
};
