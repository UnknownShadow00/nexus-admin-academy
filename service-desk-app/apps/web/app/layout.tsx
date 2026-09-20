import type { Metadata } from 'next';
import type { ReactNode } from 'react';

import './globals.css';

export const metadata: Metadata = {
  title: 'Nexus Service Desk',
  description: 'A hands-on service desk training console.',
};

const themeScript = `
  (function () {
    var root = document.documentElement;
    var savedTheme = null;
    try { savedTheme = localStorage.getItem('theme'); } catch (_) {}
    if (savedTheme === 'light' || savedTheme === 'dark') {
      root.dataset.theme = savedTheme;
      return;
    }
    try {
      root.dataset.theme = window.matchMedia('(prefers-color-scheme: light)').matches
        ? 'light'
        : 'dark';
    } catch (_) {
      root.dataset.theme = 'dark';
    }
  })();
`;

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
