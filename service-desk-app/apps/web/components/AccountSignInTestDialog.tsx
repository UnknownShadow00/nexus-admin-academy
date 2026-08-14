'use client';

import type { DirectoryUserTemplate } from '@service-desk/shared';
import { Badge, Button, Modal } from '@service-desk/ui';
import { IconLogin2, IconShieldCheck } from '@tabler/icons-react';
import { useState } from 'react';

type VerificationCheck =
  | 'account-unlocked'
  | 'temporary-password-issued'
  | 'mfa-reregistration-ready';

export const ACCOUNT_SIGN_IN_TESTS: Readonly<
  Record<
    NonNullable<DirectoryUserTemplate['supportIssue']>,
    {
      begin: string;
      check: VerificationCheck;
      expected: string;
      result: string;
    }
  >
> = {
  'account-locked': {
    begin: 'Attempt clean account sign-in',
    check: 'account-unlocked',
    expected: 'The previous account-lock message must not recur.',
    result:
      'The simulated sign-in was accepted. The account-lock message did not recur.',
  },
  'password-expired': {
    begin: 'Begin temporary-credential handoff',
    check: 'temporary-password-issued',
    expected:
      'The temporary credential must lead to a required password-change step.',
    result:
      'The temporary credential was accepted and the required password-change screen appeared. No credential value was exposed.',
  },
  'mfa-factor-unavailable': {
    begin: 'Test sign-in through second factor',
    check: 'mfa-reregistration-ready',
    expected:
      'Primary authentication must succeed and the user must reach MFA re-registration.',
    result:
      'Primary authentication succeeded and the simulated sign-in reached the MFA re-registration prompt.',
  },
};

interface AccountSignInTestDialogProps {
  onConfirm: (check: VerificationCheck) => void;
  user: DirectoryUserTemplate;
}

export function AccountSignInTestDialog({
  onConfirm,
  user,
}: AccountSignInTestDialogProps) {
  const [open, setOpen] = useState(false);
  const [testStarted, setTestStarted] = useState(false);
  const issue = user.supportIssue;

  if (!issue) return null;

  const test = ACCOUNT_SIGN_IN_TESTS[issue];

  return (
    <Modal
      description="Retest the requester’s original sign-in path after remediation."
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
        if (!nextOpen) setTestStarted(false);
      }}
      open={open}
      title="Simulated sign-in test"
      trigger={
        <Button disabled={user.accessVerified} variant="soft">
          <IconLogin2 aria-hidden="true" className="h-4 w-4" />
          {user.accessVerified
            ? 'Sign-in path verified'
            : 'Test original sign-in'}
        </Button>
      }
    >
      <div className="space-y-4">
        <div className="grid gap-3 rounded-sm border border-zinc-700 bg-zinc-950/60 p-4 sm:grid-cols-2">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-zinc-500">
              Simulated user
            </p>
            <p className="mt-1 text-sm font-bold text-zinc-100">
              {user.fullName}
            </p>
            <p className="text-xs text-zinc-400">@{user.username}</p>
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-zinc-500">
              Credential handling
            </p>
            <Badge className="mt-1" variant="success">
              Training-safe · no secrets
            </Badge>
          </div>
        </div>

        {!testStarted ? (
          <div>
            <p className="text-sm leading-relaxed text-zinc-300">
              Expected checkpoint: {test.expected}
            </p>
            <Button
              className="mt-4 w-full justify-center"
              onClick={() => setTestStarted(true)}
              variant="primary"
            >
              <IconLogin2 aria-hidden="true" className="h-4 w-4" />
              {test.begin}
            </Button>
          </div>
        ) : (
          <div className="rounded-sm border border-emerald-500/30 bg-emerald-500/10 p-4">
            <div className="flex items-start gap-3">
              <IconShieldCheck
                aria-hidden="true"
                className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400"
              />
              <div>
                <p className="text-sm font-bold text-emerald-300">
                  Checkpoint reached
                </p>
                <p className="mt-1 text-sm leading-relaxed text-zinc-300">
                  {test.result}
                </p>
              </div>
            </div>
            <Button
              className="mt-4 w-full justify-center"
              onClick={() => {
                onConfirm(test.check);
                setOpen(false);
                setTestStarted(false);
              }}
              variant="primary"
            >
              Record successful sign-in test
            </Button>
          </div>
        )}
      </div>
    </Modal>
  );
}
