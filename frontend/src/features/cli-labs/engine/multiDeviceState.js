import { cloneState, initialState } from "./commandEngine.js";

function looksLikeInterfaceConfig(value = {}) {
  return ["mode", "status", "accessVlan", "shutdown", "nativeVlan", "allowedVlans", "trunkEncapsulation"].some((key) =>
    Object.prototype.hasOwnProperty.call(value, key)
  );
}

export function switchDevices(topology = {}) {
  return (topology.devices || []).filter((device) => device.type === "switch");
}

export function isMultiSwitchTopology(topology = {}) {
  return switchDevices(topology).length > 1;
}

function deviceInterfaces(topology = {}, deviceId) {
  const interfaces = topology.interfaces || {};
  if (interfaces[deviceId] && !looksLikeInterfaceConfig(interfaces[deviceId])) return interfaces[deviceId];
  return interfaces;
}

function deviceVlans(topology = {}, deviceId) {
  const vlans = topology.vlans || {};
  if (vlans[deviceId] && !vlans[deviceId].name && !vlans[deviceId].ports) return vlans[deviceId];
  return vlans;
}

function pcSwitchId(pc = {}, fallback = "main") {
  if (pc.switch) return pc.switch;
  const connected = String(pc.connectedTo || "");
  if (connected.includes(":")) return connected.split(":")[0];
  return fallback;
}

function normalizePcForDevice(pc, deviceId) {
  const connectedTo = String(pc.connectedTo || "");
  return {
    ...pc,
    switch: deviceId,
    connectedTo: connectedTo.includes(":") ? connectedTo.split(":")[1] : connectedTo,
  };
}

function deviceStartState(lesson = {}, device = {}) {
  const startState = lesson.startState || {};
  const nested = startState.devices?.[device.id] || startState.switches?.[device.id] || startState[device.id] || {};
  const shared = startState.devices || startState.switches || startState[device.id] ? {} : startState;
  return {
    ...shared,
    ...nested,
    hostname: nested.hostname || shared.hostname || device.hostname || device.label || device.id,
  };
}

export function lessonForDevice(lesson = {}, device = {}) {
  const topology = lesson.topology || lesson.sharedTopology || {};
  const devices = [
    { ...device, label: device.label || device.hostname || device.id },
    ...(topology.devices || [])
      .filter((item) => item.type === "pc" && pcSwitchId(item, device.id) === device.id)
      .map((pc) => normalizePcForDevice(pc, device.id)),
  ];
  return {
    ...lesson,
    topology: {
      ...topology,
      devices,
      interfaces: deviceInterfaces(topology, device.id),
      vlans: deviceVlans(topology, device.id),
    },
    startState: deviceStartState(lesson, device),
  };
}

export function initialDeviceStates(lesson = {}) {
  const topology = lesson.topology || lesson.sharedTopology || {};
  return Object.fromEntries(switchDevices(topology).map((device) => [device.id, initialState(lessonForDevice(lesson, device))]));
}

export function cloneDeviceStates(deviceStates = {}) {
  return Object.fromEntries(Object.entries(deviceStates).map(([deviceId, state]) => [deviceId, cloneState(state)]));
}

export function aggregateDeviceState(deviceStates = {}) {
  const states = Object.values(deviceStates);
  return {
    ...(states[0] || {}),
    commandLog: states.flatMap((state) => state.commandLog || []),
    pcActions: states.flatMap((state) => state.pcActions || []),
    devices: deviceStates,
  };
}
