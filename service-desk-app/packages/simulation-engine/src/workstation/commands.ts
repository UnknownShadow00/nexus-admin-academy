import type {
  WorkstationMappedDrive,
  WorkstationService,
  WorkstationState,
} from '@service-desk/shared';

export interface WorkstationCommandResult {
  state: WorkstationState;
  output: readonly string[];
  success: boolean;
}

const SHELL_METACHARACTERS = /[&|><;`$\r\n]/;
const DRIVE_LETTER = /^[A-Z]:$/;
const IPV4 = /^\d{1,3}(?:\.\d{1,3}){3}$/;

function result(
  state: WorkstationState,
  output: readonly string[],
  success = true,
): WorkstationCommandResult {
  return { state, output, success };
}

function tokenize(command: string) {
  if (SHELL_METACHARACTERS.test(command)) {
    return { error: 'The command contains unsupported characters.' } as const;
  }
  const tokens: string[] = [];
  const pattern = /"([^"]*)"|'([^']*)'|(\S+)/g;
  let match: RegExpExecArray | null;
  let consumed = '';
  while ((match = pattern.exec(command)) !== null) {
    tokens.push(match[1] ?? match[2] ?? match[3] ?? '');
    consumed += match[0];
  }
  if (
    !tokens.length ||
    command.replace(/\s/g, '') !== consumed.replace(/\s/g, '')
  ) {
    return { error: 'The command has invalid or unmatched quoting.' } as const;
  }
  return { tokens } as const;
}

function primaryInterface(state: WorkstationState) {
  return (
    state.network.interfaces.find((entry) => entry.kind !== 'vpn') ??
    state.network.interfaces[0]
  );
}

function netmask(prefixLength: number) {
  const mask =
    prefixLength === 0 ? 0 : (0xffffffff << (32 - prefixLength)) >>> 0;
  return [24, 16, 8, 0].map((shift) => (mask >>> shift) & 255).join('.');
}

function healthyInternalDns(state: WorkstationState) {
  return state.network.interfaces.some((entry) =>
    entry.dnsServers.some((server) => server.startsWith('10.')),
  );
}

function resolveHost(state: WorkstationState, hostname: string) {
  const host = state.network.knownHosts[hostname.toLowerCase()];
  if (!host) return null;
  if (host.scope === 'public') {
    return state.network.internetReachable ? (host.addresses[0] ?? null) : null;
  }
  if (!healthyInternalDns(state)) return null;
  if (host.scope === 'intranet') {
    return state.network.intranetReachable ? (host.addresses[0] ?? null) : null;
  }
  return state.network.vpn.status === 'connected'
    ? (host.addresses[0] ?? null)
    : null;
}

function canReachIp(state: WorkstationState, address: string) {
  if (address.startsWith('10.90.')) {
    return state.network.routes.some(
      (route) => route.source === 'vpn' && route.destination === '10.90.0.0',
    );
  }
  if (address.startsWith('10.')) return state.network.intranetReachable;
  return state.network.internetReachable;
}

function withDnsCache(
  state: WorkstationState,
  hostname: string,
  address: string,
  timestamp: string,
) {
  const expiresAt = new Date(
    new Date(timestamp).getTime() + 15 * 60 * 1000,
  ).toISOString();
  return {
    ...state,
    network: {
      ...state.network,
      dnsCache: [
        ...state.network.dnsCache.filter(
          (entry) => entry.hostname.toLowerCase() !== hostname.toLowerCase(),
        ),
        { hostname, address, expiresAt, source: 'query' as const },
      ],
    },
  };
}

function listMappings(state: WorkstationState) {
  const drives = Object.values(state.mappedDrives).sort((left, right) =>
    left.letter.localeCompare(right.letter),
  );
  const label = (drive: WorkstationMappedDrive) => {
    if (drive.status === 'connected') return 'OK';
    if (drive.status === 'disconnected') return 'Disconnected';
    if (drive.status === 'permission-error') return 'Access Denied';
    return 'Unavailable';
  };
  return drives.length
    ? [
        'New connections will be remembered.',
        '',
        'Status       Local     Remote',
        ...drives.map(
          (drive) =>
            `${label(drive).padEnd(12)} ${drive.letter.padEnd(9)} ${drive.uncPath}`,
        ),
        '',
        'The command completed successfully.',
      ]
    : [
        'New connections will be remembered.',
        '',
        'There are no entries in the list.',
      ];
}

function uncHostname(path: string) {
  const match = /^\\\\([^\\]+)\\([^\\]+)(?:\\.*)?$/.exec(path);
  return match?.[1]?.toLowerCase() ?? null;
}

export function mapWorkstationDrive(
  state: WorkstationState,
  letter: string,
  uncPath: string,
  reconnectAtSignIn: boolean,
) {
  const hostname = uncHostname(uncPath);
  if (!hostname) {
    return result(
      state,
      ['System error 67 has occurred.', 'The network name cannot be found.'],
      false,
    );
  }
  const address = resolveHost(state, hostname);
  if (!address || !canReachIp(state, address)) {
    return result(
      state,
      ['System error 53 has occurred.', 'The network path was not found.'],
      false,
    );
  }
  const existing =
    state.mappedDrives[letter] ??
    Object.values(state.mappedDrives).find(
      (drive) => drive.uncPath.toLowerCase() === uncPath.toLowerCase(),
    );
  if (existing?.status === 'permission-error') {
    return result(
      state,
      ['System error 5 has occurred.', 'Access is denied.'],
      false,
    );
  }
  const drive: WorkstationMappedDrive = {
    id: existing?.id ?? `mapping-${letter[0]!.toLowerCase()}`,
    letter,
    label:
      existing?.label ??
      uncPath.split('\\').filter(Boolean).at(-1) ??
      'Network Drive',
    uncPath,
    reconnectAtSignIn,
    credentialTarget: existing?.credentialTarget ?? null,
    status: 'connected',
    lastError: null,
  };
  const rootId = `drive-${letter[0]}`;
  return result(
    {
      ...state,
      mappedDrives: { ...state.mappedDrives, [letter]: drive },
      filesystem: {
        ...state.filesystem,
        nodes: {
          ...state.filesystem.nodes,
          [rootId]: {
            ...(state.filesystem.nodes[rootId] ?? {
              id: rootId,
              parentId: null,
              name: `${drive.label} (${letter})`,
              path: `${letter}\\`,
              kind: 'drive' as const,
              modifiedAt: null,
              sizeBytes: null,
            }),
            access: 'read-write',
            available: true,
          },
        },
        error: null,
      },
    },
    ['The command completed successfully.'],
  );
}

export function deleteWorkstationDrive(
  state: WorkstationState,
  letter: string,
) {
  if (!state.mappedDrives[letter]) {
    return result(state, ['The network connection could not be found.'], false);
  }
  const mappedDrives = { ...state.mappedDrives };
  delete mappedDrives[letter];
  const prefix = `${letter}\\`.toLowerCase();
  const nodes = Object.fromEntries(
    Object.entries(state.filesystem.nodes).filter(
      ([, node]) => !node.path.toLowerCase().startsWith(prefix),
    ),
  );
  return result(
    {
      ...state,
      mappedDrives,
      filesystem: {
        ...state.filesystem,
        nodes,
        currentPath: state.filesystem.currentPath
          .toLowerCase()
          .startsWith(prefix)
          ? 'This PC'
          : state.filesystem.currentPath,
        error: null,
      },
    },
    [`${letter} was deleted successfully.`],
  );
}

function serviceByName(state: WorkstationState, name: string) {
  return Object.values(state.services).find(
    (service) =>
      service.name.toLowerCase() === name.toLowerCase() ||
      service.displayName.toLowerCase() === name.toLowerCase(),
  );
}

function serviceQuery(service: WorkstationService) {
  return [
    `SERVICE_NAME: ${service.name}`,
    '        TYPE               : 10  WIN32_OWN_PROCESS',
    `        STATE              : ${service.state === 'running' ? '4  RUNNING' : '1  STOPPED'}`,
    `        START_TYPE         : ${service.startupType.toUpperCase()}`,
  ];
}

export function executeWorkstationCommand(
  state: WorkstationState,
  command: string,
  timestamp: string,
): WorkstationCommandResult {
  const parsed = tokenize(command.trim());
  if ('error' in parsed) {
    return result(
      state,
      [parsed.error ?? 'The command could not be parsed.'],
      false,
    );
  }
  const tokens = parsed.tokens;
  const executable = tokens[0]!.toLowerCase();
  const args = tokens.slice(1);
  const normalizedArgs = args.map((arg) => arg.toLowerCase());
  const networkInterface = primaryInterface(state);

  if (executable === 'ipconfig') {
    if (!networkInterface) {
      return result(state, [
        'Windows IP Configuration',
        '',
        'No adapters found.',
      ]);
    }
    if (normalizedArgs.length === 0 || normalizedArgs[0] === '/all') {
      const all = normalizedArgs[0] === '/all';
      return result(state, [
        'Windows IP Configuration',
        '',
        ...(all
          ? [
              `   Host Name . . . . . . . . . . . . : ${state.machine.hostname}`,
              '   Node Type . . . . . . . . . . . . : Hybrid',
            ]
          : []),
        `${networkInterface.kind === 'wifi' ? 'Wireless LAN' : 'Ethernet'} adapter ${networkInterface.alias}:`,
        `   IPv4 Address. . . . . . . . . . . : ${networkInterface.ipv4.address}`,
        `   Subnet Mask . . . . . . . . . . . : ${netmask(networkInterface.ipv4.prefixLength)}`,
        `   Default Gateway . . . . . . . . . : ${networkInterface.ipv4.gateway}`,
        ...(all
          ? [
              `   DHCP Enabled. . . . . . . . . . . : ${networkInterface.ipv4.dhcpEnabled ? 'Yes' : 'No'}`,
              `   DNS Servers . . . . . . . . . . . : ${networkInterface.dnsServers.join('\n                                       ')}`,
            ]
          : []),
      ]);
    }
    if (normalizedArgs[0] === '/flushdns') {
      return result(
        {
          ...state,
          network: { ...state.network, dnsCache: [] },
        },
        [
          'Windows IP Configuration',
          '',
          'Successfully flushed the DNS Resolver Cache.',
        ],
      );
    }
    if (normalizedArgs[0] === '/displaydns') {
      return result(
        state,
        state.network.dnsCache.length
          ? state.network.dnsCache.flatMap((entry) => [
              `    ${entry.hostname}`,
              `    A (Host) Record . . . . . : ${entry.address}`,
              '',
            ])
          : ['Could not display the DNS Resolver Cache.'],
      );
    }
    if (normalizedArgs[0] === '/release' || normalizedArgs[0] === '/renew') {
      const renewing = normalizedArgs[0] === '/renew';
      const updatedInterface = {
        ...networkInterface,
        status: renewing ? ('up' as const) : ('limited' as const),
        ipv4: {
          ...networkInterface.ipv4,
          address: renewing ? networkInterface.ipv4.address : '0.0.0.0',
          gateway: renewing ? networkInterface.ipv4.gateway : '0.0.0.0',
          leaseObtainedAt: renewing ? timestamp : null,
        },
      };
      return result(
        {
          ...state,
          network: {
            ...state.network,
            internetReachable: renewing,
            interfaces: state.network.interfaces.map((entry) =>
              entry.id === networkInterface.id ? updatedInterface : entry,
            ),
          },
        },
        [
          `Windows IP Configuration`,
          '',
          renewing ? 'DHCP lease renewed.' : 'DHCP lease released.',
        ],
      );
    }
    return result(state, ['The parameter is incorrect.'], false);
  }

  if (
    executable === 'ping' ||
    executable === 'tracert' ||
    executable === 'nslookup'
  ) {
    const target = args[0];
    if (!target) return result(state, [`Usage: ${executable} <host>`], false);
    const address = IPV4.test(target) ? target : resolveHost(state, target);
    const reachable = Boolean(address && canReachIp(state, address));
    const nextState =
      address && !IPV4.test(target)
        ? withDnsCache(state, target, address, timestamp)
        : state;
    if (executable === 'nslookup') {
      const dns = networkInterface?.dnsServers[0] ?? '0.0.0.0';
      return address
        ? result(nextState, [
            'Server:  dns01.nexus.internal',
            `Address:  ${dns}`,
            '',
            `Name:    ${target}`,
            `Address:  ${address}`,
          ])
        : result(
            state,
            [
              'Server:  UnKnown',
              `Address:  ${dns}`,
              '',
              `*** UnKnown can't find ${target}: Request timed out`,
            ],
            false,
          );
    }
    if (!address && !IPV4.test(target)) {
      return result(
        state,
        [
          executable === 'ping'
            ? `Ping request could not find host ${target}. Check the name and try again.`
            : `Unable to resolve target system name ${target}.`,
        ],
        false,
      );
    }
    if (!reachable) {
      return result(
        nextState,
        [
          executable === 'ping'
            ? `Request timed out for ${target}.`
            : `Unable to reach target system ${target}.`,
        ],
        false,
      );
    }
    if (executable === 'tracert') {
      return result(nextState, [
        `Tracing route to ${target} over a maximum of 3 hops:`,
        `  1     1 ms     1 ms     1 ms  ${networkInterface?.ipv4.gateway ?? '0.0.0.0'}`,
        `  2     4 ms     4 ms     5 ms  ${address}`,
        'Trace complete.',
      ]);
    }
    return result(nextState, [
      `Pinging ${target} [${address}] with 32 bytes of data:`,
      `Reply from ${address}: bytes=32 time=4ms TTL=127`,
      `Reply from ${address}: bytes=32 time=5ms TTL=127`,
      '',
      `Ping statistics for ${address}: Sent = 2, Received = 2, Lost = 0 (0% loss),`,
    ]);
  }

  if (executable === 'net' && normalizedArgs[0] === 'use') {
    if (args.length === 1) return result(state, listMappings(state));
    const letter = args[1]?.toUpperCase();
    if (!letter || !DRIVE_LETTER.test(letter)) {
      return result(state, ['Use a drive letter in the form Z:.'], false);
    }
    if (normalizedArgs[2] === '/delete') {
      return deleteWorkstationDrive(state, letter);
    }
    const uncPath = args[2];
    if (!uncPath) return result(state, ['Enter a UNC path to map.'], false);
    const persistent = normalizedArgs.find((arg) =>
      arg.startsWith('/persistent:'),
    );
    if (
      persistent &&
      !['/persistent:yes', '/persistent:no'].includes(persistent)
    ) {
      return result(state, ['Use /persistent:yes or /persistent:no.'], false);
    }
    return mapWorkstationDrive(
      state,
      letter,
      uncPath,
      persistent !== '/persistent:no',
    );
  }

  if (executable === 'cmdkey') {
    if (normalizedArgs[0] === '/list') {
      const credentials = Object.values(state.credentials);
      return result(
        state,
        credentials.length
          ? credentials.flatMap((credential) => [
              `Target: ${credential.target}`,
              `Type: ${credential.type === 'domain-password' ? 'Domain Password' : 'Generic'}`,
              `User: ${credential.username}`,
              '',
            ])
          : ['Currently stored credentials:', '', 'None'],
      );
    }
    const add = args.find((arg) => arg.toLowerCase().startsWith('/add:'));
    const user = args.find((arg) => arg.toLowerCase().startsWith('/user:'));
    const remove = args.find((arg) => arg.toLowerCase().startsWith('/delete:'));
    if (add && user) {
      const target = add.slice('/add:'.length).toLowerCase();
      const username = user.slice('/user:'.length);
      if (!target || !username || !/^[a-z0-9.-]+$/i.test(target)) {
        return result(
          state,
          ['The command line parameters are not valid.'],
          false,
        );
      }
      return result(
        {
          ...state,
          credentials: {
            ...state.credentials,
            [target]: {
              id: `credential-${target.replace(/[^a-z0-9]+/g, '-')}`,
              target,
              username,
              type: 'domain-password',
              persistence: 'local-machine',
              createdAt: timestamp,
            },
          },
        },
        ['CMDKEY: Credential added successfully.'],
      );
    }
    if (remove) {
      const target = remove.slice('/delete:'.length).toLowerCase();
      if (!state.credentials[target]) {
        return result(state, ['CMDKEY: Element not found.'], false);
      }
      const credentials = { ...state.credentials };
      delete credentials[target];
      return result({ ...state, credentials }, [
        'CMDKEY: Credential deleted successfully.',
      ]);
    }
    return result(
      state,
      ['Usage: cmdkey /list | /add:<target> /user:<user> | /delete:<target>'],
      false,
    );
  }

  if (executable === 'whoami')
    return result(state, [state.machine.signedInUser]);
  if (executable === 'hostname') return result(state, [state.machine.hostname]);
  if (
    executable === 'gpupdate' &&
    (args.length === 0 || normalizedArgs[0] === '/force')
  ) {
    return result(state, [
      'Updating policy...',
      'Computer Policy update has completed successfully.',
      'User Policy update has completed successfully.',
    ]);
  }
  if (executable === 'systeminfo') {
    return result(state, [
      `Host Name:                 ${state.machine.hostname}`,
      `OS Name:                   ${state.machine.operatingSystem}`,
      `OS Version:                ${state.machine.build}`,
      `System Model:              ${state.machine.model}`,
      `Domain:                    ${state.machine.domain}`,
    ]);
  }
  if (executable === 'tasklist') {
    const services = Object.values(state.services)
      .filter((service) => service.state === 'running')
      .map(
        (service, index) =>
          `${service.name.replace(/\s+/g, '').slice(0, 18).padEnd(25)} ${String(1200 + index).padStart(5)} Console                    1     12,000 K`,
      );
    return result(state, [
      'Image Name                     PID Session Name        Session#    Mem Usage',
      '========================= ======== ================ =========== ============',
      'explorer.exe                  1040 Console                    1     48,000 K',
      ...services,
    ]);
  }
  if (executable === 'sc' && normalizedArgs[0] === 'query') {
    const service = serviceByName(state, args.slice(1).join(' '));
    return service
      ? result(state, serviceQuery(service))
      : result(
          state,
          [
            '[SC] OpenService FAILED 1060: The specified service does not exist as an installed service.',
          ],
          false,
        );
  }
  if (
    executable === 'net' &&
    (normalizedArgs[0] === 'start' || normalizedArgs[0] === 'stop')
  ) {
    const service = serviceByName(state, args.slice(1).join(' '));
    if (!service) return result(state, ['The service name is invalid.'], false);
    const nextState = normalizedArgs[0] === 'start' ? 'running' : 'stopped';
    return result(
      {
        ...state,
        services: {
          ...state.services,
          [service.name]: { ...service, state: nextState },
        },
      },
      [
        `The ${service.name} service was ${nextState === 'running' ? 'started' : 'stopped'} successfully.`,
      ],
    );
  }
  if (executable === 'cls') return result(state, []);
  if (executable === 'help') {
    return result(state, [
      'Supported commands:',
      'ipconfig [/all|/release|/renew|/displaydns|/flushdns]',
      'ping <host>, nslookup <host>, tracert <host>',
      'net use [<drive>: <UNC> [/persistent:yes|no] | <drive>: /delete]',
      'cmdkey [/list|/add:<target> /user:<user>|/delete:<target>]',
      'whoami, hostname, gpupdate /force, systeminfo, tasklist',
      'sc query <service>, net start <service>, net stop <service>, cls, help',
    ]);
  }
  return result(
    state,
    [
      `'${command.trim()}' is not recognized as an internal or external command, operable program or batch file.`,
    ],
    false,
  );
}
