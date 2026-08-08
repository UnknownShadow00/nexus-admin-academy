'use client';

import {
  applyBackup,
  exportBackup,
  validateBackup,
  type AttemptCodec,
  type ScenarioRecord,
} from '@service-desk/shared';
import {
  restoreAttempt,
  serializeAttempt,
  type Attempt,
} from '@service-desk/simulation-engine';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  PriorityBadge,
} from '@service-desk/ui';
import Link from 'next/link';
import { useEffect, useState, type ChangeEvent } from 'react';

import { TestStudentManager } from './TestStudentManager';
import {
  deleteServerScenario,
  listServerScenarios,
} from '../../../lib/nexus-admin-scenario-client';

const attemptCodec: AttemptCodec<Attempt> = {
  restoreAttempt,
  serializeAttempt,
};

export function AdminDashboard() {
  const [backupMessage, setBackupMessage] = useState<{
    text: string;
    tone: 'error' | 'success';
  } | null>(null);
  const [records, setRecords] = useState<ScenarioRecord[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    listServerScenarios()
      .then(setRecords)
      .catch((error: unknown) => setBackupMessage({
        text: error instanceof Error ? error.message : 'Scenario library could not load.',
        tone: 'error',
      }))
      .finally(() => setLoading(false));
  }, []);

  function downloadBackup() {
    try {
      const backup = exportBackup(attemptCodec);
      const blob = new Blob([JSON.stringify(backup, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.download = `nexus-service-desk-backup-${backup.exportedAt.slice(0, 10)}.json`;
      anchor.href = url;
      anchor.hidden = true;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setBackupMessage({
        text: 'Backup exported successfully.',
        tone: 'success',
      });
    } catch (error) {
      setBackupMessage({
        text: error instanceof Error ? error.message : 'Backup export failed.',
        tone: 'error',
      });
    }
  }

  async function importBackup(event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) {
      return;
    }

    try {
      const json = await file.text();
      validateBackup(json, attemptCodec);
      const restored = applyBackup(json, attemptCodec);
      setBackupMessage({
        text: `Local practice backup restored: ${restored.testStudentCount} test students. Server scenarios were not changed.`,
        tone: 'success',
      });
    } catch (error) {
      setBackupMessage({
        text: error instanceof Error ? error.message : 'Backup import failed.',
        tone: 'error',
      });
    } finally {
      input.value = '';
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-black">Scenario library</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Server-backed drafts with immutable published version history.
          </p>
        </div>
        <Link
          className="rounded-sm border border-amber-500 bg-amber-600 px-4 py-2 text-center text-sm font-black uppercase text-zinc-950 hover:bg-amber-500"
          href="/admin/scenarios/new"
        >
          New Scenario
        </Link>
      </div>

      <Card>
        <CardHeader meta={`${records.length} templates`} title="Scenarios" />
        <div className="p-4">
          {loading ? (
            <p className="py-8 text-center text-sm text-zinc-500">Loading scenarios…</p>
          ) : records.length === 0 ? (
            <p className="py-8 text-center text-sm text-zinc-500">
              No scenarios have been created yet.
            </p>
          ) : (
            <ul className="divide-y divide-zinc-800">
              {records.map(({ template, versions }) => {
                const draft = versions.find(
                  (version) => version.publishedAt === null,
                );
                return (
                  <li
                    className="flex flex-col gap-3 py-4 lg:flex-row lg:items-center"
                    key={template.id}
                  >
                    <div className="min-w-0 flex-1">
                      <Link
                        className="font-bold text-zinc-100 hover:text-sky-300"
                        href={`/admin/scenarios/${template.id}`}
                      >
                        {template.title}
                      </Link>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Badge>{template.category}</Badge>
                        <PriorityBadge pill priority={template.priority} />
                        <Badge variant={draft ? 'amber' : 'success'}>
                          {draft
                            ? `Draft v${draft.version}`
                            : template.activeVersionId
                              ? 'Published'
                              : 'Empty'}
                        </Badge>
                        <span className="text-xs text-zinc-500">
                          {versions.length} version
                          {versions.length === 1 ? '' : 's'}
                        </span>
                      </div>
                    </div>
                    <Link
                      className="text-sm font-bold text-sky-300 hover:underline"
                      href={`/admin/scenarios/${template.id}/preview`}
                    >
                      Preview
                    </Link>
                    <Button
                      onClick={() => {
                        if (
                          window.confirm(
                            `Delete the unpublished scenario “${template.title}”? Published history cannot be deleted.`,
                          )
                        ) {
                          void deleteServerScenario(template.id)
                            .then(() => setRecords((current) => current.filter(
                              ({ template: candidate }) => candidate.id !== template.id,
                            )))
                            .catch((error: unknown) => setBackupMessage({
                              text: error instanceof Error ? error.message : 'Scenario delete failed.',
                              tone: 'error',
                            }));
                        }
                      }}
                    >
                      Delete
                    </Button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </Card>
      <Card>
        <CardHeader meta="Local practice data" title="Backup and restore" />
        <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center">
          <Button onClick={downloadBackup} variant="primary">
            Export all data
          </Button>
          <label className="sd-button sd-button--default sd-focus-ring inline-flex min-h-10 cursor-pointer items-center justify-center rounded-sm border border-zinc-700 bg-zinc-900 px-4 py-2 text-sm font-extrabold uppercase text-zinc-200 transition-colors hover:bg-zinc-800 focus-within:ring-2 focus-within:ring-sky-400">
            Import backup
            <input
              accept="application/json,.json"
              className="sr-only"
              onChange={importBackup}
              type="file"
            />
          </label>
          <p className="text-xs text-zinc-500">
            Includes browser-local practice and test-student attempts. Scenario
            definitions are already stored authoritatively on the Nexus server.
          </p>
        </div>
        {backupMessage ? (
          <p
            className={`border-t border-zinc-800 px-4 py-3 text-sm ${
              backupMessage.tone === 'success'
                ? 'text-emerald-300'
                : 'text-red-300'
            }`}
            role={backupMessage.tone === 'error' ? 'alert' : 'status'}
          >
            {backupMessage.text}
          </p>
        ) : null}
      </Card>
      <TestStudentManager compact />
    </div>
  );
}
