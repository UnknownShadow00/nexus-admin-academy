const MAX_PORT = 48;

export function normalizeIfName(raw = "") {
  const compact = raw.replace(/\s+/g, "");
  return compact.replace(/^gigabitethernet/i, "g").replace(/^vlan/i, "Vlan").replace(/^g/i, "g");
}

export function ensureInterface(state, name) {
  if (!state.interfaces[name]) state.interfaces[name] = { mode: "access", accessVlan: 1, shutdown: true };
  return state.interfaces[name];
}

export function ensureVlan(state, id) {
  const key = String(id);
  if (!state.vlans[key]) {
    state.vlans[key] = { name: `VLAN${key}`, ports: [] };
    return true;
  }
  if (!state.vlans[key].ports) state.vlans[key].ports = [];
  return false;
}

export function applyAccessVlan(state, name, vlanId) {
  const iface = ensureInterface(state, name);
  const id = String(vlanId);
  ensureVlan(state, id);
  for (const vlan of Object.values(state.vlans)) {
    vlan.ports = (vlan.ports || []).filter((port) => port !== name);
  }
  iface.accessVlan = Number(id);
  if (!state.vlans[id].ports.includes(name)) state.vlans[id].ports.push(name);
}

export function parseInterfaceRange(raw = "") {
  const match = raw.match(/^(gigabitethernet0\/|g0\/)(\d+)\s*-\s*(?:(?:gigabitethernet0\/|g0\/)?(\d+))$/i);
  if (!match) return null;
  const prefix = normalizeIfName(match[1]).replace(/\d+$/, "");
  const start = Number(match[2]);
  const end = Number(match[3]);
  if (!Number.isInteger(start) || !Number.isInteger(end) || end < start || end > MAX_PORT) return null;
  const names = [];
  for (let port = start; port <= end; port += 1) names.push(`${prefix}${port}`);
  return { names, label: `${prefix}${start} - ${end}` };
}

export function activeInterfaceNames(state) {
  if (state.mode === "interface-range") return state.activeInterfaceRange || [];
  return state.activeInterface ? [state.activeInterface] : [];
}

export function renderRunningConfig(state) {
  const lines = ["Building configuration...", "", `hostname ${state.hostname}`];
  if (state.domainName) lines.push(`ip domain-name ${state.domainName}`);
  if (state.bannerSet) lines.push(`banner motd ${state.bannerText}`);
  if (state.enableSecret) lines.push(`enable secret ${state.enableSecret}`);
  if (state.enablePassword) lines.push(`enable password ${state.enablePassword}`);
  for (const user of state.users) {
    lines.push(`username ${user.username} privilege ${user.privilege} password ${user.password}`);
  }
  for (const [id, vlan] of Object.entries(state.vlans)) {
    lines.push(`vlan ${id}  ! ${vlan.name}`);
  }
  for (const [name, iface] of Object.entries(state.interfaces)) {
    lines.push(...renderInterfaceConfig(name, iface));
  }
  lines.push("line console 0");
  if (state.consolePassword) lines.push(` password ${state.consolePassword}`);
  if (state.consoleLogin) lines.push(" login");
  lines.push("line vty 0 4");
  if (state.vtyLoginLocal) lines.push(" login local");
  else if (state.vtyLogin) lines.push(" login");
  if (state.vtyPassword) lines.push(` password ${state.vtyPassword}`);
  lines.push(` transport input ${state.vtyTransportInput}`);
  lines.push("end");
  return lines;
}

export function renderRunningConfigInterface(state, rawName) {
  const name = normalizeIfName(rawName);
  const iface = state.interfaces[name];
  if (!iface) return ["% Invalid input detected at '^' marker."];
  return ["Building configuration...", "", ...renderInterfaceConfig(name, iface), "end"];
}

function renderInterfaceConfig(name, iface) {
  const lines = [`interface ${name}`];
  if (iface.description) lines.push(` description ${iface.description}`);
  if (iface.mode === "access") lines.push(" switchport mode access");
  if (iface.accessVlan && Number(iface.accessVlan) !== 1) lines.push(` switchport access vlan ${iface.accessVlan}`);
  if (iface.speed) lines.push(` speed ${iface.speed}`);
  if (iface.duplex) lines.push(` duplex ${iface.duplex}`);
  if (iface.shutdown) lines.push(" shutdown");
  if (iface.ip) lines.push(` ip address ${iface.ip} ${iface.mask}`);
  return lines;
}

