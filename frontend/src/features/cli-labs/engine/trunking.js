function normalizeIfName(raw = "") {
  const compact = raw.replace(/\s+/g, "");
  return compact.replace(/^gigabitethernet/i, "g").replace(/^vlan/i, "Vlan").replace(/^g/i, "g");
}

const MIN_VLAN_ID = 1;
const MAX_VLAN_ID = 4094;

function vlanTokens(value) {
  const values = Array.isArray(value) ? value : String(value).split(",");
  return values.flatMap((item) => String(item).split(",")).map((item) => item.trim()).filter(Boolean);
}

function rawVlanTokens(value) {
  const values = Array.isArray(value) ? value : String(value).split(",");
  return values.flatMap((item) => String(item).split(",")).map((item) => item.trim());
}

function isValidVlanId(value) {
  const id = Number(value);
  return Number.isInteger(id) && id >= MIN_VLAN_ID && id <= MAX_VLAN_ID;
}

function expandVlanToken(token) {
  const range = token.match(/^(\d+)\s*-\s*(\d+)$/);
  if (range) {
    const start = Math.max(Number(range[1]), MIN_VLAN_ID);
    const end = Math.min(Number(range[2]), MAX_VLAN_ID);
    const vlans = [];
    for (let id = start; id <= end; id += 1) vlans.push(String(id));
    return vlans;
  }
  return /^\d+$/.test(token) && isValidVlanId(token) ? [String(Number(token))] : [];
}

export function isValidAllowedVlanList(value) {
  if (!value) return false;
  if (String(value).trim().toLowerCase() === "all") return true;
  const tokens = rawVlanTokens(value);
  if (!tokens.length) return false;
  return tokens.every((token) => {
    const range = token.match(/^(\d+)\s*-\s*(\d+)$/);
    if (range) {
      const start = Number(range[1]);
      const end = Number(range[2]);
      return isValidVlanId(start) && isValidVlanId(end) && start <= end;
    }
    return /^\d+$/.test(token) && isValidVlanId(token);
  });
}

export function parseLinkEndpoint(endpoint = "") {
  const [deviceId, iface] = String(endpoint).split(":");
  if (!deviceId || !iface) return null;
  return { deviceId, interface: normalizeIfName(iface) };
}

export function normalizeAllowedVlans(value) {
  if (!value || String(value).trim().toLowerCase() === "all") return "all";
  return [...new Set(vlanTokens(value).flatMap(expandVlanToken))].sort((a, b) => Number(a) - Number(b));
}

export function allowedVlansLabel(value) {
  const normalized = normalizeAllowedVlans(value);
  return normalized === "all" ? "all" : normalized.join(",");
}

export function vlanAllowed(iface, vlanId) {
  const allowed = normalizeAllowedVlans(iface?.allowedVlans);
  return allowed === "all" || allowed.includes(String(vlanId));
}

export function administrativeMode(iface = {}) {
  if (iface.mode === "trunk") return "trunk";
  if (iface.mode === "dynamic desirable") return "dynamic desirable";
  if (iface.mode === "dynamic auto") return "dynamic auto";
  return "static access";
}

export function trunkModeColumn(iface = {}) {
  if (iface.mode === "dynamic desirable") return "desirable";
  if (iface.mode === "dynamic auto") return "auto";
  return "on";
}

export function isOperationalTrunk(local = {}, remote = null) {
  const localMode = local.mode || "access";
  const remoteMode = remote?.mode || (localMode === "trunk" ? "trunk" : "access");
  if (local.shutdown || remote?.shutdown) return false;
  if (localMode === "access" || remoteMode === "access") return false;
  if (localMode === "trunk" && remoteMode === "trunk") return true;
  if (local.nonegotiate && localMode === "trunk" && ["dynamic desirable", "dynamic auto"].includes(remoteMode)) return false;
  if (remote?.nonegotiate && remoteMode === "trunk" && ["dynamic desirable", "dynamic auto"].includes(localMode)) return false;
  if ((local.nonegotiate && localMode.startsWith("dynamic")) || (remote?.nonegotiate && remoteMode.startsWith("dynamic"))) return false;
  if (localMode === "dynamic auto" && remoteMode === "dynamic auto") return false;
  return ["trunk", "dynamic desirable", "dynamic auto"].includes(localMode) && ["trunk", "dynamic desirable", "dynamic auto"].includes(remoteMode);
}

export function findPeerEndpoint(context = {}, localInterface) {
  const local = normalizeIfName(localInterface);
  for (const link of context.topology?.links || []) {
    const a = parseLinkEndpoint(link.a);
    const b = parseLinkEndpoint(link.b);
    if (!a || !b) continue;
    if (a.deviceId === context.deviceId && a.interface === local) return b;
    if (b.deviceId === context.deviceId && b.interface === local) return a;
  }
  return null;
}

export function peerInterfaceState(context = {}, localInterface) {
  const peer = findPeerEndpoint(context, localInterface);
  if (!peer) return null;
  return context.deviceStates?.[peer.deviceId]?.interfaces?.[peer.interface] || null;
}

export function operationalMode(iface = {}, context = {}, name = "") {
  return isOperationalTrunk(iface, peerInterfaceState(context, name)) ? "trunk" : "static access";
}

export function renderNeighborTable(context = {}) {
  const lines = ["Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID"];
  for (const link of context.topology?.links || []) {
    const a = parseLinkEndpoint(link.a);
    const b = parseLinkEndpoint(link.b);
    if (!a || !b) continue;
    const local = a.deviceId === context.deviceId ? a : b.deviceId === context.deviceId ? b : null;
    const remote = local === a ? b : local === b ? a : null;
    if (!local || !remote) continue;
    lines.push(`${remote.deviceId.padEnd(17)}${local.interface.padEnd(17)}153        S           C2960X    ${remote.interface}`);
  }
  return lines;
}
