import {
  DEPLOYMENT_CABLE_PORTS,
  DEPLOYMENT_CABLES,
  DEPLOYMENT_DOMAIN,
  DEPLOYMENT_DOMAIN_PASSWORD,
  DEPLOYMENT_DOMAIN_USERNAME,
  DEPLOYMENT_SHARE_PASSWORD,
  type DeploymentCable,
} from '@service-desk/shared';
import { describe, expect, it } from 'vitest';

import type { SimulationAction } from './actions';
import { applyAction } from './apply-action';
import { createAttempt } from './attempt';
import type { Attempt } from './types';

const ACTOR_ID = 'student-1';

function apply(attempt: Attempt, action: SimulationAction) {
  return applyAction(attempt, ACTOR_ID, action);
}

function startDeployment() {
  const started = apply(createAttempt(), {
    type: 'deployment.start',
    payload: {},
  });
  const runId = started.attempt.activeDeploymentRunId;
  if (!runId) {
    throw new Error('Deployment did not create an active run.');
  }
  return { ...started, runId };
}

function completeThroughHostname(hostname = 'SD4312') {
  const started = startDeployment();
  let attempt = apply(started.attempt, {
    type: 'deployment.select_device_type',
    payload: { runId: started.runId, deviceType: 'Desktop' },
  }).attempt;
  for (const cable of DEPLOYMENT_CABLES) {
    attempt = apply(attempt, {
      type: 'deployment.connect_cable',
      payload: {
        runId: started.runId,
        cable,
        port: DEPLOYMENT_CABLE_PORTS[cable],
      },
    }).attempt;
  }
  attempt = apply(attempt, {
    type: 'deployment.press_f12',
    payload: { runId: started.runId, timing: 'window' },
  }).attempt;
  attempt = apply(attempt, {
    type: 'deployment.select_boot_source',
    payload: { runId: started.runId, source: 'PXE Network Boot IPv4' },
  }).attempt;
  attempt = apply(attempt, {
    type: 'deployment.authenticate_share',
    payload: { runId: started.runId, password: DEPLOYMENT_SHARE_PASSWORD },
  }).attempt;
  attempt = apply(attempt, {
    type: 'deployment.set_hostname',
    payload: { runId: started.runId, hostname },
  }).attempt;
  return { attempt, runId: started.runId };
}

function completeDeployment(hostname = 'SD4312') {
  const ready = completeThroughHostname(hostname);
  let attempt = apply(ready.attempt, {
    type: 'deployment.run_task_sequence',
    payload: { runId: ready.runId },
  }).attempt;
  attempt = apply(attempt, {
    type: 'deployment.reboot',
    payload: { runId: ready.runId },
  }).attempt;
  attempt = apply(attempt, {
    type: 'deployment.domain_login',
    payload: {
      runId: ready.runId,
      domain: DEPLOYMENT_DOMAIN,
      username: DEPLOYMENT_DOMAIN_USERNAME,
      password: DEPLOYMENT_DOMAIN_PASSWORD,
    },
  }).attempt;
  return { attempt, runId: ready.runId };
}

