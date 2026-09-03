import { TOOL_CATALOG, getToolBySlug } from '@service-desk/shared';
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { renderTool } from '../../../../components/tool-registry';

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

  return renderTool(tool.slug) ?? notFound();
}
