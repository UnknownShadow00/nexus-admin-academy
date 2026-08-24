export const TOOL_CATEGORIES = [
  'infrastructure',
  'knowledge',
  'management',
] as const;

export type ToolCategory = (typeof TOOL_CATEGORIES)[number];

export interface ToolDefinition {
  category?: ToolCategory;
  description: string;
  displayName: string;
  menuLabel: string;
  path: `/tools/${string}`;
  slug: string;
}

export const TOOL_CATALOG = [
  {
    category: 'infrastructure',
    description: 'Find people, teams, and account records in one workspace.',
    displayName: 'Directory',
    menuLabel: 'Directory',
    path: '/tools/directory',
    slug: 'directory',
  },
  {
    category: 'infrastructure',
    description:
      'Inspect the systems that keep the practice environment online.',
    displayName: 'Server Room',
    menuLabel: 'Server Room',
    path: '/tools/server-room',
    slug: 'server-room',
  },
  {
    category: 'infrastructure',
    description: 'Connect to a workstation when hands-on support is required.',
    displayName: 'Remote Desktop',
    menuLabel: 'Remote Desktop',
    path: '/tools/remote-desktop',
    slug: 'remote-desktop',
  },
  {
    category: 'infrastructure',
    description: 'Prepare operating systems and software for newly issued PCs.',
    displayName: 'Computer Deployment',
    menuLabel: 'Computer Deployment',
    path: '/tools/computer-deployment',
    slug: 'computer-deployment',
  },
  {
    category: 'infrastructure',
    description: 'Review the computers available for support and assignment.',
    displayName: 'PC Shelf',
    menuLabel: 'PC Shelf',
    path: '/tools/pc-shelf',
    slug: 'pc-shelf',
  },
  {
    category: 'knowledge',
    description: 'Search the support guidance used to resolve common requests.',
    displayName: 'Documentation',
    menuLabel: 'Documentation',
    path: '/tools/documentation',
    slug: 'documentation',
  },
  {
    category: 'management',
    description:
      'Inspect managed endpoint records and perform narrowly authorized device actions.',
    displayName: 'Device Management',
    menuLabel: 'Device Management',
    path: '/tools/device-management',
    slug: 'device-management',
  },
  {
    category: 'management',
    description:
      'Track equipment ownership and its place in the device lifecycle.',
    displayName: 'Asset Management',
    menuLabel: 'Asset Management',
    path: '/tools/asset-management',
    slug: 'asset-management',
  },
  {
    category: 'management',
    description:
      'Coordinate outbound equipment without losing delivery context.',
    displayName: 'Shipping Manager',
    menuLabel: 'Ship Manager',
    path: '/tools/shipping-manager',
    slug: 'shipping-manager',
  },
  {
    description:
      'Keep support conversations together with the work they concern.',
    displayName: 'Company Chat',
    menuLabel: 'Company Chat',
    path: '/tools/company-chat',
    slug: 'company-chat',
  },
] as const satisfies readonly ToolDefinition[];

export type ToolSlug = (typeof TOOL_CATALOG)[number]['slug'];

export function getToolBySlug(slug: string) {
  return TOOL_CATALOG.find((tool) => tool.slug === slug);
}

export function getToolsByCategory(category: ToolCategory) {
  return TOOL_CATALOG.filter(
    (tool) => 'category' in tool && tool.category === category,
  );
}
