import {
  IconBooks,
  IconDeviceDesktop,
  IconDevicesPc,
  IconDisc,
  IconMessages,
  IconPackage,
  IconServer,
  IconTruckDelivery,
  IconUsers,
} from '@tabler/icons-react';
import type { ToolSlug } from '@service-desk/shared';

type ToolIcon = typeof IconUsers;

export const TOOL_ICONS: Record<ToolSlug, ToolIcon> = {
  'asset-management': IconPackage,
  'company-chat': IconMessages,
  'computer-deployment': IconDisc,
  directory: IconUsers,
  documentation: IconBooks,
  'pc-shelf': IconDevicesPc,
  'remote-desktop': IconDeviceDesktop,
  'server-room': IconServer,
  'shipping-manager': IconTruckDelivery,
};
