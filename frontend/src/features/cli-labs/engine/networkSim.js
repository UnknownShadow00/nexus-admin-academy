import { normalizeIfName } from "./interfaceCommands.js";
import { isOperationalTrunk, parseLinkEndpoint, vlanAllowed } from "./trunking.js";

function pingFailure(source, rawCommand) {
  return {
    output: ["Request timed out.", "Request timed out.", "Request timed out.", "Request timed out.", "Ping statistics: 4 sent, 0 received, 4 lost"],
    events: [{ id: "pc.ping.failed", arg: rawCommand, device: source?.id }],
    event: "pc.ping.failed",
  };
}

function pingSuccess(source, target, rawCommand, transcript) {
  return {
    output: [
      ...transcript,
      `Reply from ${target.ip}: bytes=32 time<1ms TTL=128`,
      `Reply from ${target.ip}: bytes=32 time<1ms TTL=128`,
      `Reply from ${target.ip}: bytes=32 time<1ms TTL=128`,
      `Reply from ${target.ip}: bytes=32 time<1ms TTL=128`,
      "Ping statistics: 4 sent, 4 received, 0 lost",
    ],
    events: [{ id: "pc.ping.success", arg: rawCommand, device: source.id }],
    event: "pc.ping.success",
  };
}

function pcsById(deviceStates) {
  const rows = [];
  for (const [switchId, state] of Object.entries(deviceStates || {})) {
    for (const pc of state.pcDevices || []) rows.push({ ...pc, switch: pc.switch || switchId });
  }
  return rows;
}

function findPc(deviceStates, sourcePcId, targetIp) {
  const pcs = pcsById(deviceStates);
  const source = pcs.find((pc) => pc.id?.toLowerCase() === sourcePcId?.toLowerCase());
  const target = pcs.find((pc) => pc.ip === targetIp && pc.id !== source?.id);
  return { source, target };
}

function accessPort(deviceStates, pc) {
  const state = deviceStates[pc.switch];
  const iface = state?.interfaces?.[normalizeIfName(pc.connectedTo)];
  const vlan = Number(iface?.accessVlan || pc.vlan || 1);
  return { state, iface, vlan, port: normalizeIfName(pc.connectedTo) };
}

function learnMac(state, mac, vlan, port) {
  if (!state.macTable) state.macTable = [];
  const existing = state.macTable.find((entry) => entry.mac.toLowerCase() === mac.toLowerCase() && entry.type === "DYNAMIC");
  if (existing) {
    existing.vlan = vlan;
    existing.port = port;
    return;
  }
  state.macTable.push({ mac, vlan, port, type: "DYNAMIC" });
}

function linkEndpoints(link) {
  const a = parseLinkEndpoint(link.a);
  const b = parseLinkEndpoint(link.b);
  return a && b ? [a, b] : null;
}

function findDirectLink(topology, sourceSwitch, targetSwitch) {
  for (const link of topology?.links || []) {
    const endpoints = linkEndpoints(link);
    if (!endpoints) continue;
    const [a, b] = endpoints;
    if (
      (a.deviceId === sourceSwitch && b.deviceId === targetSwitch) ||
      (b.deviceId === sourceSwitch && a.deviceId === targetSwitch)
    ) {
      return a.deviceId === sourceSwitch ? { link, local: a, remote: b } : { link, local: b, remote: a };
    }
  }
  return null;
}

function trunkPasses(deviceStates, link, vlan) {
  const localIface = deviceStates[link.local.deviceId]?.interfaces?.[link.local.interface];
  const remoteIface = deviceStates[link.remote.deviceId]?.interfaces?.[link.remote.interface];
  if (!localIface || !remoteIface) return false;
  if (!isOperationalTrunk(localIface, remoteIface)) return false;
  if (localIface.encapsulationRequired && localIface.trunkEncapsulation !== "dot1q") return false;
  if (remoteIface.encapsulationRequired && remoteIface.trunkEncapsulation !== "dot1q") return false;
  if (!vlanAllowed(localIface, vlan) || !vlanAllowed(remoteIface, vlan)) return false;
  const localNative = Number(localIface.nativeVlan || 1);
  const remoteNative = Number(remoteIface.nativeVlan || 1);
  if ((Number(vlan) === localNative || Number(vlan) === remoteNative) && localNative !== remoteNative) return false;
  return true;
}

