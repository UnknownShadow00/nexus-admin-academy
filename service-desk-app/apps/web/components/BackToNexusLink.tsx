import React from 'react';

interface BackToNexusLinkProps {
  href?: string;
  label?: string;
}

// href/label default to the generic Nexus destination. Header passes a
// contextual "Back to Week N" target when useNexusReturnTarget finds one.
export function BackToNexusLink({
  href = '/',
  label = 'Back to Nexus',
}: BackToNexusLinkProps) {
  const shortLabel = label.replace(/^Back to /, '');
  return (
    <a
      aria-label={label}
      className="sd-focus-ring inline-flex min-h-9 shrink-0 items-center rounded-sm border border-accent/30 bg-accent/10 px-2 text-xs font-bold text-accent hover:bg-accent/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus sm:px-3 sm:text-sm"
      href={href}
    >
      <span aria-hidden="true">←</span>
      <span className="ml-1 hidden sm:inline">{label}</span>
      <span className="ml-1 sm:hidden">{shortLabel}</span>
    </a>
  );
}
