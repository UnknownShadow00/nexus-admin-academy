import React from 'react';
import {
  REMOTE_DESKTOP_APP_IDS,
  TOOL_CATALOG,
  TicketCategory,
} from '@service-desk/shared';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { WORKSTATION_APP_REGISTRY } from './app-registry';
import { CredentialManagerApp } from './apps/CredentialManagerApp';
import { MapNetworkDriveDialog } from './apps/MapNetworkDriveDialog';
import { WindowFrame } from './WindowFrame';
import { ACCOUNT_SIGN_IN_TESTS } from '../AccountSignInTestDialog';
import { SuggestedTools } from '../SuggestedTools';

describe('workstation UI contracts', () => {
  it('registers every desktop app including Credential Manager', () => {
    expect(Object.keys(WORKSTATION_APP_REGISTRY).sort()).toEqual(
      [...REMOTE_DESKTOP_APP_IDS].sort(),
    );
    expect(WORKSTATION_APP_REGISTRY['credential-manager'].label).toBe(
      'Credential Manager',
    );
  });

  it('renders credential metadata without any password control', () => {
    const markup = renderToStaticMarkup(
      <CredentialManagerApp
        credentials={[
          {
            id: 'credential-share',
            target: 'files.nexus.internal',
            username: 'NEXUS\\student.user',
            type: 'domain-password',
            persistence: 'local-machine',
            createdAt: '2026-07-30T10:30:00.000Z',
          },
        ]}
        onAdd={() => ({ success: true, rejectReason: null })}
        onDelete={vi.fn()}
      />,
    );

    expect(markup).toContain('Credential Manager');
    expect(markup).toContain('files.nexus.internal');
    expect(markup).toContain('Passwords are never entered');
    expect(markup).not.toContain('type="password"');
  });

  it('renders a complete Map Network Drive dialog', () => {
    const markup = renderToStaticMarkup(
      <MapNetworkDriveDialog
        credentials={[]}
        currentMapping={null}
        onCancel={vi.fn()}
        onMap={() => ({ success: true, rejectReason: null })}
      />,
    );

    expect(markup).toContain('role="dialog"');
    expect(markup).toContain('Map Network Drive');
    expect(markup).toContain('Reconnect at sign-in');
    expect(markup).toContain('Stored Windows credential');
    expect(markup).toContain('server');
    expect(markup).toContain('share');
  });

  it('renders persistent, keyboard-described window controls', () => {
    const markup = renderToStaticMarkup(
      <WindowFrame
        appId="explorer"
        focused
        onClose={vi.fn()}
        onFocus={vi.fn()}
        onMinimize={vi.fn()}
        onMove={vi.fn()}
        onToggleMaximize={vi.fn()}
        windowState={{
          appId: 'explorer',
          open: true,
          minimized: false,
          maximized: false,
          bounds: { x: 40, y: 32, width: 760, height: 520 },
          restoreBounds: null,
          zIndex: 10,
        }}
      >
        Explorer contents
      </WindowFrame>,
    );

    expect(markup).toContain('File Explorer window');
    expect(markup).toContain('Hold Alt and use arrow keys');
    expect(markup).toContain('Minimize File Explorer');
    expect(markup).toContain('Maximize File Explorer');
    expect(markup).toContain('Close File Explorer');
  });

  it('keeps assessment tools complete without revealing the solution subset', () => {
    const markup = renderToStaticMarkup(
      <SuggestedTools
        experienceMode="assessment"
        ticketCategory={TicketCategory.Access}
        ticketId="INC2511"
        toolSlugs={['directory', 'company-chat']}
      />,
    );

    expect(markup).toContain('Available technician tools');
    expect(markup).not.toContain('Recommended places to start');
    for (const tool of TOOL_CATALOG) {
      expect(markup).toContain(tool.menuLabel);
    }
  });

  it('uses case-specific, secret-free original sign-in checkpoints', () => {
    expect(ACCOUNT_SIGN_IN_TESTS['account-locked'].result).toContain(
      'account-lock message did not recur',
    );
    expect(ACCOUNT_SIGN_IN_TESTS['password-expired'].result).toContain(
      'required password-change screen',
    );
    expect(ACCOUNT_SIGN_IN_TESTS['mfa-factor-unavailable'].result).toContain(
      'MFA re-registration prompt',
    );
    expect(JSON.stringify(ACCOUNT_SIGN_IN_TESTS)).toContain(
      'No credential value was exposed',
    );
  });
});
