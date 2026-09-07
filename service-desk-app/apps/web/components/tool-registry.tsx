import React, { Suspense, type ReactNode } from 'react';

import { AssetManagementTool } from './AssetManagementTool';
import { CompanyChatTool } from './CompanyChatTool';
import { ComputerDeploymentTool } from './ComputerDeploymentTool';
import { DeviceManagementTool } from './DeviceManagementTool';
import { DirectoryTool } from './DirectoryTool';
import { DocumentationTool } from './DocumentationTool';
import { PcShelfTool } from './PcShelfTool';
import { RemoteDesktopTool } from './RemoteDesktopTool';
import { ServerRoomTool } from './ServerRoomTool';
import { ShippingManagerTool } from './ShippingManagerTool';

export function renderTool(slug: string, activeTicketId?: string): ReactNode | null {
  switch (slug) {
    case 'directory':
      return <DirectoryTool />;
    case 'documentation':
      return (
        <Suspense fallback={<ToolLoadingState label="documentation" />}>
          <DocumentationTool />
        </Suspense>
      );
    case 'device-management':
      return (
        <Suspense fallback={<ToolLoadingState label="device management" />}>
          <DeviceManagementTool />
        </Suspense>
      );
    case 'company-chat':
      return (
        <Suspense fallback={<ToolLoadingState label="company chat" />}>
          <CompanyChatTool />
        </Suspense>
      );
    case 'asset-management':
      return <AssetManagementTool />;
    case 'pc-shelf':
      return <PcShelfTool />;
    case 'server-room':
      return <ServerRoomTool />;
    case 'remote-desktop':
      return <RemoteDesktopTool activeTicketId={activeTicketId} />;
    case 'computer-deployment':
      return <ComputerDeploymentTool />;
    case 'shipping-manager':
      return <ShippingManagerTool />;
    default:
      return null;
  }
}

export function ToolLoadingState({ label }: { label: string }) {
  return (
    <div
      className="mx-auto min-h-72 w-full max-w-5xl animate-pulse rounded-md border border-border bg-surface-raised"
      role="status"
    >
      <span className="sr-only">Loading {label}…</span>
    </div>
  );
}
