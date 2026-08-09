import type { ReactNode } from 'react';

import { ApplicationShell } from '../../components/ApplicationShell';

export default function AuthenticatedAppLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return <ApplicationShell>{children}</ApplicationShell>;
}