describe('Computer Deployment actions', () => {
  it('records device-type rejection before accepting Desktop Deployment', () => {
    const started = startDeployment();
    const rejected = apply(started.attempt, {
      type: 'deployment.select_device_type',
      payload: { runId: started.runId, deviceType: 'Laptop' },
    });
    const accepted = apply(rejected.attempt, {
      type: 'deployment.select_device_type',
      payload: { runId: started.runId, deviceType: 'Desktop' },
    });

    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('desktop hardware');
    expect(accepted.event.success).toBe(true);
    expect(
      accepted.attempt.deploymentRuns[started.runId]?.currentStepIndex,
    ).toBe(1);
  });

  it('rejects a wrong cable port and completes the cable step at 5/5', () => {
    const started = startDeployment();
    let attempt = apply(started.attempt, {
      type: 'deployment.select_device_type',
      payload: { runId: started.runId, deviceType: 'Desktop' },
    }).attempt;
    const rejected = apply(attempt, {
      type: 'deployment.connect_cable',
      payload: {
        runId: started.runId,
        cable: 'POWER',
        port: 'RJ-45 NETWORK',
      },
    });
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('does not match');
    attempt = rejected.attempt;

    for (const cable of DEPLOYMENT_CABLES) {
      attempt = apply(attempt, {
        type: 'deployment.connect_cable',
        payload: {
          runId: started.runId,
          cable,
          port: DEPLOYMENT_CABLE_PORTS[cable],
        },
      }).attempt;
    }

    expect(attempt.deploymentRuns[started.runId]?.connectedCables).toHaveLength(
      5,
    );
    expect(attempt.deploymentRuns[started.runId]?.currentStepIndex).toBe(2);
  });

  it.each([
    ['early', 'initializing'],
    ['late', 'window closed'],
  ] as const)('rejects %s F12 timing and permits a retry', (timing, copy) => {
    const ready = completeThroughCables();
    const rejected = apply(ready.attempt, {
      type: 'deployment.press_f12',
      payload: { runId: ready.runId, timing },
    });
    const accepted = apply(rejected.attempt, {
      type: 'deployment.press_f12',
      payload: { runId: ready.runId, timing: 'window' },
    });

    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain(copy);
    expect(accepted.event.success).toBe(true);
  });

  it.each([
    ['Workstation OS Boot Manager (Internal NVMe SSD)', 'internal drive'],
    ['PXE Network Boot IPv6', 'IPv6 PXE'],
  ] as const)('rejects the %s boot source', (source, copy) => {
    const ready = completeThroughF12();
    const rejected = apply(ready.attempt, {
      type: 'deployment.select_boot_source',
      payload: { runId: ready.runId, source },
    });

    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain(copy);
  });

  it('rejects an incorrect deployment-share password', () => {
    const ready = completeThroughBootSource();
    const rejected = apply(ready.attempt, {
      type: 'deployment.authenticate_share',
      payload: { runId: ready.runId, password: 'not-it' },
    });

    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toBe('The password is incorrect.');
  });

  it('rejects invalid and duplicate hostnames, then accepts a unique SD tag', () => {
    const ready = completeThroughShareAuth();
    const invalid = apply(ready.attempt, {
      type: 'deployment.set_hostname',
      payload: { runId: ready.runId, hostname: 'sd42' },
    });
    const duplicate = apply(invalid.attempt, {
      type: 'deployment.set_hostname',
      payload: { runId: ready.runId, hostname: 'SD9099' },
    });
    const accepted = apply(duplicate.attempt, {
      type: 'deployment.set_hostname',
      payload: { runId: ready.runId, hostname: 'SD4312' },
    });

    expect(invalid.event.rejectReason).toContain('SD followed by four digits');
    expect(duplicate.event.rejectReason).toContain('already registered');
    expect(accepted.event.success).toBe(true);
  });

  it('rejects out-of-order task-sequence and reboot actions', () => {
    const ready = completeThroughHostname();
    const earlyReboot = apply(ready.attempt, {
      type: 'deployment.reboot',
      payload: { runId: ready.runId },
    });
    const taskRun = apply(earlyReboot.attempt, {
      type: 'deployment.run_task_sequence',
      payload: { runId: ready.runId },
    });
    const repeatedTask = apply(taskRun.attempt, {
      type: 'deployment.run_task_sequence',
      payload: { runId: ready.runId },
    });

    expect(earlyReboot.event.success).toBe(false);
    expect(earlyReboot.event.rejectReason).toContain('automated task sequence');
    expect(repeatedTask.event.success).toBe(false);
    expect(repeatedTask.event.rejectReason).toContain('Reboot');
  });

  it('rejects wrong domain and credentials, then completes onto PC Shelf', () => {
    const ready = completeThroughHostname('SD4312');
    let attempt = apply(ready.attempt, {
      type: 'deployment.run_task_sequence',
      payload: { runId: ready.runId },
    }).attempt;
    attempt = apply(attempt, {
      type: 'deployment.reboot',
      payload: { runId: ready.runId },
    }).attempt;
    const wrongDomain = apply(attempt, {
      type: 'deployment.domain_login',
      payload: {
        runId: ready.runId,
        domain: 'LOCAL',
        username: DEPLOYMENT_DOMAIN_USERNAME,
        password: DEPLOYMENT_DOMAIN_PASSWORD,
      },
    });
    const wrongPassword = apply(wrongDomain.attempt, {
      type: 'deployment.domain_login',
      payload: {
        runId: ready.runId,
        domain: DEPLOYMENT_DOMAIN,
        username: DEPLOYMENT_DOMAIN_USERNAME,
        password: 'wrong',
      },
    });
    const completed = apply(wrongPassword.attempt, {
      type: 'deployment.domain_login',
      payload: {
        runId: ready.runId,
        domain: DEPLOYMENT_DOMAIN,
        username: DEPLOYMENT_DOMAIN_USERNAME,
        password: DEPLOYMENT_DOMAIN_PASSWORD,
      },
    });

    expect(wrongDomain.event.rejectReason).toContain(DEPLOYMENT_DOMAIN);
    expect(wrongPassword.event.rejectReason).toBe(
      'The password is incorrect. Try again.',
    );
    expect(
      completed.attempt.deploymentRuns[ready.runId]?.completedAt,
    ).toBeTruthy();
    expect(completed.attempt.pcShelfOverlays.SD4312).toMatchObject({
      present: true,
      device: { assetTag: 'SD4312' },
    });
    expect(
      completed.attempt.deploymentRuns[ready.runId]?.events.every((event) =>
        event.type.startsWith('deployment.'),
      ),
    ).toBe(true);
  });
});

