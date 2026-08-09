import type { Metadata } from 'next';
import type { ReactNode } from 'react';

import './globals.css';

export const metadata: Metadata = {
  title: 'Nexus Service Desk',
  description: 'A hands-on service desk training console.',
};

const themeScript = `
  try {
    const savedTheme = localStorage.getItem('theme');
    document.documentElement.dataset.theme = savedTheme === 'light' ? 'light' : 'dark';
  } catch (_) {
    document.documentElement.dataset.theme = 'dark';
  }
`;

const fontScript = `
  document.getElementById('service-desk-fonts')?.addEventListener('load', function () {
    this.media = 'all';
  });
`;

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html data-theme="dark" lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        <link href="https://fonts.googleapis.com" rel="preconnect" />
        <link
          crossOrigin="anonymous"
          href="https://fonts.gstatic.com"
          rel="preconnect"
        />
        <link
          id="service-desk-fonts"
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Orbitron:wght@400;500;600;700;800;900&family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&display=swap"
          media="print"
          rel="stylesheet"
          suppressHydrationWarning
        />
        <script dangerouslySetInnerHTML={{ __html: fontScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
