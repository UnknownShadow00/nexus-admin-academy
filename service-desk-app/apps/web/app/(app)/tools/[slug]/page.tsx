import { TOOL_CATALOG, getToolBySlug } from '@service-desk/shared';
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { Suspense } from 'react';

import { CompanyChatTool } from '../../../../components/CompanyChatTool';
import { ComputerDeploymentTool } from '../../../../components/ComputerDeploymentTool';
import { AssetManagementTool } from '../../../../components/AssetManagementTool';
import { DirectoryTool } from '../../../../components/DirectoryTool';
import { DocumentationTool } from '../../../../components/DocumentationTool';
import { PcShelfTool } from '../../../../components/PcShelfTool';
import { RemoteDesktopTool } from '../../../../components/RemoteDesktopTool';
import { ServerRoomTool } from '../../../../components/ServerRoomTool';
import { ShippingManagerTool } from '../../../../components/ShippingManagerTool';

interface ToolPageProps {
  params: Promise<{ slug: string }>;
}

export function generateStaticParams() {
  return TOOL_CATALOG.map((tool) => ({ slug: tool.slug }));
}

export async function generateMetadata({
  params,
}: ToolPageProps): Promise<Metadata> {
  const { slug } = await params;
  const tool = getToolBySlug(slug);

  return {
    title: tool ? `${tool.displayName} | Nexus Service Desk` : 'Tool not found',
  };
}

export default async function ToolPage({ params }: ToolPageProps) {
  const { slug } = await params;
  const tool = getToolBySlug(slug);

  if (!tool) {
    notFound();
  }

  if (tool.slug === 'directory') {
    return <DirectoryTool />;
  }

  if (tool.slug === 'documentation') {
    return (
      <Suspense fallback={<ToolLoadingState label="documentation" />}>
        <DocumentationTool />
      </Suspense>
    );
  }

  if (tool.slug === 'company-chat') {
    return (
      <Suspense fallback={<ToolLoadingState label="company chat" />}>
        <CompanyChatTool />
      </Suspense>
    );
  }

  if (tool.slug === 'asset-management') {
    return <AssetManagementTool />;
  }

  if (tool.slug === 'pc-shelf') {
    return <PcShelfTool />;
  }

  if (tool.slug === 'server-room') {
    return <ServerRoomTool />;
  }

  if (tool.slug === 'remote-desktop') {
    return <RemoteDesktopTool />;
  }

  if (tool.slug === 'computer-deployment') {
    return <ComputerDeploymentTool />;
  }

  if (tool.slug === 'shipping-manager') {
    return <ShippingManagerTool />;
  }

  return notFound();
}

function ToolLoadingState({ label }: { label: string }) {
  return (
    <div
      className="mx-auto min-h-72 w-full max-w-5xl animate-pulse rounded-md border border-zinc-800 bg-zinc-900"
      role="status"
    >
      <span className="sr-only">Loading {label}…</span>
    </div>
  );
}