function transcript(source, target, vlan, link) {
  if (source.switch === target.switch) {
    return [
      `ARP request: who has ${target.ip}? tell ${source.ip} (broadcast ffff.ffff.ffff)`,
      `ARP reply: ${target.ip} is at ${target.mac}`,
    ];
  }
  const native = Number(link.localIface?.nativeVlan || 1) === Number(vlan);
  return [
    `Access ingress on ${source.switch} ${source.connectedTo} (VLAN ${vlan}, untagged)`,
    native ? `Native VLAN ${vlan} crosses ${source.switch} ${link.local.interface} untagged` : `802.1Q tag VLAN ${vlan} added on ${source.switch} ${link.local.interface}`,
    `Frame crosses trunk to ${target.switch} ${link.remote.interface}`,
    native ? `Native VLAN ${vlan} accepted on ${target.switch} ${link.remote.interface}` : `802.1Q tag removed at ${target.switch} ${link.remote.interface}`,
    `Access egress on ${target.switch} ${target.connectedTo}`,
  ];
}

export function evaluatePcPing(deviceStates, topology, sourcePcId, targetIp, rawCommand = `ping ${targetIp}`) {
  const { source, target } = findPc(deviceStates, sourcePcId, targetIp);
  if (!source || !target) return pingFailure(source, rawCommand);
  const sourceAccess = accessPort(deviceStates, source);
  const targetAccess = accessPort(deviceStates, target);
  const sourceState = sourceAccess.state;
  if (!sourceAccess.iface || !targetAccess.iface || sourceAccess.iface.shutdown || targetAccess.iface.shutdown) return pingFailure(source, rawCommand);
  if (sourceAccess.vlan !== targetAccess.vlan) return pingFailure(source, rawCommand);

  sourceState.commandLog.push({ cmd: `${source.id}: ${rawCommand}`, canonical: "pc", ts: Date.now() });
  sourceState.pcActions.push(rawCommand);

  let link = null;
  if (source.switch !== target.switch) {
    link = findDirectLink(topology, source.switch, target.switch);
    if (!link || !trunkPasses(deviceStates, link, sourceAccess.vlan)) return pingFailure(source, rawCommand);
    link.localIface = deviceStates[link.local.deviceId].interfaces[link.local.interface];
  }

  learnMac(sourceAccess.state, source.mac, sourceAccess.vlan, sourceAccess.port);
  learnMac(targetAccess.state, target.mac, targetAccess.vlan, targetAccess.port);
  if (link) {
    learnMac(sourceAccess.state, target.mac, sourceAccess.vlan, link.local.interface);
    learnMac(targetAccess.state, source.mac, targetAccess.vlan, link.remote.interface);
  } else {
    learnMac(sourceAccess.state, target.mac, targetAccess.vlan, targetAccess.port);
  }
  return pingSuccess(source, target, rawCommand, transcript(source, target, sourceAccess.vlan, link));
}

export function runMultiPcCommand(deviceStates, topology, rawInput, explicitSourceId = null) {
  const trimmed = rawInput.trim();
  const prefixed = trimmed.match(/^(pc-[a-z0-9]+)\s*[:>]\s*(.+)$/i) || trimmed.match(/^(pc-[a-z0-9]+)\s+(.+)$/i);
  const sourceId = explicitSourceId || prefixed?.[1]?.toUpperCase();
  const command = (prefixed ? prefixed[2] : trimmed).trim();
  const pingMatch = command.match(/^ping\s+(\S+)$/i);
  if (pingMatch) return evaluatePcPing(deviceStates, topology, sourceId, pingMatch[1], command);
  return { output: ["Command not available in this PC terminal."], events: [{ id: "error.unknown-command", arg: command, device: sourceId }] };
}
