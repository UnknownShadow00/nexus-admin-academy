import { fakePcMac, removeStaticMac, renderMacAddressTable, setStaticMac } from "./macTable.js";
import {
  activeInterfaceNames,
  applyAccessVlan,
  ensureInterface,
  ensureVlan,
  normalizeIfName,
  parseInterfaceRange,
  renderInterfaces,
  renderInterfacesSwitchport,
  renderInterfacesTrunk,
  renderInterfaceStatus,
  renderRunningConfig,
  renderRunningConfigInterface,
  renderShowVersion,
  renderVlanBrief,
} from "./interfaceCommands.js";
import { isValidAllowedVlanList, normalizeAllowedVlans, renderNeighborTable } from "./trunking.js";
import { ETHERCHANNEL_COMMANDS } from "./etherchannel.js";
import { STP_COMMANDS } from "./stpSim.js";
export { redactCommandLog, runPcCommand } from "./pcCommands.js";
export { SUPPORTED_EVENT_IDS } from "./supportedEvents.js";

const PROMPTS = {
  user: (hostname) => `${hostname}>`,
  privileged: (hostname) => `${hostname}#`,
  config: (hostname) => `${hostname}(config)#`,
  interface: (hostname) => `${hostname}(config-if)#`,
  "interface-range": (hostname) => `${hostname}(config-if-range)#`,
  vlan: (hostname) => `${hostname}(config-vlan)#`,
  line: (hostname) => `${hostname}(config-line)#`,
};
const KNOWN_AMBIGUOUS = ["sh st", "show st"];

function baseState() {
  return {
    hostname: "Switch",
    mode: "user",
    visitedModes: ["user"],
    activeInterface: null,
    activeInterfaceRange: null,
    activeInterfaceRangeLabel: null,
    activeVlan: null,
    activeLine: null,
    pendingAuth: null,
    enablePassword: null,
    enableSecret: null,
    consolePassword: null,
    consoleLogin: false,
    vtyPassword: null,
    vtyLogin: false,
    vtyLoginLocal: false,
    vtyTransportInput: "telnet",
    bannerSet: false,
    bannerText: null,
    domainName: null,
    rsaGenerated: false,
    rsaModulus: null,
    vlan1Ip: null,
    users: [],
    vlans: { "1": { name: "default", ports: ["g0/1", "g0/2", "g0/3", "g0/4", "Vlan1"] } },
    macTable: [],
    arpCaches: {},
    pcDevices: [],
    interfaces: {
      "g0/1": { mode: "access", accessVlan: 1, shutdown: false, label: "Admin PC" },
      "g0/2": { mode: "access", accessVlan: 1, shutdown: false, label: "Test PC" },
      "g0/3": { mode: "access", accessVlan: 1, shutdown: true },
      "g0/4": { mode: "access", accessVlan: 1, shutdown: true },
      Vlan1: { ip: null, mask: null, shutdown: true },
    },
    saved: true,
    commandLog: [],
    pcActions: [],
  };
}

export function cloneState(state) {
  return JSON.parse(JSON.stringify(state));
}

function mergeState(target, patch = {}) {
  for (const [key, value] of Object.entries(patch || {})) {
    if (
      value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      target[key] &&
      typeof target[key] === "object" &&
      !Array.isArray(target[key])
    ) {
      target[key] = { ...target[key] };
      mergeState(target[key], value);
    } else {
      target[key] = value;
    }
  }
}

function normalizeUsers(users) {
  return (users || []).map((user) => {
    if (typeof user === "string") {
      return { username: user, privilege: 1, password: "" };
    }
    return { username: user.username, privilege: user.privilege || 1, password: user.password || "" };
  });
}

