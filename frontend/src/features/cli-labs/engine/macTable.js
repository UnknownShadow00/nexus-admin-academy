function invalidInput() {
  return { output: ["% Invalid input detected at '^' marker."] };
}

export function fakePcMac(id = "") {
  // Deterministic lab-only MAC: first alphanumeric id byte repeated, plus a two-digit id checksum.
  const compact = String(id).replace(/[^a-z0-9]/gi, "").toLowerCase();
  const seed = compact.charCodeAt(0) || 0xaa;
  const hex = seed.toString(16).padStart(2, "0").slice(-2);
  const suffix = [...compact].reduce((sum, char) => sum + char.charCodeAt(0), 0).toString(16).padStart(2, "0").slice(-2);
  return `${hex}${hex}.${hex}${hex}.${hex}${suffix}`;
}

export function renderMacAddressTable(state, filter = {}) {
  const lines = [
    "          Mac Address Table",
    "-------------------------------------------",
    "Vlan    Mac Address       Type        Ports",
    "----    -----------       --------    -----",
  ];
  const entries = [...(state.macTable || [])]
    .filter((entry) => {
      if (filter.type && entry.type !== filter.type) return false;
      if (filter.vlan && Number(entry.vlan) !== Number(filter.vlan)) return false;
      if (filter.port && entry.port !== filter.port) return false;
      return true;
    })
    .sort((a, b) => {
    if (a.type !== b.type) return a.type === "STATIC" ? -1 : 1;
    return Number(a.vlan) - Number(b.vlan) || a.mac.localeCompare(b.mac);
  });
  for (const entry of entries) {
    lines.push(`${String(entry.vlan).padEnd(8)}${entry.mac.padEnd(18)}${entry.type.padEnd(12)}${entry.port}`);
  }
  return lines;
}

export function learnDynamicMac(state, pc, vlan) {
  const exists = (state.macTable || []).some((entry) => entry.mac.toLowerCase() === pc.mac.toLowerCase());
  if (!exists) state.macTable.push({ mac: pc.mac, vlan, port: pc.connectedTo, type: "DYNAMIC" });
}

export function setStaticMac(state, raw, normalizeIfName) {
  const match = raw.match(/^([0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4})\s+vlan\s+(\d+)\s+interface\s+(\S+)$/i);
  if (!match) return invalidInput();
  const [, mac, vlan, rawPort] = match;
  const port = normalizeIfName(rawPort);
  if (!state.interfaces[port]) return invalidInput();
  state.macTable = (state.macTable || []).filter((entry) => !(entry.type === "STATIC" && entry.mac.toLowerCase() === mac.toLowerCase()));
  state.macTable.push({ mac: mac.toLowerCase(), vlan: Number(vlan), port, type: "STATIC" });
  state.saved = false;
  return { output: [], event: "config.mac-static.set", eventArg: mac.toLowerCase() };
}

export function removeStaticMac(state, raw, normalizeIfName) {
  const match = raw.match(/^([0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4})\s+vlan\s+(\d+)\s+interface\s+(\S+)$/i);
  if (!match) return invalidInput();
  const [, mac, vlan, rawPort] = match;
  const port = normalizeIfName(rawPort);
  if (!state.interfaces[port]) return invalidInput();
  state.macTable = (state.macTable || []).filter(
    (entry) => !(entry.type === "STATIC" && entry.mac.toLowerCase() === mac.toLowerCase() && Number(entry.vlan) === Number(vlan) && entry.port === port)
  );
  state.saved = false;
  return { output: [], event: "config.mac-static.removed", eventArg: mac.toLowerCase() };
}
