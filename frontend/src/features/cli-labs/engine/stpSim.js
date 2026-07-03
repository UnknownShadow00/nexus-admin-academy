import { channelSummary, portChannelForMember } from "./etherchannel.js";
import { parseLinkEndpoint } from "./trunking.js";

const DEFAULT_PRIORITY = 32768;
const ROOT_PRIMARY_PRIORITY = 24576;
const ROOT_SECONDARY_PRIORITY = 28672;
const PRIORITY_STEP = 4096;
const MAX_PRIORITY = 61440;

function ensureStp(state) {
  state.stp = state.stp || { mode: "pvst", priorities: {} };
  state.stp.priorities = state.stp.priorities || {};
  return state.stp;
}

function vlanPriority(state, vlanId) {
  return Number(ensureStp(state).priorities[String(vlanId)] ?? DEFAULT_PRIORITY);
}

function bridgePriority(state, vlanId) {
  return vlanPriority(state, vlanId) + Number(vlanId);
}

function bridgeMac(deviceId = "Switch") {
  const trailing = String(deviceId).match(/(\d+)$/)?.[1];
  const value = trailing ? Number(trailing) : [...String(deviceId)].reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return `001b.0c00.${(value % 65536).toString(16).padStart(4, "0")}`;
}

function switchIds(context = {}) {
  const fromTopology = (context.topology?.devices || []).filter((device) => device.type === "switch").map((device) => device.id);
  return fromTopology.length ? fromTopology : Object.keys(context.deviceStates || {});
}

function bridgeIdFor(context, deviceId, vlanId) {
  const state = context.deviceStates?.[deviceId];
  return { deviceId, priority: bridgePriority(state || {}, vlanId), mac: bridgeMac(deviceId) };
}

function rootBridge(context, vlanId) {
  return switchIds(context)
    .map((deviceId) => bridgeIdFor(context, deviceId, vlanId))
    .sort((a, b) => a.priority - b.priority || a.mac.localeCompare(b.mac))[0];
}

function portNumber(name = "") {
  return Number(String(name).match(/(\d+)$/)?.[1] || 0);
}

function displayPort(name) {
  return name.startsWith("Po") ? name : `Gi${name.slice(1)}`;
}

function normalizeIfName(raw = "") {
  const compact = String(raw).replace(/\s+/g, "");
  return compact.replace(/^port-channel/i, "Po").replace(/^po/i, "Po").replace(/^gigabitethernet/i, "g").replace(/^g/i, "g");
}

function validVlanId(vlanId) {
  const value = Number(vlanId);
  return /^\d+$/.test(String(vlanId)) && Number.isInteger(value) && value >= 1 && value <= 4094;
}

function localLinks(context = {}) {
  return (context.topology?.links || []).flatMap((link) => {
    const a = parseLinkEndpoint(link.a);
    const b = parseLinkEndpoint(link.b);
    if (!a || !b) return [];
    if (a.deviceId === context.deviceId) return [{ local: a, remote: b }];
    if (b.deviceId === context.deviceId) return [{ local: b, remote: a }];
    return [];
  });
}

function linkedToSwitch(context, localName) {
  return localLinks(context).some((link) => link.local.interface === localName && context.deviceStates?.[link.remote.deviceId]);
}

function pcReferencesLocalPort(pc = {}, context = {}, localName) {
  const connectedTo = String(pc.connectedTo || "");
  if (!connectedTo) return false;
  if (connectedTo.includes(":")) {
    const endpoint = parseLinkEndpoint(connectedTo);
    return endpoint?.deviceId === context.deviceId && endpoint.interface === localName;
  }
  const pcSwitch = pc.switch || pc.switchId;
  const sameSwitch = !context.deviceId || !pcSwitch || pcSwitch === context.deviceId;
  return sameSwitch && normalizeIfName(connectedTo) === localName;
}

function hasConnectedPc(state, context, localName) {
  const topologyPcs = (context.topology?.devices || []).filter((device) => device.type === "pc");
  return [...(state.pcDevices || []), ...topologyPcs].some((pc) => pcReferencesLocalPort(pc, context, localName));
}