export function renderVlanBrief(state) {
  const lines = ["VLAN Name                             Status    Ports"];
  for (const [id, vlan] of Object.entries(state.vlans)) {
    lines.push(`${id.padEnd(5)}${vlan.name.padEnd(35)}active    ${(vlan.ports || []).join(", ")}`);
  }
  return lines;
}

export function renderInterfaceStatus(state) {
  const interfaces = Object.entries(state.interfaces);
  const showDescription = interfaces.some(([, iface]) => iface.description);
  const lines = [
    showDescription
      ? "Port      Name                 Status       Vlan       Duplex   Speed    Type"
      : "Port      Status       Vlan       Duplex   Speed    Type",
  ];
  for (const [name, iface] of interfaces) {
    const status = iface.shutdown ? "disabled" : pcOnPort(state, name) ? "connected" : "notconnect";
    const duplex = status === "connected" ? statusValue(iface.duplex, "a-full") : statusValue(iface.duplex, "auto");
    const speed = status === "connected" ? statusValue(iface.speed, "a-1000") : statusValue(iface.speed, "auto");
    const values = showDescription
      ? [name.padEnd(10), (iface.description || "").padEnd(21), status.padEnd(13), String(iface.accessVlan || "-").padEnd(11), duplex.padEnd(9), speed.padEnd(9), "10/100/1000BaseTX"]
      : [name.padEnd(10), status.padEnd(13), String(iface.accessVlan || "-").padEnd(11), duplex.padEnd(9), speed.padEnd(9), "10/100/1000BaseTX"];
    lines.push(values.join(""));
  }
  return lines;
}

export function renderInterfaces(state, rawName = "") {
  const names = rawName ? [normalizeIfName(rawName)] : Object.keys(state.interfaces);
  const lines = [];
  for (const name of names) {
    const iface = state.interfaces[name];
    if (!iface) return ["% Invalid input detected at '^' marker."];
    const up = !iface.shutdown && pcOnPort(state, name);
    const duplex = iface.duplex === "half" ? "Half-duplex" : iface.duplex === "full" ? "Full-duplex" : up ? "Full-duplex" : "Auto-duplex";
    const speed = iface.speed && iface.speed !== "auto" ? `${iface.speed}Mb/s` : up ? "1000Mb/s" : "Auto-speed";
    lines.push(
      `${name} is ${up ? "up" : "down"}, line protocol is ${up ? "up" : "down"}`,
      iface.description ? `  Description: ${iface.description}` : "  Description: not set",
      `  Hardware is Gigabit Ethernet, address is 001b.0c00.${name.replace(/\D/g, "").padStart(4, "0")}`,
      `  ${duplex}, ${speed}, media type is 10/100/1000BaseTX`
    );
    if (iface.duplex === "half" && up) lines.push("  5 input errors, 5 late collisions");
    if (names.length > 1) lines.push("");
  }
  return lines.at(-1) === "" ? lines.slice(0, -1) : lines;
}

export function renderInterfacesSwitchport(state, raw = "") {
  const cleaned = raw.replace(/\s*switchport\s*$/i, "").trim();
  const names = cleaned ? [normalizeIfName(cleaned)] : Object.keys(state.interfaces).filter((name) => !name.startsWith("Vlan"));
  const lines = [];
  for (const name of names) {
    const iface = state.interfaces[name];
    if (!iface) return ["% Invalid input detected at '^' marker."];
    const mode = iface.mode === "access" ? "static access" : iface.mode || "access";
    lines.push(
      `Name: ${name}`,
      `  Administrative Mode: ${mode}`,
      `  Operational Mode: ${mode}`,
      `  Access Mode VLAN: ${iface.accessVlan || 1}`,
      "  Trunking Native Mode VLAN: 1",
      ""
    );
  }
  return lines.at(-1) === "" ? lines.slice(0, -1) : lines;
}

export function renderShowVersion(state) {
  return [
    "Cisco IOS Software, C2960X Software (C2960X-UNIVERSALK9-M), Version 15.2(7)E",
    "Technical Support: http://www.cisco.com/techsupport",
    `System image file is \"flash:c2960x-universalk9-mz.152-7.E.bin\"`,
    `${state.hostname} uptime is 2 weeks, 3 days, 4 hours, 12 minutes`,
    "cisco WS-C2960X-24TS-L (APM86XXX) processor",
    "Base ethernet MAC Address       : 00:1B:0C:00:00:01",
  ];
}

function pcOnPort(state, name) {
  if (!(state.pcDevices || []).length) return !name.startsWith("Vlan");
  return (state.pcDevices || []).some((pc) => pc.connectedTo === name);
}

function statusValue(configured, autoValue) {
  if (!configured || configured === "auto") return autoValue;
  return configured;
}
