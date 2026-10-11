'use client';

import {
  IconBook,
  IconChartBar,
  IconHome,
  IconMoon,
  IconSun,
  IconHeadset,
  IconSettings,
} from '@tabler/icons-react';
import { usePathname } from 'next/navigation';
import { useEffect, useState, type ReactNode } from 'react';

import { Header } from './Header';
import { AcademySearch } from './AcademySearch';
import { Footer } from './Footer';
import { MainContainer } from './MainContainer';
import { useSessionIdentity } from './TicketSessionProvider';
import { useNexusReturnTarget } from './useNexusReturnTarget';

/** Academy assets are served by the existing same-origin Academy application. */
const ASSETS = '/academy/';

export function AcademyFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const identity = useSessionIdentity();
  const returnTarget = useNexusReturnTarget();
  const [dark, setDark] = useState(true);
  const learner =
    !identity.isAdmin &&
    !identity.isMentor &&
    !pathname.startsWith('/admin') &&
    process.env.NEXT_PUBLIC_NEXUS_INTEGRATION === '1';
  useEffect(() => {
    if (!learner) return;
    // Portal dialogs inherit the learner palette, including the close/escalate forms.
    document.documentElement.dataset.academyServiceDesk = 'true';
    return () => {
      delete document.documentElement.dataset.academyServiceDesk;
    };
  }, [learner]);
  useEffect(() => {
    setDark(document.documentElement.dataset.theme !== 'light');
  }, []);
  function toggleTheme() {
    const next = document.documentElement.dataset.theme !== 'dark';
    document.documentElement.dataset.theme = next ? 'dark' : 'light';
    try {
      localStorage.setItem('theme', next ? 'dark' : 'light');
    } catch {
      /* Storage is optional. */
    }
    setDark(next);
  }

  // Preserve the operational/admin console and standalone simulator appearance.
  if (
    identity.isAdmin ||
    identity.isMentor ||
    pathname.startsWith('/admin') ||
    process.env.NEXT_PUBLIC_NEXUS_INTEGRATION !== '1'
  ) {
    return (
      <div className="flex min-h-screen w-full max-w-full flex-col overflow-x-hidden bg-surface text-text">
        <Header currentPath={pathname} />
        <MainContainer>{children}</MainContainer>
        <Footer />
      </div>
    );
  }

  const nav = [
    { href: '/', label: 'Today', Icon: IconHome },
    // Use the validated curriculum return target rather than assume V2 enrollment.
    {
      href: returnTarget?.href ?? '/learning-path',
      label: 'My Course',
      Icon: IconBook,
    },
    { href: '/service-desk', label: 'Service Desk', Icon: IconHeadset },
    { href: '/progress', label: 'Progress', Icon: IconChartBar },
  ];
  return (
    <div className="sd-academy">
      <a className="sd-academy-skip" href="#service-desk-content">
        Skip to ticket workspace
      </a>
      <aside className="sd-academy-sidebar" aria-label="Learner sidebar">
        <a
          className="sd-academy-brand"
          href="/"
          aria-label="Nexus Academy home"
        >
          <img src={`${ASSETS}nexus-mark.svg`} alt="" />
          <span>
            <strong>NEXUS</strong>
            <small>ACADEMY</small>
          </span>
        </a>
        <nav aria-label="Academy navigation">
          {nav.map(({ href, label, Icon }) => (
            <a
              href={href}
              key={label}
              aria-current={label === 'Service Desk' ? 'page' : undefined}
            >
              <Icon aria-hidden="true" size={20} />
              <span>{label}</span>
            </a>
          ))}
          <button type="button" onClick={toggleTheme}>
            <IconSettings aria-hidden="true" size={20} />
            Theme settings
          </button>
        </nav>
        <div className="sd-academy-sidebar-art" aria-hidden="true">
          <img src={`${ASSETS}academy-tower-refined.webp`} alt="" />
          <p>
            “Discipline today,
            <br />
            stronger tomorrow.”
          </p>
        </div>
      </aside>
      <div className="sd-academy-body">
        <div className="sd-academy-topbar">
          <AcademySearch />
          <Header currentPath={pathname} />
          <button
            className="sd-academy-theme"
            onClick={toggleTheme}
            type="button"
            aria-label="Toggle dark mode"
            aria-pressed={dark}
          >
            {dark ? (
              <IconSun size={19} aria-hidden="true" />
            ) : (
              <IconMoon size={19} aria-hidden="true" />
            )}
          </button>
        </div>
        <main
          id="service-desk-content"
          className="sd-academy-content"
          tabIndex={-1}
        >
          {children}
        </main>
        <Footer />
      </div>
      <nav
        className="sd-academy-mobile-nav"
        aria-label="Academy mobile navigation"
      >
        {nav.map(({ href, label, Icon }) => (
          <a
            href={href}
            key={label}
            aria-current={label === 'Service Desk' ? 'page' : undefined}
          >
            <Icon size={20} aria-hidden="true" />
            <span>
              {label === 'Service Desk'
                ? 'Desk'
                : label === 'My Course'
                  ? 'Course'
                  : label}
            </span>
          </a>
        ))}
      </nav>
    </div>
  );
}
