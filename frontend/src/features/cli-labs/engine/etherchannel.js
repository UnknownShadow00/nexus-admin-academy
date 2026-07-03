const CHANNEL_MODES = ["active", "passive", "on", "desirable", "auto"];

function normalizeIfName(raw = "") {
  const compact = raw.replace(/\s+/g, "");
  return compact.replace(/^port-channel/i, "Po").replace(/^po/i, "Po").replace(/^gigabitethernet/i, "g").replace(/^g/i, "g");
}

function parseEndpoint(endpoint = "") {
  const [deviceId, iface] = String(endpoint).split(":");
  return deviceId && iface ? { deviceId, interface: normalizeIfName(iface) } : null;
}

function portChannelName(group) {
  return `Po${Number(group)}`;
}

function invalidInput() {
  return { output: ["% Invalid input detected at '^' marker."] };
}

function incompleteCommand() {
  return { output: ["% Incomplete command."] };
}

function interfaceNumber(name = "") {
  return Number(String(name).match(/(\d+)$/)?.[1] || 0);
}

function modeProtocol(localMode, remoteMode) {
  if (localMode === "on" && remoteMode === "on") return "Static";
  if (["active", "passive"].includes(localMode) && ["active", "passive"].includes(remoteMode)) {
    return localMode === "active" || remoteMode === "active" ? "LACP" : null;
  }
  if (["desirable", "auto"].includes(localMode) && ["desirable", "auto"].includes(remoteMode)) {
    return localMode === "desirable" || remoteMode === "desirable" ? "PAgP" : null;
  }
  return null;
}

function linksForDevice(topology = {}, deviceId) {
  return (topology.links || []).flatMap((link) => {
    const a = parseEndpoint(link.a);
    const b = parseEndpoint(link.b);
    if (!a || !b) return [];
    if (a.deviceId === deviceId) return [{ link, local: a, remote: b }];
    if (b.deviceId === deviceId) return [{ link, local: b, remote: a }];
    return [];
  });
}

export function channelMembers(state = {}, group) {
  return Object.entries(state.interfaces || {})
    .filter(([name, iface]) => !name.startsWith("Vlan") && !name.startsWith("Po") && Number(iface.channelGroup) === Number(group))
    .map(([name]) => name)
    .sort((a, b) => interfaceNumber(a) - interfaceNumber(b));
}

export function channelGroups(state = {}) {
  return [...new Set(Object.values(state.interfaces || {}).map((iface) => iface.channelGroup).filter(Boolean))].sort((a, b) => Number(a) - Number(b));
}

function matchedMemberRows(state, context, group) {
  const rows = [];
  for (const localName of channelMembers(state, group)) {
    const match = linksForDevice(context.topology, context.deviceId).find((item) => item.local.interface === localName);
    if (!match) continue;
    const remoteState = context.deviceStates?.[match.remote.deviceId];
    const remoteIface = remoteState?.interfaces?.[match.remote.interface];
    rows.push({ localName, localIface: state.interfaces[localName], remote: match.remote, remoteIface });
  }
  return rows;
}

function peerHostname(context = {}, deviceId) {
  const device = (context.topology?.devices || []).find((item) => item.id === deviceId);
  return context.deviceStates?.[deviceId]?.hostname || device?.hostname || device?.label || deviceId;
}

export function channelSummary(state = {}, context = {}, group) {
  const members = channelMembers(state, group);
  const firstMode = state.interfaces?.[members[0]]?.channelMode;
  const poName = portChannelName(group);
  const rows = matchedMemberRows(state, context, group);
  const remoteModes = rows.map((row) => row.remoteIface?.channelMode).filter(Boolean);
  const sameLocalMode = members.every((name) => state.interfaces[name]?.channelMode === firstMode);
  const sameRemoteGroup = rows.length === members.length && rows.every((row) => Number(row.remoteIface?.channelGroup) === Number(group));
  const sameRemoteMode = remoteModes.length > 0 && remoteModes.every((mode) => mode === remoteModes[0]);
  const protocol = sameLocalMode && sameRemoteGroup && sameRemoteMode ? modeProtocol(firstMode, remoteModes[0]) : null;
  const configuredPair = members.length >= 2 && rows.length >= 2 && rows.every((row) => row.remoteIface);
  const channelShutdown =
    Boolean(state.interfaces?.[poName]?.shutdown || state.interfaces?.[poName]?.errDisabled) ||
    rows.some((row) => {
      const remotePo = context.deviceStates?.[row.remote.deviceId]?.interfaces?.[poName];
      return remotePo?.shutdown || remotePo?.errDisabled;
    });
  const upMembers = channelShutdown
    ? []
    : rows.filter((row) => !row.localIface.shutdown && !row.localIface.errDisabled && !row.remoteIface?.shutdown && !row.remoteIface?.errDisabled);
  const bundledMembers = protocol && configuredPair ? upMembers.map((row) => row.localName) : [];
  return {
    group: Number(group),
    name: poName,
    members,
    protocol: protocol || "-",
    formed: Boolean(protocol && configuredPair),
    up: bundledMembers.length > 0,
    upMembers: bundledMembers,
    channelShutdown,
  };
}

