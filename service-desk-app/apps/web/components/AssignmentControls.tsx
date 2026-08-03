'use client';

import { Button } from '@service-desk/ui';
import { IconUserCheck, IconUserMinus } from '@tabler/icons-react';

interface AssignmentControlsProps {
  assigned: boolean;
  onAssign: () => void;
  onUnassign: () => void;
}

export function AssignmentControls({
  assigned,
  onAssign,
  onUnassign,
}: AssignmentControlsProps) {
  return assigned ? (
    <Button className="flex-1 sm:flex-none" onClick={onUnassign}>
      <IconUserMinus aria-hidden="true" className="h-4 w-4" />
      Unassign
    </Button>
  ) : (
    <Button className="flex-1 sm:flex-none" onClick={onAssign} variant="soft">
      <IconUserCheck aria-hidden="true" className="h-4 w-4" />
      Assign to me
    </Button>
  );
}
