'use client';

import { getStatusTransitions, TicketStatus } from '@service-desk/shared';
import { Select } from '@service-desk/ui';

import { TICKET_STATUS_LABELS } from './ticket-labels';

interface StatusMenuProps {
  onChange: (status: TicketStatus) => void;
  status: TicketStatus;
}

export function StatusMenu({ onChange, status }: StatusMenuProps) {
  const options = [status, ...getStatusTransitions(status)];

  return (
    <label className="min-w-44 flex-1 sm:flex-none">
      <span className="sr-only">Change ticket status</span>
      <Select
        aria-label="Change ticket status"
        onChange={(event) => onChange(event.target.value as TicketStatus)}
        value={status}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {TICKET_STATUS_LABELS[option]}
          </option>
        ))}
      </Select>
    </label>
  );
}