function applyTopology(state, topology = {}) {
  for (const [id, vlan] of Object.entries(topology.vlans || {})) {
    state.vlans[String(id)] = {
      ...(state.vlans[String(id)] || {}),
      ...cloneState(vlan),
    };
  }
  for (const [rawName, iface] of Object.entries(topology.interfaces || {})) {
    const name = normalizeIfName(rawName);
    const current = state.interfaces[name] || { mode: iface.mode || "access", accessVlan: 1 };
    state.interfaces[name] = {
      ...current,
      ...iface,
      shutdown: iface.shutdown ?? (iface.status ? iface.status === "down" : current.shutdown),
    };
    if (state.interfaces[name].accessVlan) applyAccessVlan(state, name, state.interfaces[name].accessVlan);
  }
  state.pcDevices = (topology.devices || [])
    .filter((device) => device.type === "pc" && device.ip && device.connectedTo)
    .map((device) => ({
      ...device,
      connectedTo: normalizeIfName(device.connectedTo),
      vlan: Number(device.vlan || state.interfaces[normalizeIfName(device.connectedTo)]?.accessVlan || 1),
      mac: device.mac || fakePcMac(device.id),
    }));
  for (const pc of state.pcDevices) {
    if (!state.interfaces[pc.connectedTo]) state.interfaces[pc.connectedTo] = { mode: "access", accessVlan: pc.vlan, shutdown: false };
    applyAccessVlan(state, pc.connectedTo, pc.vlan);
    if (!state.interfaces[pc.connectedTo].label) state.interfaces[pc.connectedTo].label = pc.label || pc.id;
  }
}

export function initialState(lesson = {}) {
  const state = baseState();
  applyTopology(state, lesson.topology || lesson.sharedTopology);
  if (lesson.startState) {
    mergeState(state, cloneState(lesson.startState));
  }
  state.users = normalizeUsers(state.users);
  if (lesson.startMode) {
    state.mode = lesson.startMode;
    state.visitedModes = Array.from(new Set([...(state.visitedModes || []), lesson.startMode]));
  }
  return state;
}

function setMode(state, mode) {
  state.mode = mode;
  if (!state.visitedModes.includes(mode)) {
    state.visitedModes.push(mode);
  }
}

function makeEvent(id, arg, meta = {}) {
  return { id, arg, ...meta };
}

function normalizeResult(result, extraEvents = []) {
  const events = [...extraEvents];
  if (result?.event) {
    if (typeof result.event === "string") {
      events.push(makeEvent(result.event, result.eventArg, result.eventMeta || {}));
    } else {
      events.push(result.event);
    }
  }
  return {
    output: result?.output || [],
    events,
    event: events[0]?.id,
    needsAuth: result?.needsAuth,
  };
}

function incompleteWithoutCommandLog() {
  return { output: ["% Incomplete command."], suppressCommandLog: true };
}