export function isBundledMember(state, context, name) {
  const iface = state.interfaces?.[normalizeIfName(name)];
  if (!iface?.channelGroup) return false;
  return channelSummary(state, context, iface.channelGroup).upMembers.includes(normalizeIfName(name));
}

export function effectiveInterface(state, context, name) {
  const normalized = normalizeIfName(name);
  const iface = state.interfaces?.[normalized];
  if (iface?.channelGroup) {
    const poIface = state.interfaces?.[portChannelName(iface.channelGroup)];
    if (poIface?.shutdown || poIface?.errDisabled) return { ...iface, shutdown: true };
  }
  if (!iface?.channelGroup || !isBundledMember(state, context, normalized)) return iface;
  return { ...iface, ...(state.interfaces?.[portChannelName(iface.channelGroup)] || {}) };
}

export function portChannelForMember(state, context, name) {
  const iface = state.interfaces?.[normalizeIfName(name)];
  return iface?.channelGroup && isBundledMember(state, context, name) ? portChannelName(iface.channelGroup) : null;
}

export function applyChannelGroup(state, names, group, mode) {
  if (!CHANNEL_MODES.includes(mode)) return invalidInput();
  if (!Number.isInteger(Number(group)) || Number(group) < 1) return invalidInput();
  const poName = portChannelName(group);
  state.interfaces[poName] = state.interfaces[poName] || { shutdown: false };
  for (const name of names) {
    state.interfaces[name].channelGroup = Number(group);
    state.interfaces[name].channelMode = mode;
  }
  state.saved = false;
  return { output: [], event: "config.channel-group.set", eventArg: String(group) };
}

export function removeChannelGroup(state, names, group) {
  for (const name of names) {
    if (!group || Number(state.interfaces[name].channelGroup) === Number(group)) {
      delete state.interfaces[name].channelGroup;
      delete state.interfaces[name].channelMode;
    }
  }
  state.saved = false;
  return { output: [], event: "config.channel-group.removed", eventArg: group ? String(group) : "" };
}

function displayPort(name) {
  return name.startsWith("Po") ? name : `Gi${name.slice(1)}`;
}

function memberFlag(state, summary, name, row = null) {
  const iface = state.interfaces?.[name] || {};
  if (summary.channelShutdown || iface.shutdown || iface.errDisabled || row?.remoteIface?.shutdown || row?.remoteIface?.errDisabled) return "D";
  return summary.upMembers.includes(name) ? "P" : "s";
}

export function renderEtherChannelSummary(state = {}, context = {}) {
  const lines = [
    "Flags:  D - down        P - bundled in port-channel",
    "        s - suspended   U - in use",
    "",
    "Group  Port-channel  Protocol    Ports",
  ];
  for (const group of channelGroups(state)) {
    const summary = channelSummary(state, context, group);
    const rowsByName = new Map(matchedMemberRows(state, context, group).map((row) => [row.localName, row]));
    const flags = summary.up ? "SU" : "SD";
    const ports = summary.members
      .map((name) => `${displayPort(name)}(${memberFlag(state, summary, name, rowsByName.get(name))})`)
      .join(" ");
    lines.push(`${String(group).padEnd(7)}${`${summary.name}(${flags})`.padEnd(14)}${summary.protocol.padEnd(12)}${ports}`);
  }
  return lines;
}

export function renderEtherChannelDetail(state = {}, context = {}) {
  const lines = [
    "Flags:  D - down        P - bundled in port-channel",
    "        s - suspended   U - in use",
    "",
  ];
  for (const group of channelGroups(state)) {
    const summary = channelSummary(state, context, group);
    const rowsByName = new Map(matchedMemberRows(state, context, group).map((row) => [row.localName, row]));
    lines.push(
      `Group: ${group}`,
      "----------",
      `Port-channel: ${summary.name} (${summary.up ? "SU" : "SD"})`,
      `Protocol: ${summary.protocol}`,
      "Member Ports:"
    );
    for (const name of summary.members) {
      const row = rowsByName.get(name);
      const partner = row?.remote ? `${peerHostname(context, row.remote.deviceId)} ${displayPort(row.remote.interface)}` : "-";
      lines.push(`  ${displayPort(name).padEnd(8)} Flags: ${memberFlag(state, summary, name, row).padEnd(2)} Partner: ${partner}`);
    }
    lines.push("");
  }
  return lines.at(-1) === "" ? lines.slice(0, -1) : lines;
}

