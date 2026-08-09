'use client';

import {
  createTestStudent,
  deleteTestStudent,
  listTestStudents,
  renameTestStudent,
  type TestStudentSlot,
} from '@service-desk/shared';
import { Button, Card, CardHeader, Input } from '@service-desk/ui';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { clearTestAttempt } from '../_lib/test-attempt';

export function TestStudentManager({ compact = false }: { compact?: boolean }) {
  const [slots, setSlots] = useState<TestStudentSlot[]>([]);
  const [name, setName] = useState('');

  useEffect(() => setSlots(listTestStudents()), []);

  function create() {
    const slot = createTestStudent(name);
    setSlots(listTestStudents());
    setName('');
    if (compact) {
      window.location.href = `/admin/test-students/${slot.id}`;
    }
  }

  return (
    <Card>
      <CardHeader
        meta={
          <Link
            className="text-sky-300 hover:underline"
            href="/admin/test-students"
          >
            Manage all
          </Link>
        }
        title="Test student slots"
      />
      <div className="space-y-4 p-4">
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            aria-label="Test student name"
            onChange={(event) => setName(event.target.value)}
            placeholder="Slot name"
            value={name}
          />
          <Button onClick={create} variant="primary">
            New Test Student
          </Button>
        </div>
        {slots.length === 0 ? (
          <p className="text-sm text-zinc-500">No test students yet.</p>
        ) : (
          <ul className="divide-y divide-zinc-800">
            {slots.map((slot) => (
              <li
                className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center"
                key={slot.id}
              >
                <Input
                  aria-label={`Rename ${slot.name}`}
                  defaultValue={slot.name}
                  onBlur={(event) => {
                    renameTestStudent(slot.id, event.target.value);
                    setSlots(listTestStudents());
                  }}
                />
                <span className="whitespace-nowrap text-xs text-zinc-500">
                  {slot.assignedScenarioIds.length} assigned
                </span>
                <Link
                  className="rounded-sm border border-sky-500/40 px-3 py-2 text-center text-xs font-bold uppercase text-sky-300"
                  href={`/admin/test-students/${slot.id}`}
                >
                  Open
                </Link>
                {!compact ? (
                  <Button
                    onClick={() => {
                      deleteTestStudent(slot.id);
                      clearTestAttempt(slot.id);
                      setSlots(listTestStudents());
                    }}
                  >
                    Delete
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}
