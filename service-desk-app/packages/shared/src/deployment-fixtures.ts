export const DEPLOYMENT_DOMAIN = 'SERVICEDESK-SIMULATOR.LOCAL';
export const DEPLOYMENT_SHARE_PASSWORD = 'Deploy!2026';
export const DEPLOYMENT_DOMAIN_USERNAME = 'deployment.tech';
export const DEPLOYMENT_DOMAIN_PASSWORD = 'Welcome!2026';

export const DEPLOYMENT_CABLES = [
  'POWER',
  'ETHERNET/RJ-45',
  'DISPLAYPORT',
  'USB KEYBOARD',
  'USB MOUSE',
] as const;

export type DeploymentCable = (typeof DEPLOYMENT_CABLES)[number];

export const DEPLOYMENT_PORTS = [
  'AC POWER IN',
  'RJ-45 NETWORK',
  'DISPLAYPORT OUT',
  'USB PORT 1',
  'USB PORT 2',
] as const;

export type DeploymentPort = (typeof DEPLOYMENT_PORTS)[number];

export const DEPLOYMENT_CABLE_PORTS: Readonly<
  Record<DeploymentCable, DeploymentPort>
> = {
  POWER: 'AC POWER IN',
  'ETHERNET/RJ-45': 'RJ-45 NETWORK',
  DISPLAYPORT: 'DISPLAYPORT OUT',
  'USB KEYBOARD': 'USB PORT 1',
  'USB MOUSE': 'USB PORT 2',
};

export const DEPLOYMENT_BOOT_SOURCES = [
  'Workstation OS Boot Manager (Internal NVMe SSD)',
  'PXE Network Boot IPv4',
  'PXE Network Boot IPv6',
] as const;

export type DeploymentBootSource = (typeof DEPLOYMENT_BOOT_SOURCES)[number];

export const DEPLOYMENT_STEP_IDS = [
  'device-type',
  'cables',
  'post-f12',
  'boot-source',
  'share-auth',
  'hostname',
  'task-sequence',
  'reboot',
  'domain-login',
  'success',
  'pc-shelf',
] as const;

export type DeploymentStepId = (typeof DEPLOYMENT_STEP_IDS)[number];

export interface DeploymentStepTemplate {
  id: DeploymentStepId;
  title: string;
  expectedAction: string;
  wrongActionResponses: Readonly<Record<string, string>>;
}

export const DEPLOYMENT_STEP_TEMPLATES: readonly DeploymentStepTemplate[] = [
  {
    id: 'device-type',
    title: 'Select Desktop Deployment',
    expectedAction: 'deployment.select_device_type',
    wrongActionResponses: {
      unsupported:
        'This task sequence is prepared for desktop hardware. Select Desktop Deployment to continue.',
    },
  },
  {
    id: 'cables',
    title: 'Connect workstation cables',
    expectedAction: 'deployment.connect_cable',
    wrongActionResponses: {
      'wrong-port':
        'That connector does not match the selected port. Check the port label and try again.',
      duplicate: 'That cable is already connected to the workstation.',
    },
  },
  {
    id: 'post-f12',
    title: 'Open the one-time boot menu',
    expectedAction: 'deployment.press_f12',
    wrongActionResponses: {
      early:
        'The firmware is still initializing and did not register F12. Wait for the boot prompt, then retry.',
      late: 'The boot-menu window closed. Restart the POST sequence and try again.',
    },
  },
  {
    id: 'boot-source',
    title: 'Choose a network boot source',
    expectedAction: 'deployment.select_boot_source',
    wrongActionResponses: {
      local:
        'The internal drive starts the existing operating system. Use the IPv4 network option for imaging.',
      ipv6: 'IPv6 PXE is not configured on this training network. Choose PXE Network Boot IPv4.',
    },
  },
  {
    id: 'share-auth',
    title: 'Authenticate to the deployment share',
    expectedAction: 'deployment.authenticate_share',
    wrongActionResponses: { password: 'The password is incorrect.' },
  },
  {
    id: 'hostname',
    title: 'Set OSDCOMPUTERNAME',
    expectedAction: 'deployment.set_hostname',
    wrongActionResponses: {
      format:
        'Use the uppercase corporate asset format SD followed by four digits.',
      duplicate:
        'That computer name is already registered to another device. Choose an unused asset tag.',
    },
  },
  {
    id: 'task-sequence',
    title: 'Run the automated task sequence',
    expectedAction: 'deployment.run_task_sequence',
    wrongActionResponses: {
      order: 'Complete the current deployment step first.',
    },
  },
  {
    id: 'reboot',
    title: 'Reboot into the deployed operating system',
    expectedAction: 'deployment.reboot',
    wrongActionResponses: {
      order: 'The task sequence must finish before rebooting.',
    },
  },
  {
    id: 'domain-login',
    title: 'Verify the domain login',
    expectedAction: 'deployment.domain_login',
    wrongActionResponses: {
      credentials: 'The password is incorrect. Try again.',
      domain: `Sign in to the ${DEPLOYMENT_DOMAIN} domain.`,
    },
  },
  {
    id: 'success',
    title: 'Deployment Successful',
    expectedAction: 'deployment.domain_login',
    wrongActionResponses: {},
  },
  {
    id: 'pc-shelf',
    title: 'Land the provisioned PC on the PC Shelf',
    expectedAction: 'deployment.domain_login',
    wrongActionResponses: {},
  },
] as const;