const registry = [
  {
    canonical: "enable",
    validModes: ["user"],
    handler: (state) => {
      if (state.enableSecret || state.enablePassword) {
        state.pendingAuth = "enable";
        return { output: [], needsAuth: "enable" };
      }
      setMode(state, "privileged");
      return { output: [], event: "mode.privileged.enter" };
    },
  },
  {
    canonical: "disable",
    validModes: ["privileged"],
    handler: (state) => {
      setMode(state, "user");
      return { output: [], event: "mode.user.enter" };
    },
  },
  {
    canonical: "configure terminal",
    aliasPrefixes: ["config", "conf t", "config t", "configure t"],
    validModes: ["privileged"],
    handler: (state) => {
      setMode(state, "config");
      return { output: [], event: "mode.config.enter" };
    },
  },
  {
    canonical: "exit",
    validModes: ["privileged", "config", "interface", "interface-range", "vlan", "line"],
    handler: (state) => {
      if (["interface", "interface-range", "vlan", "line"].includes(state.mode)) {
        setMode(state, "config");
        state.activeInterface = null;
        state.activeInterfaceRange = null;
        state.activeInterfaceRangeLabel = null;
        state.activeVlan = null;
        state.activeLine = null;
        return { output: [], event: "mode.config.enter" };
      }
      if (state.mode === "config") {
        setMode(state, "privileged");
        return { output: [], event: "mode.privileged.enter" };
      }
      if (state.mode === "privileged") {
        setMode(state, "user");
        return { output: state.bannerSet ? [state.bannerText] : [], event: "mode.user.enter" };
      }
      return { output: [] };
    },
  },
  {
    canonical: "end",
    validModes: ["config", "interface", "interface-range", "vlan", "line"],
    handler: (state) => {
      setMode(state, "privileged");
      state.activeInterface = null;
      state.activeInterfaceRange = null;
      state.activeInterfaceRangeLabel = null;
      state.activeVlan = null;
      state.activeLine = null;
      return { output: [], event: "mode.privileged.enter" };
    },
  },
  {
    canonical: "hostname",
    validModes: ["config", "interface", "interface-range"],
    takesArg: true,
    handler: (state, args) => {
      if (!args[0]) return { output: ["% Incomplete command."] };
      state.hostname = args[0];
      state.saved = false;
      return { output: [], event: "config.hostname.set", eventArg: args[0] };
    },
  },
  {
    canonical: "interface range",
    aliasPrefixes: ["int range"],
    validModes: ["config", "interface", "interface-range"],
    takesRawArg: true,
    handler: (state, _args, raw) => {
      const range = parseInterfaceRange(raw);
      if (!range) return { output: ["% Invalid input detected at '^' marker."] };
      for (const name of range.names) ensureInterface(state, name);
      setMode(state, "interface-range");
      state.activeInterface = null;
      state.activeInterfaceRange = range.names;
      state.activeInterfaceRangeLabel = range.label;
      return { output: [], event: "mode.interface-range.enter", eventArg: range.label };
    },
  },
  {
    canonical: "interface",
    aliasPrefixes: ["int"],
    validModes: ["config", "interface", "interface-range"],
    takesArg: true,
    handler: (state, args) => {
      if (!args[0]) return { output: ["% Incomplete command."] };
      const name = normalizeIfName(args[0]);
      ensureInterface(state, name);
      setMode(state, "interface");
      state.activeInterface = name;
      state.activeInterfaceRange = null;
      state.activeInterfaceRangeLabel = null;
      return { output: [], event: "mode.interface.enter", eventArg: name };
    },
  },
  {
    canonical: "vlan",
    validModes: ["config", "vlan"],
    takesArg: true,
    handler: (state, args) => {
      const id = args[0];
      if (!id) return { output: ["% Incomplete command."] };
      const created = !state.vlans[id];
      if (created) {
        state.vlans[id] = { name: `VLAN${id}`, ports: [] };
        state.saved = false;
      }
      setMode(state, "vlan");
      state.activeVlan = id;
      return {
        output: [],
        event: created ? "vlan.create" : "mode.vlan.enter",
        eventArg: id,
      };
    },
  },
  {
    canonical: "name",
    validModes: ["vlan"],
    takesRawArg: true,
    handler: (state, _args, raw) => {
      if (!raw) return { output: ["% Incomplete command."] };
      state.vlans[state.activeVlan].name = raw;
      state.saved = false;
      return { output: [], event: "config.vlan-name.set", eventArg: raw };
    },
  },
  {
    canonical: "no vlan",
    validModes: ["config"],
    takesArg: true,
    handler: (state, args) => {
      if (!args[0]) return { output: ["% Incomplete command."] };
      delete state.vlans[args[0]];
      state.saved = false;
      return { output: [], event: "vlan.delete", eventArg: args[0] };
    },
  },
  {
    canonical: "shutdown",
    validModes: ["interface", "interface-range"],
    handler: (state) => {
      for (const name of activeInterfaceNames(state)) {
        state.interfaces[name].shutdown = true;
        state.interfaces[name].errDisabled = false;
      }
      state.saved = false;
      return { output: [], event: "interface.shutdown", eventArg: state.activeInterfaceRangeLabel || state.activeInterface };
    },
  },
  {
    canonical: "no shutdown",
    validModes: ["interface", "interface-range"],
    handler: (state) => {
      for (const name of activeInterfaceNames(state)) {
        state.interfaces[name].shutdown = false;
        state.interfaces[name].errDisabled = false;
      }
      state.saved = false;
      return { output: [], event: "interface.no-shutdown", eventArg: state.activeInterfaceRangeLabel || state.activeInterface };
    },
  },
  ...ETHERCHANNEL_COMMANDS(activeInterfaceNames),
  ...STP_COMMANDS(activeInterfaceNames),
  {
    canonical: "description",
    validModes: ["interface", "interface-range"],
    takesRawArg: true,
    handler: (state, _args, raw) => {
      if (!raw) return { output: ["% Incomplete command."] };
      for (const name of activeInterfaceNames(state)) state.interfaces[name].description = raw;
      state.saved = false;
      return { output: [], event: "config.description.set", eventArg: raw };
    },
  },
  {
    canonical: "switchport mode access",
    validModes: ["interface", "interface-range"],
    handler: (state) => {
      for (const name of activeInterfaceNames(state)) state.interfaces[name].mode = "access";
      state.saved = false;
      return { output: [], event: "config.switchport-mode.set", eventArg: "access" };
    },
  },
  {
    canonical: "switchport mode trunk",
    validModes: ["interface", "interface-range"],
    handler: (state) => {
      for (const name of activeInterfaceNames(state)) state.interfaces[name].mode = "trunk";
      state.saved = false;
      return { output: [], event: "config.switchport-mode.set", eventArg: "trunk" };
    },
  },
  {
    canonical: "switchport mode dynamic desirable",
    validModes: ["interface", "interface-range"],
    handler: (state) => {
      for (const name of activeInterfaceNames(state)) state.interfaces[name].mode = "dynamic desirable";
      state.saved = false;
      return { output: [], event: "config.switchport-mode.set", eventArg: "dynamic desirable" };
    },
  },
  {
    canonical: "switchport mode dynamic auto",
    validModes: ["interface", "interface-range"],
    handler: (state) => {
      for (const name of activeInterfaceNames(state)) state.interfaces[name].mode = "dynamic auto";
      state.saved = false;
      return { output: [], event: "config.switchport-mode.set", eventArg: "dynamic auto" };
    },
  },
  {
    canonical: "switchport nonegotiate",
    validModes: ["interface", "interface-range"],
    handler: (state) => {
      const activeNames = activeInterfaceNames(state);
      if (activeNames.some((name) => ["dynamic auto", "dynamic desirable"].includes(state.interfaces[name].mode))) {
        return { output: ["Command rejected: Conflict between 'nonegotiate' and 'dynamic' status."] };
      }
      for (const name of activeNames) state.interfaces[name].nonegotiate = true;
      state.saved = false;
      return { output: [], event: "config.nonegotiate.set" };
    },
  },
  {
    canonical: "switchport trunk encapsulation dot1q",
    validModes: ["interface", "interface-range"],
    handler: (state) => {
      for (const name of activeInterfaceNames(state)) state.interfaces[name].trunkEncapsulation = "dot1q";
      state.saved = false;
      return { output: [], event: "config.trunk-encapsulation.set", eventArg: "dot1q" };
    },
  },
  {
    canonical: "switchport trunk allowed vlan add",
    validModes: ["interface", "interface-range"],
    takesArg: true,
    handler: (state, _args, raw) => {
      if (!raw) return { output: ["% Incomplete command."] };
      if (raw.trim().toLowerCase() === "all" || !isValidAllowedVlanList(raw)) return { output: ["% Invalid input detected at '^' marker."] };
      const addList = normalizeAllowedVlans(raw);
      for (const name of activeInterfaceNames(state)) {
        const current = normalizeAllowedVlans(state.interfaces[name].allowedVlans);
        state.interfaces[name].allowedVlans = current === "all" ? addList : normalizeAllowedVlans([...current, ...addList]);
      }
      state.saved = false;
      return { output: [], event: "config.trunk-allowed.add", eventArg: raw };
    },
  },
  {
    canonical: "switchport trunk allowed vlan",
    validModes: ["interface", "interface-range"],
    takesArg: true,
    handler: (state, _args, raw) => {
      if (!raw) return { output: ["% Incomplete command."] };
      if (!isValidAllowedVlanList(raw)) return { output: ["% Invalid input detected at '^' marker."] };
      const value = raw.toLowerCase() === "all" ? "all" : normalizeAllowedVlans(raw);
      for (const name of activeInterfaceNames(state)) state.interfaces[name].allowedVlans = value;
      state.saved = false;
      return { output: [], event: "config.trunk-allowed.set", eventArg: raw };
    },
  },
  {
    canonical: "switchport trunk native vlan",
    validModes: ["interface", "interface-range"],
    takesArg: true,
    handler: (state, args) => {
      if (!args[0]) return { output: ["% Incomplete command."] };
      if (!/^\d+$/.test(args[0])) return { output: ["% Invalid input detected at '^' marker."] };
      const nativeVlan = Number(args[0]);
      if (nativeVlan < 1 || nativeVlan > 4094) return { output: ["% Invalid input detected at '^' marker."] };
      for (const name of activeInterfaceNames(state)) state.interfaces[name].nativeVlan = nativeVlan;
      state.saved = false;
      return { output: [], event: "config.trunk-native.set", eventArg: args[0] };
    },
  },
  {
    canonical: "switchport access vlan",
    validModes: ["interface", "interface-range"],
    takesArg: true,
    handler: (state, args) => {
      const id = args[0];
      if (!id || !/^\d+$/.test(id)) return { output: ["% Incomplete command."] };
      const created = ensureVlan(state, id);
      for (const name of activeInterfaceNames(state)) applyAccessVlan(state, name, id);
      state.saved = false;
      return {
        output: created ? [`% Access VLAN does not exist. Creating vlan ${id}`] : [],
        event: "config.access-vlan.set",
        eventArg: id,
      };
    },
  },
  {
    canonical: "speed",
    validModes: ["interface", "interface-range"],
    takesArg: true,
    handler: (state, args) => {
      if (!["10", "100", "1000", "auto"].includes(args[0])) return { output: ["% Invalid input detected at '^' marker."] };
      for (const name of activeInterfaceNames(state)) state.interfaces[name].speed = args[0];
      state.saved = false;
      return { output: [], event: "config.speed.set", eventArg: args[0] };
    },
  },
  {
    canonical: "duplex",
    validModes: ["interface", "interface-range"],
    takesArg: true,
    handler: (state, args) => {
      if (!["half", "full", "auto"].includes(args[0])) return { output: ["% Invalid input detected at '^' marker."] };
      for (const name of activeInterfaceNames(state)) state.interfaces[name].duplex = args[0];
      state.saved = false;
      return { output: [], event: "config.duplex.set", eventArg: args[0] };
    },
  },
  {
    canonical: "show running-config interface",
    aliasPrefixes: ["show run interface", "sh run interface", "sh running-config interface"],
    validModes: ["privileged"],
    takesArg: true,
    handler: (state, args) => {
      if (!args[0]) return { output: ["% Incomplete command."] };
      return { output: renderRunningConfigInterface(state, args[0]), event: "cmd.show.running-config-interface" };
    },
  },
  {
    canonical: "show running-config",
    aliasPrefixes: ["show run", "sh run", "sh running-config"],
    validModes: ["privileged"],
    handler: (state) => ({ output: renderRunningConfig(state), event: "cmd.show.running-config" }),
  },
  {
    canonical: "show startup-config",
    aliasPrefixes: ["show start", "sh start"],
    validModes: ["privileged"],
    handler: (state) => ({
      output: state.saved ? renderRunningConfig(state) : ["startup-config does not match running-config"],
      event: "cmd.show.startup-config",
    }),
  },
  {
    canonical: "show version",
    aliasPrefixes: ["sh version", "show ver", "sh ver"],
    validModes: ["privileged"],
    handler: (state) => ({ output: renderShowVersion(state), event: "cmd.show.version" }),
  },
  {
    canonical: "show vlan brief",
    aliasPrefixes: ["show vlan", "sh vlan"],
    validModes: ["privileged"],
    handler: (state) => ({ output: renderVlanBrief(state), event: "cmd.show.vlan-brief" }),
  },
  {
    canonical: "show interfaces status",
    aliasPrefixes: ["show int status", "sh int status"],
    validModes: ["privileged"],
    handler: (state, _args, _raw, context) => ({ output: renderInterfaceStatus(state, context), event: "cmd.show.interfaces-status" }),
  },
  {
    canonical: "show interfaces trunk",
    aliasPrefixes: ["show int trunk", "sh interfaces trunk", "sh int trunk"],
    validModes: ["privileged"],
    handler: (state, _args, _raw, context) => ({ output: renderInterfacesTrunk(state, context), event: "cmd.show.interfaces-trunk" }),
  },
  {
    canonical: "show interfaces",
    aliasPrefixes: ["show int", "sh interfaces", "sh int"],
    validModes: ["privileged"],
    takesRawArg: true,
    handler: (state, _args, raw, context) =>
      /\bswitchport\s*$/i.test(raw)
        ? { output: renderInterfacesSwitchport(state, raw, context), event: "cmd.show.interfaces-switchport" }
        : { output: renderInterfaces(state, raw), event: "cmd.show.interfaces" },
  },
  {
    canonical: "show cdp neighbors",
    aliasPrefixes: ["sh cdp neighbors", "show cdp neigh", "sh cdp neigh"],
    validModes: ["privileged"],
    handler: (_state, _args, _raw, context) => ({ output: renderNeighborTable(context), event: "cmd.show.cdp-neighbors" }),
  },
  {
    canonical: "show lldp neighbors",
    aliasPrefixes: ["sh lldp neighbors", "show lldp neigh", "sh lldp neigh"],
    validModes: ["privileged"],
    handler: (_state, _args, _raw, context) => ({ output: renderNeighborTable(context), event: "cmd.show.lldp-neighbors" }),
  },
  {
    canonical: "show ip interface brief",
    aliasPrefixes: ["show ip int brief", "sh ip int brief"],
    validModes: ["privileged"],
    handler: (state, _args, _raw, context) => ({ output: renderInterfaceStatus(state, context), event: "cmd.show.ip-interface-brief" }),
  },
  {
    canonical: "show mac address-table dynamic",
    aliasPrefixes: ["show mac dynamic", "sh mac dynamic", "show mac-address-table dynamic", "sh mac address-table dynamic"],
    validModes: ["privileged"],
    handler: (state) => ({ output: renderMacAddressTable(state, { type: "DYNAMIC" }), event: "cmd.show.mac-address-table-dynamic" }),
  },
  {
    canonical: "show mac address-table vlan",
    aliasPrefixes: ["show mac vlan", "sh mac vlan", "show mac-address-table vlan", "sh mac address-table vlan"],
    validModes: ["privileged"],
    takesArg: true,
    handler: (state, args) => {
      if (!args[0]) return incompleteWithoutCommandLog();
      return { output: renderMacAddressTable(state, { vlan: args[0] }), event: "cmd.show.mac-address-table-vlan", eventArg: args[0] };
    },
  },
  {
    canonical: "show mac address-table interface",
    aliasPrefixes: ["show mac interface", "sh mac interface", "show mac-address-table interface", "sh mac address-table interface"],
    validModes: ["privileged"],
    takesArg: true,
    handler: (state, args) => {
      if (!args[0]) return incompleteWithoutCommandLog();
      return {
        output: renderMacAddressTable(state, { port: normalizeIfName(args[0]) }),
        event: "cmd.show.mac-address-table-interface",
        eventArg: normalizeIfName(args[0]),
      };
    },
  },
  {
    canonical: "show mac address-table",
    aliasPrefixes: ["show mac", "sh mac", "show mac-address-table", "sh mac address-table"],
    validModes: ["privileged"],
    handler: (state) => ({ output: renderMacAddressTable(state), event: "cmd.show.mac-address-table" }),
  },
  {
    canonical: "write memory",
    aliasPrefixes: ["wr", "wr mem", "copy running-config startup-config"],
    validModes: ["privileged"],
    handler: (state) => {
      state.saved = true;
      return { output: ["Building configuration...", "[OK]"], event: "cmd.write.memory" };
    },
  },
  {
    canonical: "banner motd",
    validModes: ["config"],
    takesRawArg: true,
    handler: (state, _args, raw) => {
      state.bannerSet = true;
      state.bannerText = raw;
      state.saved = false;
      return { output: [], event: "config.banner.set", eventArg: raw };
    },
  },
  {
    canonical: "enable password",
    validModes: ["config"],
    takesArg: true,
    handler: (state, args) => {
      if (!args[0]) return { output: ["% Incomplete command."] };
      state.enablePassword = args[0];
      state.saved = false;
      return { output: [], event: "config.enable-password.set", eventArg: args[0] };
    },
  },
  {
    canonical: "enable secret",
    validModes: ["config"],
    takesArg: true,
    handler: (state, args) => {
      if (!args[0]) return { output: ["% Incomplete command."] };
      state.enableSecret = args[0];
      state.saved = false;
      return { output: [], event: "config.enable-secret.set", eventArg: args[0] };
    },
  },
  {
    canonical: "line console 0",
    validModes: ["config"],
    handler: (state) => {
      setMode(state, "line");
      state.activeLine = "console";
      return { output: [], event: "mode.line.enter", eventArg: "console" };
    },
  },
  {
    canonical: "line vty",
    validModes: ["config"],
    takesArg: true,
    handler: (state, args) => {
      if (args.length < 2) return { output: ["% Incomplete command."] };
      setMode(state, "line");
      state.activeLine = "vty";
      return { output: [], event: "mode.line.enter", eventArg: "vty" };
    },
  },
  {
    canonical: "password",
    validModes: ["line"],
    takesArg: true,
    handler: (state, args) => {
      if (!args[0]) return { output: ["% Incomplete command."] };
      if (state.activeLine === "console") {
        state.consolePassword = args[0];
        state.saved = false;
        return { output: [], event: "line.console.password", eventArg: args[0] };
      }
      state.vtyPassword = args[0];
      state.saved = false;
      return { output: [], event: "line.password.set", eventArg: args[0] };
    },
  },
  {
    canonical: "login",
    validModes: ["line"],
    handler: (state) => {
      if (state.activeLine === "console") state.consoleLogin = true;
      else state.vtyLogin = true;
      state.saved = false;
      return { output: [], event: "line.login.set", eventArg: state.activeLine };
    },
  },
  {
    canonical: "login local",
    validModes: ["line"],
    handler: (state) => {
      if (state.activeLine === "vty") {
        state.vtyLoginLocal = true;
        state.saved = false;
      }
      return { output: [], event: "line.login-local.set", eventArg: state.activeLine };
    },
  },
  {
    canonical: "transport input ssh",
    validModes: ["line"],
    handler: (state) => {
      if (state.activeLine !== "vty") return { output: ["% Invalid input detected at '^' marker."] };
      state.vtyTransportInput = "ssh";
      state.saved = false;
      return { output: [], event: "line.transport-input.set", eventArg: "ssh" };
    },
  },
  {
    canonical: "username",
    validModes: ["config"],
    takesRawArg: true,
    handler: (state, _args, raw) => {
      const match = raw.match(/^(\S+)(?:\s+privilege\s+(\d+))?\s+password\s+(\S+)$/i);
      if (!match) return { output: ["% Incomplete command."] };
      const user = { username: match[1], privilege: match[2] ? Number(match[2]) : 1, password: match[3] };
      const existing = state.users.find((row) => row.username.toLowerCase() === user.username.toLowerCase());
      if (existing) Object.assign(existing, user);
      else state.users.push(user);
      state.saved = false;
      return { output: [], event: "config.username.set", eventArg: user.username };
    },
  },
  {
    canonical: "ip domain-name",
    validModes: ["config"],
    takesArg: true,
    handler: (state, args) => {
      if (!args[0]) return { output: ["% Incomplete command."] };
      state.domainName = args[0];
      state.saved = false;
      return { output: [], event: "config.domain-name.set", eventArg: args[0] };
    },
  },
  {
    canonical: "mac address-table static",
    validModes: ["config"],
    takesRawArg: true,
    handler: (state, _args, raw) => setStaticMac(state, raw, normalizeIfName),
  },
  {
    canonical: "no mac address-table static",
    validModes: ["config"],
    takesRawArg: true,
    handler: (state, _args, raw) => removeStaticMac(state, raw, normalizeIfName),
  },
  {
    canonical: "crypto key generate rsa",
    validModes: ["config"],
    takesRawArg: true,
    handler: (state, _args, raw) => {
      if (!state.hostname || state.hostname === "Switch" || !state.domainName) {
        return { output: ["% Please configure a hostname and domain name first."] };
      }
      const modulus = raw.match(/modulus\s+(\d+)/i)?.[1] || "2048";
      state.rsaGenerated = true;
      state.rsaModulus = Number(modulus);
      state.saved = false;
      return {
        output: [`The name for the keys will be: ${state.hostname}.${state.domainName}`, `% Generating ${modulus} bit RSA keys...`],
        event: "config.crypto-key.generate",
        eventArg: modulus,
      };
    },
  },
  {
    canonical: "ip address",
    validModes: ["interface"],
    takesArg: true,
    handler: (state, args) => {
      if (args.length < 2) return { output: ["% Incomplete command."] };
      state.interfaces[state.activeInterface].ip = args[0];
      state.interfaces[state.activeInterface].mask = args[1];
      state.saved = false;
      if (state.activeInterface === "Vlan1") state.vlan1Ip = args[0];
      return { output: [], event: "interface.ip-address.set", eventArg: args[0] };
    },
  },
];