function activeStpPorts(state, context, vlanId) {
  const seen = new Set();
  const switchLinkPorts = new Set();
  const rows = [];
  for (const link of localLinks(context)) {
    switchLinkPorts.add(link.local.interface);
    const iface = state.interfaces?.[link.local.interface];
    if (!iface || iface.shutdown || iface.errDisabled) continue;
    const po = portChannelForMember(state, context, link.local.interface);
    const port = po || link.local.interface;
    if (seen.has(port)) continue;
    seen.add(port);
    rows.push({ port, remoteDevice: link.remote.deviceId, edge: Boolean(iface.portfast), vlanId });
  }
  for (const [name, iface] of Object.entries(state.interfaces || {})) {
    if (seen.has(name) || switchLinkPorts.has(name) || name.startsWith("Vlan") || name.startsWith("Po")) continue;
    if (!iface || iface.shutdown || iface.errDisabled) continue;
    if (!iface.portfast && !hasConnectedPc(state, context, name)) continue;
    seen.add(name);
    rows.push({ port: name, remoteDevice: null, edge: Boolean(iface.portfast), vlanId });
  }
  return rows.sort((a, b) => portNumber(a.port) - portNumber(b.port));
}

function annotateRoles(state, context, vlanId) {
  const root = rootBridge(context, vlanId) || bridgeIdFor(context, context.deviceId, vlanId);
  const rows = activeStpPorts(state, context, vlanId);
  if (context.deviceId === root.deviceId) return rows.map((row) => ({ ...row, role: "Desg", state: "FWD" }));
  const rootFacing = rows.filter((row) => row.remoteDevice === root.deviceId);
  const rootPort = rootFacing[0]?.port;
  return rows.map((row) => {
    if (row.port === rootPort) return { ...row, role: "Root", state: "FWD" };
    if (row.remoteDevice === root.deviceId && rootFacing.length > 1) return { ...row, role: "Altn", state: "BLK" };
    return { ...row, role: "Desg", state: "FWD" };
  });
}

function renderVlan(state, context, vlanId) {
  const stp = ensureStp(state);
  const root = rootBridge(context, vlanId) || bridgeIdFor(context, context.deviceId, vlanId);
  const local = bridgeIdFor({ ...context, deviceStates: { ...context.deviceStates, [context.deviceId]: state } }, context.deviceId, vlanId);
  const protocol = stp.mode === "rapid-pvst" ? "rstp" : "ieee";
  const lines = [
    `VLAN${String(vlanId).padStart(4, "0")}`,
    `  Spanning tree enabled protocol ${protocol}`,
    "  Root ID    Priority    " + root.priority,
    "             Address     " + root.mac,
  ];
  if (root.deviceId === context.deviceId) lines.push("             This bridge is the root");
  lines.push(
    "",
    "  Bridge ID  Priority    " + local.priority,
    "             Address     " + local.mac,
    "",
    "Interface           Role Sts Cost      Prio.Nbr Type"
  );
  for (const row of annotateRoles(state, context, vlanId)) {
    const type = row.edge ? "P2p Edge" : "P2p";
    lines.push(`${displayPort(row.port).padEnd(20)}${row.role.padEnd(5)}${row.state.padEnd(4)}4         128.${portNumber(row.port).toString().padEnd(7)}${type}`);
  }
  return lines;
}

export function renderSpanningTree(state, context = {}, vlanId = "1") {
  if (vlanId && !validVlanId(vlanId)) {
    return ["% Invalid input detected at '^' marker."];
  }
  return renderVlan(state, context, Number(vlanId));
}

export function setStpMode(state, mode) {
  if (!["pvst", "rapid-pvst"].includes(mode)) return { output: ["% Invalid input detected at '^' marker."] };
  ensureStp(state).mode = mode;
  state.saved = false;
  return { output: [], event: "config.stp-mode.set", eventArg: mode };
}

export function setStpPriority(state, vlanId, priority) {
  const value = Number(priority);
  if (!validVlanId(vlanId) || !Number.isInteger(value) || value < 0 || value > MAX_PRIORITY || value % PRIORITY_STEP !== 0) {
    return { output: ["% Invalid input detected at '^' marker."] };
  }
  ensureStp(state).priorities[String(Number(vlanId))] = value;
  state.saved = false;
  return { output: [], event: "config.stp-priority.set", eventArg: String(value) };
}

