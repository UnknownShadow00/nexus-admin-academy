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
    tint: 'text-warning',
  },
  vpn: {
    label: 'VPN Client',
    Icon: IconShieldCheck,
    tint: 'text-success',
  },
  settings: {
    label: 'Settings',
    Icon: IconSettings,
    tint: 'text-text',
  },
  services: {
    label: 'Services',
    Icon: IconTerminal2,
    tint: 'text-orange-300',
  },
  chat: {
    label: 'Company Chat',
    Icon: IconMessageCircle,
    tint: 'text-accent',
  },
  mail: { label: 'Mail', Icon: IconMail, tint: 'text-accent' },
  browser: { label: 'Web Browser', Icon: IconWorld, tint: 'text-cyan-300' },
  updates: {
    label: 'System Update',
    Icon: IconRefresh,
    tint: 'text-violet-300',
  },
  trash: { label: 'Recycle Bin', Icon: IconTrash, tint: 'text-text' },
  system: {
    label: 'System Information',
    Icon: IconTerminal2,
    tint: 'text-lime-300',
  },
  terminal: {
    label: 'Command Prompt',
    Icon: IconTerminal2,
    tint: 'text-success',
  },
  'credential-manager': {
    label: 'Credential Manager',
    Icon: IconKey,
    tint: 'text-warning',
  },
};
