'use client';

import {
  DIRECTORY_GROUP_NAMES,
  type DirectoryUserTemplate,
} from '@service-desk/shared';
import type { ActionEvent } from '@service-desk/simulation-engine';
import { Badge, Button, Card, CardHeader, Select } from '@service-desk/ui';
import {
  IconDeviceLaptop,
  IconLockOpen,
  IconShieldLock,
  IconUserCheck,
  IconUsersGroup,
  IconX,
} from '@tabler/icons-react';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { AccountSignInTestDialog } from './AccountSignInTestDialog';
import { DirectoryActionDialog } from './DirectoryActionDialog';
import { PasswordResetDialog } from './PasswordResetDialog';
import { useDirectorySession } from './TicketSessionProvider';

interface DirectoryUserDetailProps {
  onAction: (event: ActionEvent) => void;
  user: DirectoryUserTemplate;
}

export function DirectoryUserDetail({
  onAction,
  user,
}: DirectoryUserDetailProps) {
  const {
    disableAccount,
    enableAccount,
    inspectAccount,
    recordDiagnosis,
    resetMfa,
    resetPassword,
    unlockAccount,
    testPrimaryAuth,
    updateGroups,
    verifyAccess,
    verifyIdentity,
  } = useDirectorySession();
  const [groupToAdd, setGroupToAdd] = useState('');
  const [diagnosis, setDiagnosis] = useState('');
  const isStarterAccountCase = user.supportIssue !== null;
  const remediationComplete =
    (user.supportIssue === 'account-locked' && !user.locked) ||
    (user.supportIssue === 'password-expired' &&
      user.passwordState === 'temporary') ||
    (user.supportIssue === 'mfa-factor-unavailable' &&
      user.mfaFactorStatus === 'reset-ready');
  const ticketBySupportIssue = {
    'account-locked': 'INC2511',
    'password-expired': 'INC2512',
    'mfa-factor-unavailable': 'INC2513',
  } as const;
  const supportTicketId = user.supportIssue
    ? ticketBySupportIssue[user.supportIssue]
    : null;
  const availableGroups = useMemo(
    () => DIRECTORY_GROUP_NAMES.filter((group) => !user.groups.includes(group)),
    [user.groups],
  );

  useEffect(() => {
    if (groupToAdd && !availableGroups.some((group) => group === groupToAdd)) {
      setGroupToAdd('');
    }
  }, [availableGroups, groupToAdd]);

  return (
    <aside aria-labelledby="directory-user-name" className="space-y-4">
      <Card>
        <CardHeader meta={`@${user.username}`} title="User profile" />
        <div className="p-4">
          <h2
            className="font-display text-xl font-bold text-zinc-100"
            id="directory-user-name"
          >
            {user.fullName}
          </h2>
          <p className="mt-1 text-sm text-zinc-400">
            {user.jobTitle} · {user.department}
          </p>
          <p className="mt-1 text-xs font-semibold uppercase text-zinc-500">
            Primary asset {user.assetTag}
          </p>
          {!isStarterAccountCase || user.accountInspected ? (
            <div className="mt-4 space-y-3">
              <div className="flex flex-wrap gap-2">
                <Badge variant={user.disabled ? 'amber' : 'success'}>
                  {user.disabled ? 'Account disabled' : 'Account enabled'}
                </Badge>
                <Badge variant={user.locked ? 'amber' : 'success'}>
                  {user.locked ? 'Account locked' : 'Account unlocked'}
                </Badge>
                <Badge variant={user.mfaEnrolled ? 'sky' : 'default'}>
                  {user.mfaEnrolled ? 'MFA enrolled' : 'MFA reset'}
                </Badge>
                {isStarterAccountCase ? (
                  <Badge
                    variant={
                      user.passwordState === 'expired' ? 'amber' : 'default'
                    }
                  >
                    Password {user.passwordState}
                  </Badge>
                ) : null}
              </div>
              {isStarterAccountCase ? (
                <dl className="grid gap-2 rounded-sm border border-zinc-800 bg-zinc-950/60 p-3 text-xs sm:grid-cols-2">
                  <div>
                    <dt className="font-bold uppercase tracking-wide text-zinc-500">
                      Primary authentication
                    </dt>
                    <dd className="mt-1 text-zinc-200">
                      {user.primaryAuthSucceeds
                        ? 'Expected to succeed'
                        : 'Blocked'}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-bold uppercase tracking-wide text-zinc-500">
                      Registered MFA factor
                    </dt>
                    <dd className="mt-1 text-zinc-200">
                      {user.mfaFactorStatus === 'device-unavailable'
                        ? 'Device unavailable'
                        : user.mfaFactorStatus === 'reset-ready'
                          ? 'Re-registration required'
                          : 'Available'}
                    </dd>
                  </div>
                </dl>
              ) : null}
            </div>
          ) : (
            <p className="mt-4 rounded-sm border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-400">
              Account status has not been reviewed yet.
            </p>
          )}
        </div>
      </Card>

      {isStarterAccountCase ? (
        <Card>
          <CardHeader
            meta="Read → investigate → diagnose"
            title="Account review"
          />
          <div className="space-y-4 p-4">
            <div className="grid gap-2 sm:grid-cols-2">
              <Button
                disabled={user.accountInspected}
                onClick={() => onAction(inspectAccount(user.id))}
                variant="soft"
              >
                {user.accountInspected
                  ? 'Account state reviewed'
                  : 'Review account state'}
              </Button>
              {user.identityVerificationMethod ? (
                <Button
                  disabled={!user.accountInspected || user.identityVerified}
                  onClick={() =>
                    onAction(
                      verifyIdentity(user.id, user.identityVerificationMethod!),
                    )
                  }
                  variant="soft"
                >
                  {user.identityVerified
                    ? 'Identity evidence recorded'
                    : 'Record verified chat evidence'}
                </Button>
              ) : (
                <Link
                  aria-disabled={!user.accountInspected}
                  className={`sd-button sd-button--light sd-focus-ring inline-flex min-h-10 items-center justify-center rounded-sm border border-zinc-300 bg-zinc-100 px-4 py-2 text-sm font-extrabold uppercase text-zinc-900 ${!user.accountInspected ? 'pointer-events-none opacity-50' : ''}`}
                  href={`/tools/company-chat?contact=${user.id}${supportTicketId ? `&ticket=${supportTicketId}` : ''}`}
                >
                  Verify through Company Chat
                </Link>
              )}
              {user.supportIssue === 'mfa-factor-unavailable' ? (
                <Button
                  disabled={!user.accountInspected || user.primaryAuthTested}
                  onClick={() =>
                    onAction(
                      testPrimaryAuth(
                        user.id,
                        user.primaryAuthSucceeds ? 'succeeds' : 'blocked',
                      ),
                    )
                  }
                  variant="soft"
                >
                  {user.primaryAuthTested
                    ? 'Primary sign-in tested'
                    : 'Test primary password sign-in'}
                </Button>
              ) : null}
            </div>
            <p className="text-xs leading-relaxed text-zinc-500">
              Training assumption: the identity check represents an approved
              internal verification process. Never request or record a real
              password, recovery code, or security answer.
            </p>
            <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
              <Select
                aria-label="Account diagnosis"
                disabled={!user.identityVerified || Boolean(user.diagnosis)}
                onChange={(event) => setDiagnosis(event.target.value)}
                value={user.diagnosis ?? diagnosis}
              >
                <option value="">Select diagnosis from the evidence</option>
                <option value="account-locked">Account is locked</option>
                <option value="password-expired">Password is expired</option>
                <option value="mfa-factor-unavailable">
                  Registered MFA factor is unavailable
                </option>
              </Select>
              <Button
                disabled={!diagnosis || Boolean(user.diagnosis)}
                onClick={() =>
                  onAction(
                    recordDiagnosis(
                      user.id,
                      diagnosis as
                        | 'account-locked'
                        | 'password-expired'
                        | 'mfa-factor-unavailable',
                    ),
                  )
                }
              >
                Record diagnosis
              </Button>
            </div>
            {remediationComplete ? (
              <AccountSignInTestDialog
                onConfirm={(check) => onAction(verifyAccess(user.id, check))}
                user={user}
              />
            ) : null}
          </div>
        </Card>
      ) : null}

      <Card>
        <CardHeader title="Account actions" />
        <div className="grid gap-2 p-4 sm:grid-cols-2">
          <DirectoryActionDialog
            confirmLabel="Unlock account"
            description={`Unlock ${user.fullName} so the account can accept new sign-in attempts.`}
            onConfirm={() => onAction(unlockAccount(user.id))}
            title="Unlock account"
            trigger={
              <Button
                disabled={
                  !user.locked ||
                  (isStarterAccountCase && user.diagnosis !== 'account-locked')
                }
                variant="soft"
              >
                <IconLockOpen aria-hidden="true" className="h-4 w-4" />
                {user.locked ? 'Unlock account' : 'Already unlocked'}
              </Button>
            }
          />
          <PasswordResetDialog
            disabled={
              user.disabled ||
              (isStarterAccountCase && user.diagnosis !== 'password-expired')
            }
            fullName={user.fullName}
            onConfirm={(requireChangeAtNextSignIn) =>
              onAction(resetPassword(user.id, requireChangeAtNextSignIn))
            }
          />
          <DirectoryActionDialog
            confirmLabel={user.disabled ? 'Enable account' : 'Disable account'}
            description={
              user.disabled
                ? `Restore sign-in access for ${user.fullName}.`
                : `Block sign-in access for ${user.fullName} until the account is enabled again.`
            }
            onConfirm={() =>
              onAction(
                user.disabled
                  ? enableAccount(user.id)
                  : disableAccount(user.id),
              )
            }
            title={user.disabled ? 'Enable account' : 'Disable account'}
            trigger={
              <Button variant={user.disabled ? 'primary' : 'default'}>
                <IconUserCheck aria-hidden="true" className="h-4 w-4" />
                {user.disabled ? 'Enable account' : 'Disable account'}
              </Button>
            }
            variant={user.disabled ? 'primary' : 'default'}
          />
          <DirectoryActionDialog
            confirmLabel="Reset MFA"
            description={`Clear ${user.fullName}’s current MFA registration so a new authenticator can be enrolled.`}
            onConfirm={() => onAction(resetMfa(user.id))}
            title="Reset MFA"
            trigger={
              <Button
                disabled={
                  user.disabled ||
                  (isStarterAccountCase &&
                    user.diagnosis !== 'mfa-factor-unavailable')
                }
              >
                <IconShieldLock aria-hidden="true" className="h-4 w-4" />
                Reset MFA
              </Button>
            }
          />
        </div>
      </Card>

      <Card>
        <CardHeader meta={`${user.groups.length} assigned`} title="Groups" />
        <div className="p-4">
          <div className="flex flex-wrap gap-2">
            {user.groups.map((group) => (
              <Badge className="gap-1 pr-1" key={group} variant="sky">
                {group}
                <DirectoryActionDialog
                  confirmLabel="Remove group"
                  description={`Remove ${user.fullName} from ${group}. Access supplied by this group may stop after the change.`}
                  onConfirm={() => onAction(updateGroups(user.id, [], [group]))}
                  title="Remove group membership"
                  trigger={
                    <button
                      aria-label={`Remove ${group} from ${user.fullName}`}
                      className="sd-focus-ring rounded-sm p-0.5 text-sky-200 hover:bg-sky-400/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                      type="button"
                    >
                      <IconX aria-hidden="true" className="h-3 w-3" />
                    </button>
                  }
                  variant="default"
                />
              </Badge>
            ))}
          </div>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <label className="sr-only" htmlFor={`add-group-${user.id}`}>
              Group to add
            </label>
            <Select
              id={`add-group-${user.id}`}
              onChange={(event) => setGroupToAdd(event.target.value)}
              value={groupToAdd}
            >
              <option value="">Select a group to add</option>
              {availableGroups.map((group) => (
                <option key={group} value={group}>
                  {group}
                </option>
              ))}
            </Select>
            <DirectoryActionDialog
              confirmLabel="Add group"
              description={`Add ${user.fullName} to ${groupToAdd || 'the selected group'} and apply its simulated access.`}
              onConfirm={() => {
                onAction(updateGroups(user.id, [groupToAdd], []));
                setGroupToAdd('');
              }}
              title="Add group membership"
              trigger={
                <Button disabled={!groupToAdd} variant="soft">
                  <IconUsersGroup aria-hidden="true" className="h-4 w-4" />
                  Add group
                </Button>
              }
            />
          </div>
        </div>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader title="Devices" />
          <div className="divide-y divide-zinc-800">
            {user.devices.map((device) => (
              <div className="flex gap-3 p-4" key={device.assetTag}>
                <IconDeviceLaptop
                  aria-hidden="true"
                  className="h-5 w-5 shrink-0 text-sky-400"
                />
                <div>
                  <p className="text-sm font-bold text-zinc-100">
                    {device.assetTag}
                  </p>
                  <p className="mt-1 text-xs text-zinc-500">
                    {device.deviceType} · {device.status}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <CardHeader title="Licenses" />
          <div className="divide-y divide-zinc-800">
            {user.licenses.map((license) => (
              <div
                className="flex items-center justify-between gap-3 p-4"
                key={license.productName}
              >
                <p className="text-sm font-semibold text-zinc-200">
                  {license.productName}
                </p>
                <Badge variant={license.assigned ? 'success' : 'default'}>
                  {license.assigned ? 'Assigned' : 'Available'}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </aside>
  );
}
