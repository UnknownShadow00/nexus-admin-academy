import { TicketStatus } from '@service-desk/shared';

import type { TicketSimulationAction } from './actions';
import { applyAction, type ApplyActionResult } from './apply-action';
import type { ActionEvent, Attempt, TicketOverlay } from './types';

const PROXY_TICKET_ID = 'INC2402';

function emptyOverlay(): TicketOverlay {
  return {
    assignedTo: null,
    closure: null,
    escalated: false,
    events: [],
    hintsRevealedCount: 0,
    notes: [],
    status: TicketStatus.Open,
  };
}

function remapEvent(event: ActionEvent, ticketId: string): ActionEvent {
  return {
    ...event,
    payload: { ...event.payload, ticketId },
  };
}

/**
 * Runs an admin-authored synthetic ticket through the unchanged production
 * ticket reducer. applyAction currently validates ticket IDs against the six
 * build-time fixtures, so this adapter temporarily mounts the synthetic
 * overlay at a fixture ID and then restores it under its admin-only key.
 */
export function applyScenarioTicketAction(
  attempt: Attempt,
  actorId: string,
  syntheticTicketId: string,
  action: TicketSimulationAction,
): ApplyActionResult {
  const priorProxy = attempt.ticketOverlays[PROXY_TICKET_ID];
  const current = attempt.ticketOverlays[syntheticTicketId] ?? emptyOverlay();
  const bridged: Attempt = {
    ...attempt,
    ticketOverlays: {
      ...attempt.ticketOverlays,
      [PROXY_TICKET_ID]: current,
    },
  };
  const result = applyAction(bridged, actorId, {
    ...action,
    payload: { ...action.payload, ticketId: PROXY_TICKET_ID },
  } as TicketSimulationAction);
  const proxyResult = result.attempt.ticketOverlays[PROXY_TICKET_ID] ?? current;
  const scenarioOverlay: TicketOverlay = {
    ...proxyResult,
    events: proxyResult.events.map((event) =>
      remapEvent(event, syntheticTicketId),
    ),
  };
  const ticketOverlays = { ...result.attempt.ticketOverlays };
  if (priorProxy) {
    ticketOverlays[PROXY_TICKET_ID] = priorProxy;
  } else {
    delete ticketOverlays[PROXY_TICKET_ID];
  }
  ticketOverlays[syntheticTicketId] = scenarioOverlay;
  const event = remapEvent(result.event, syntheticTicketId);

  return {
    attempt: { ...result.attempt, ticketOverlays },
    event,
  };
}