describe('Shipping Manager actions', () => {
  it('creates an instant shipment and consumes its selected shelf PC', () => {
    const deployed = completeDeployment('SD4312');
    const shipped = apply(deployed.attempt, createShipmentAction('SD4312'));
    const shipment = Object.values(shipped.attempt.shipments)[0];

    expect(shipped.event.success).toBe(true);
    expect(shipment).toMatchObject({
      computerAssetTag: 'SD4312',
      speed: 'rush',
      status: 'shipped',
    });
    expect(shipped.attempt.pcShelfOverlays.SD4312?.present).toBe(false);
    expect(shipped.attempt.lastShippingAddress?.recipientName).toBe(
      'Avery Brooks',
    );
  });

  it('rejects an incomplete address without consuming the PC', () => {
    const deployed = completeDeployment('SD4312');
    const action = createShipmentAction('SD4312');
    const rejected = apply(deployed.attempt, {
      ...action,
      payload: { ...action.payload, street: '' },
    });

    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toBe(
      'Enter the full shipping address before shipping.',
    );
    expect(rejected.attempt.pcShelfOverlays.SD4312?.present).toBe(true);
  });

  it('cancels a shipment, appends an event, and restores the shelf PC', () => {
    const deployed = completeDeployment('SD4312');
    const shipped = apply(deployed.attempt, createShipmentAction('SD4312'));
    const shipment = Object.values(shipped.attempt.shipments)[0];
    if (!shipment) {
      throw new Error('Shipment was not created.');
    }
    const cancelled = apply(shipped.attempt, {
      type: 'shipping.cancel',
      payload: { shipmentId: shipment.id },
    });

    expect(cancelled.event.success).toBe(true);
    expect(cancelled.attempt.shipments[shipment.id]?.status).toBe('cancelled');
    expect(cancelled.attempt.shipments[shipment.id]?.events).toHaveLength(2);
    expect(cancelled.attempt.pcShelfOverlays.SD4312?.present).toBe(true);
  });
});

function completeThroughCables() {
  const started = startDeployment();
  let attempt = apply(started.attempt, {
    type: 'deployment.select_device_type',
    payload: { runId: started.runId, deviceType: 'Desktop' },
  }).attempt;
  for (const cable of DEPLOYMENT_CABLES) {
    attempt = apply(attempt, {
      type: 'deployment.connect_cable',
      payload: {
        runId: started.runId,
        cable: cable as DeploymentCable,
        port: DEPLOYMENT_CABLE_PORTS[cable],
      },
    }).attempt;
  }
  return { attempt, runId: started.runId };
}

function completeThroughF12() {
  const ready = completeThroughCables();
  return {
    runId: ready.runId,
    attempt: apply(ready.attempt, {
      type: 'deployment.press_f12',
      payload: { runId: ready.runId, timing: 'window' },
    }).attempt,
  };
}

function completeThroughBootSource() {
  const ready = completeThroughF12();
  return {
    runId: ready.runId,
    attempt: apply(ready.attempt, {
      type: 'deployment.select_boot_source',
      payload: { runId: ready.runId, source: 'PXE Network Boot IPv4' },
    }).attempt,
  };
}

function completeThroughShareAuth() {
  const ready = completeThroughBootSource();
  return {
    runId: ready.runId,
    attempt: apply(ready.attempt, {
      type: 'deployment.authenticate_share',
      payload: { runId: ready.runId, password: DEPLOYMENT_SHARE_PASSWORD },
    }).attempt,
  };
}

function createShipmentAction(
  computerAssetTag: string,
): Extract<SimulationAction, { type: 'shipping.create' }> {
  return {
    type: 'shipping.create',
    payload: {
      recipientDirectoryUserId: 'directory-user-avery-brooks',
      recipientName: 'Avery Brooks',
      street: '120 Cedar Street',
      city: 'Seattle',
      state: 'WA',
      postalCode: '98101',
      senderDepartment: 'IT Department',
      equipment: [{ name: 'Computer', quantity: 1 }],
      computerAssetTag,
      speed: 'rush',
      includeReturnLabel: true,
    },
  };
}