function wordPrefixMatch(headWords, formWords) {
  if (headWords.length !== formWords.length) return false;
  return headWords.every((word, index) => formWords[index].toLowerCase().startsWith(word.toLowerCase()));
}

function commandForms(entry) {
  return [entry.canonical, ...(entry.aliasPrefixes || [])];
}

function findCandidateMatches(words, mode) {
  const results = [];
  for (const entry of registry) {
    if (!entry.validModes.includes(mode)) continue;
    for (const form of commandForms(entry)) {
      const formWords = form.split(/\s+/);
      const consumed = formWords.length;
      if (words.length < consumed) continue;
      if (wordPrefixMatch(words.slice(0, consumed), formWords)) {
        results.push({ entry, consumed });
      }
    }
  }
  return results;
}

function commandExistsInAnyMode(words) {
  return registry.some((entry) =>
    commandForms(entry).some((form) => {
      const formWords = form.split(/\s+/);
      if (words.length < formWords.length) return false;
      return wordPrefixMatch(words.slice(0, formWords.length), formWords);
    })
  );
}

function logCommand(state, cmd, canonical = null) {
  state.commandLog.push({ cmd, canonical, ts: Date.now() });
}

function handlePendingAuth(state, trimmed) {
  const expected = state.enableSecret || state.enablePassword;
  logCommand(state, "[enable password]", "enable password");
  state.pendingAuth = null;
  if (trimmed === expected) {
    setMode(state, "privileged");
    return normalizeResult({ output: [], event: "mode.privileged.enter" });
  }
  return normalizeResult({ output: ["% Access denied"], event: "error.auth.failed" });
}