export function renderProtocolNeighbors(state = {}, context = {}, protocol = "LACP") {
  const lines = [
    `${protocol} neighbor information:`,
    "Port      Partner Dev ID  Partner Port  Group  Flags",
  ];
  for (const group of channelGroups(state)) {
    const summary = channelSummary(state, context, group);
    if (summary.protocol !== protocol || !summary.formed) continue;
    for (const row of matchedMemberRows(state, context, group)) {
      const flag = memberFlag(state, summary, row.localName, row);
      lines.push(
        `${displayPort(row.localName).padEnd(10)}${peerHostname(context, row.remote.deviceId).padEnd(16)}${displayPort(row.remote.interface).padEnd(14)}${String(group).padEnd(7)}${flag}`
      );
    }
  }
  return lines;
}

function setMode(state, mode) {
  state.mode = mode;
  if (!state.visitedModes.includes(mode)) state.visitedModes.push(mode);
}

export function ETHERCHANNEL_COMMANDS(activeInterfaceNames) {
  return [
    {
      canonical: "interface port-channel",
      aliasPrefixes: ["int port-channel", "interface po", "int po"],
      validModes: ["config", "interface", "interface-range"],
      takesArg: true,
      handler: (state, args) => {
        if (!args[0]) return incompleteCommand();
        if (args.length !== 1 || !/^\d+$/.test(args[0])) return invalidInput();
        const name = portChannelName(args[0]);
        state.interfaces[name] = state.interfaces[name] || { shutdown: false };
        setMode(state, "interface");
        state.activeInterface = name;
        state.activeInterfaceRange = null;
        state.activeInterfaceRangeLabel = null;
        return { output: [], event: "mode.interface.enter", eventArg: name };
      },
    },
    {
      canonical: "channel-group",
      validModes: ["interface", "interface-range"],
      takesArg: true,
      handler: (state, args) => {
        if (args.length < 3 || args[1]?.toLowerCase() !== "mode") return incompleteCommand();
        if (args.length !== 3) return invalidInput();
        return applyChannelGroup(state, activeInterfaceNames(state), args[0], args[2].toLowerCase());
      },
    },
    {
      canonical: "no channel-group",
      validModes: ["interface", "interface-range"],
      takesArg: true,
      handler: (state, args) => {
        if (!args[0]) return incompleteCommand();
        if (args.length !== 1 || !/^\d+$/.test(args[0])) return invalidInput();
        return removeChannelGroup(state, activeInterfaceNames(state), args[0]);
      },
    },
    {
      canonical: "show etherchannel summary",
      aliasPrefixes: ["sh etherchannel summary"],
      validModes: ["privileged"],
      handler: (state, args, _raw, context) => {
        if (args.length) return invalidInput();
        return { output: renderEtherChannelSummary(state, context), event: "cmd.show.etherchannel-summary" };
      },
    },
    {
      canonical: "show etherchannel detail",
      aliasPrefixes: ["sh etherchannel detail"],
      validModes: ["privileged"],
      handler: (state, args, _raw, context) => {
        if (args.length) return invalidInput();
        return { output: renderEtherChannelDetail(state, context), event: "cmd.show.etherchannel-detail" };
      },
    },
    {
      canonical: "show lacp neighbor",
      aliasPrefixes: ["show lacp neighbors", "sh lacp neighbor", "sh lacp neighbors"],
      validModes: ["privileged"],
      handler: (state, args, _raw, context) => {
        if (args.length) return invalidInput();
        return { output: renderProtocolNeighbors(state, context, "LACP"), event: "cmd.show.lacp-neighbor" };
      },
    },
    {
      canonical: "show pagp neighbor",
      aliasPrefixes: ["show pagp neighbors", "sh pagp neighbor", "sh pagp neighbors"],
      validModes: ["privileged"],
      handler: (state, args, _raw, context) => {
        if (args.length) return invalidInput();
        return { output: renderProtocolNeighbors(state, context, "PAgP"), event: "cmd.show.pagp-neighbor" };
      },
    },
  ];
}
