'use client';

import * as RadixTabs from '@radix-ui/react-tabs';
import type { ComponentProps } from 'react';

import { cn } from './lib/cn';

export type TabsProps = ComponentProps<typeof RadixTabs.Root>;

export function Tabs({ className, ...props }: TabsProps) {
  return <RadixTabs.Root className={cn('sd-tabs', className)} {...props} />;
}

export function TabsList({
  className,
  ...props
}: ComponentProps<typeof RadixTabs.List>) {
  return (
    <RadixTabs.List
      className={cn('sd-tabs-list flex border-b border-zinc-700', className)}
      {...props}
    />
  );
}

export function TabsTrigger({
  className,
  ...props
}: ComponentProps<typeof RadixTabs.Trigger>) {
  return (
    <RadixTabs.Trigger
      className={cn(
        'sd-tabs-trigger sd-focus-ring -mb-px min-h-10 border-b-2 border-transparent px-3 py-2.5 text-xs font-extrabold uppercase text-zinc-500 transition-colors hover:text-zinc-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-400 data-[state=active]:border-sky-400 data-[state=active]:text-sky-300',
        className,
      )}
      {...props}
    />
  );
}

export function TabsContent({
  className,
  ...props
}: ComponentProps<typeof RadixTabs.Content>) {
  return (
    <RadixTabs.Content
      className={cn(
        'sd-tabs-content py-4 text-sm text-zinc-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400',
        className,
      )}
      {...props}
    />
  );
}