export function runCommand(state, rawInput, context = {}) {
  const trimmed = rawInput.trim();
  if (trimmed === "") return normalizeResult({ output: [] });

  if (state.pendingAuth) {
    return handlePendingAuth(state, trimmed);
  }

  logCommand(state, trimmed);

  if (trimmed === "?" || trimmed.toLowerCase() === "help") {
    const available = registry.filter((entry) => entry.validModes.includes(state.mode)).map((entry) => entry.canonical);
    return normalizeResult({ output: available, event: "cmd.help" });
  }

  let working = trimmed;
  const extraEvents = [];
  if (/^do\s+/i.test(working)) {
    working = working.replace(/^do\s+/i, "");
    extraEvents.push(makeEvent("cmd.do", working));
  }
  const effectiveMode = extraEvents.length ? "privileged" : state.mode;
  const lowerWorking = working.toLowerCase();

  if (KNOWN_AMBIGUOUS.includes(lowerWorking)) {
    return normalizeResult({ output: [`% Ambiguous command:  "${trimmed}"`], event: "error.ambiguous" }, extraEvents);
  }

  const words = working.split(/\s+/);
  const candidates = findCandidateMatches(words, effectiveMode);

  if (candidates.length === 0) {
    const event = commandExistsInAnyMode(words) ? "error.invalid-in-mode" : "error.unknown-command";
    return normalizeResult({ output: ["% Invalid input detected at '^' marker."], event }, extraEvents);
  }

  const maxConsumed = Math.max(...candidates.map((candidate) => candidate.consumed));
  const longestCandidates = candidates.filter((candidate) => candidate.consumed === maxConsumed);
  const uniqueEntries = [...new Set(longestCandidates.map((candidate) => candidate.entry))];

  if (uniqueEntries.length > 1) {
    return normalizeResult({ output: [`% Ambiguous command:  "${trimmed}"`], event: "error.ambiguous" }, extraEvents);
  }

  const entry = uniqueEntries[0];
  state.commandLog[state.commandLog.length - 1].canonical = entry.canonical;
  const args = words.slice(maxConsumed);
  const raw = args.join(" ");
  const result = entry.handler(state, args, raw, context);
  if (result?.suppressCommandLog) state.commandLog.pop();
  return normalizeResult(result, extraEvents);
}

export function getPrompt(state) {
  if (state.pendingAuth) return "Password: ";
  return PROMPTS[state.mode](state.hostname, state);
}

export function completeCommand(state, rawInput) {
  const words = rawInput.trim().split(/\s+/).filter(Boolean);
  if (!words.length) return { value: rawInput, event: null };
  const candidates = findCandidateMatches(words, state.mode);
  if (!candidates.length) return { value: rawInput, event: null };
  const maxConsumed = Math.max(...candidates.map((candidate) => candidate.consumed));
  const entries = [...new Set(candidates.filter((candidate) => candidate.consumed === maxConsumed).map((candidate) => candidate.entry))];
  if (entries.length !== 1) return { value: rawInput, event: makeEvent("error.ambiguous", rawInput) };
  return { value: entries[0].canonical, event: makeEvent("cmd.tab-complete", entries[0].canonical) };
}

export { registry };