export function setRootPriority(state, vlanId, type) {
  if (!validVlanId(vlanId)) return { output: ["% Invalid input detected at '^' marker."] };
  const value = type === "secondary" ? ROOT_SECONDARY_PRIORITY : ROOT_PRIMARY_PRIORITY;
  ensureStp(state).priorities[String(Number(vlanId))] = value;
  state.saved = false;
  return { output: [], event: `config.stp-root.${type}`, eventArg: String(vlanId) };
}

function evaluateBpduGuard(state, context, names) {
  for (const name of names) {
    const iface = state.interfaces[name];
    if (iface?.portfast && iface?.bpduguard && linkedToSwitch(context, name)) iface.errDisabled = true;
  }
}

export function stpBlocksPort(state, context, name, vlanId = 1) {
  return annotateRoles(state, context, vlanId).some((row) => row.port === name && row.state === "BLK");
}

export function activeStpPortNames(state, context, vlanId = 1) {
  return annotateRoles(state, context, vlanId).filter((row) => row.state !== "BLK").map((row) => row.port);
}

export function STP_COMMANDS(activeInterfaceNames) {
  return [
    {
      canonical: "spanning-tree mode",
      validModes: ["config"],
      takesArg: true,
      handler: (state, args) => {
        if (!args[0]) return { output: ["% Incomplete command."] };
        if (args.length !== 1) return { output: ["% Invalid input detected at '^' marker."] };
        return setStpMode(state, args[0]);
      },
    },
    {
      canonical: "spanning-tree vlan",
      validModes: ["config"],
      takesRawArg: true,
      handler: (state, _args, raw) => {
        if (!raw) return { output: ["% Incomplete command."] };
        if (/^\d+$/i.test(raw) || /^\d+\s+priority$/i.test(raw) || /^\d+\s+root$/i.test(raw)) {
          return { output: ["% Incomplete command."] };
        }
        const priority = raw.match(/^(\d+)\s+priority\s+(\d+)$/i);
        if (priority) return setStpPriority(state, priority[1], priority[2]);
        const root = raw.match(/^(\d+)\s+root\s+(primary|secondary)$/i);
        if (root) return setRootPriority(state, root[1], root[2].toLowerCase());
        return { output: ["% Invalid input detected at '^' marker."] };
      },
    },
    {
      canonical: "spanning-tree portfast",
      validModes: ["interface", "interface-range"],
      handler: (state, _args, _raw, context) => {
        const names = activeInterfaceNames(state);
        for (const name of names) state.interfaces[name].portfast = true;
        evaluateBpduGuard(state, context, names);
        state.saved = false;
        return { output: [], event: "config.portfast.set" };
      },
    },
    {
      canonical: "spanning-tree bpduguard enable",
      validModes: ["interface", "interface-range"],
      handler: (state, _args, _raw, context) => {
        const names = activeInterfaceNames(state);
        for (const name of names) state.interfaces[name].bpduguard = true;
        evaluateBpduGuard(state, context, names);
        state.saved = false;
        return { output: [], event: "config.bpduguard.set" };
      },
    },
    {
      canonical: "show spanning-tree vlan",
      aliasPrefixes: ["sh spanning-tree vlan"],
      validModes: ["privileged"],
      takesArg: true,
      handler: (state, args, _raw, context) => {
        if (!args[0]) return { output: ["% Incomplete command."] };
        if (args.length !== 1) return { output: ["% Invalid input detected at '^' marker."] };
        return { output: renderSpanningTree(state, context, args[0]), event: "cmd.show.spanning-tree", eventArg: args[0] };
      },
    },
    {
      canonical: "show spanning-tree",
      aliasPrefixes: ["sh spanning-tree"],
      validModes: ["privileged"],
      handler: (state, args, _raw, context) => {
        if (args.length) return { output: ["% Invalid input detected at '^' marker."] };
        return { output: renderSpanningTree(state, context), event: "cmd.show.spanning-tree" };
      },
    },
  ];
}
