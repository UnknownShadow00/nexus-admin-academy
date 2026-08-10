import React from 'react';

export function BackToNexusLink() {
  return (
    <a
      aria-label="Back to Nexus"
      className="sd-focus-ring inline-flex min-h-9 shrink-0 items-center rounded-sm border border-sky-400/30 bg-sky-400/10 px-2 text-xs font-bold text-sky-200 hover:bg-sky-400/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 sm:px-3 sm:text-sm"
      href="/"
    >
      <span aria-hidden="true">←</span>
      <span className="ml-1 hidden sm:inline">Back to Nexus</span>
      <span className="ml-1 sm:hidden">Nexus</span>
    </a>
  );
}
