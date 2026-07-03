import { learnDynamicMac } from "./macTable.js";

function normalizeResult(result) {
  const events = [];
  if (result?.event) events.push({ id: result.event, arg: result.eventArg });
  return { output: result?.output || [], events, event: events[0]?.id, needsAuth: result?.needsAuth };
}

function pingFailure() {
  return {
    output: ["Request timed out.", "Request timed out.", "Request timed out.", "Request timed out.", "Ping statistics: 4 sent, 0 received, 4 lost"],
    event: "pc.ping.failed",
  };
}

function sourceDevice(state, sourceId = null) {
  const pcs = state.pcDevices || [];
  if (sourceId) return pcs.find((pc) => pc.id.toLowerCase() === sourceId.toLowerCase());
  return pcs[0];
}

function ensureArpCache(state, pc) {
  if (!state.arpCaches) state.arpCaches = {};
  if (!state.arpCaches[pc.id]) state.arpCaches[pc.id] = [];
  return state.arpCaches[pc.id];
}

function rememberArpPeer(state, owner, peer) {
  const cache = ensureArpCache(state, owner);
  const existing = cache.find((entry) => entry.ip === peer.ip);
  if (existing) {
    existing.mac = peer.mac;
    return;
  }
  cache.push({ ip: peer.ip, mac: peer.mac });
}

function handlePcPing(state, source, ip, rawCommand) {
  const pcs = state.pcDevices || [];
  const target = pcs.find((pc) => pc.ip === ip && pc.id !== source?.id);
  if (!source || !target) return pingFailure();
  const sourceIface = state.interfaces[source.connectedTo];
  const targetIface = state.interfaces[target.connectedTo];
  const sourceVlan = Number(sourceIface?.accessVlan || source.vlan);
  const targetVlan = Number(targetIface?.accessVlan || target.vlan);
  if (!sourceIface || !targetIface || sourceIface.shutdown || targetIface.shutdown || sourceVlan !== targetVlan) return pingFailure();

  learnDynamicMac(state, source, sourceVlan);
  learnDynamicMac(state, target, targetVlan);
  rememberArpPeer(state, source, target);
  rememberArpPeer(state, target, source);
  return {
    output: [
      `ARP request: who has ${ip}? tell ${source.ip} (broadcast ffff.ffff.ffff)`,
      `ARP reply: ${ip} is at ${target.mac}`,
      `Reply from ${ip}: bytes=32 time<1ms TTL=128`,
      `Reply from ${ip}: bytes=32 time<1ms TTL=128`,
      `Reply from ${ip}: bytes=32 time<1ms TTL=128`,
      `Reply from ${ip}: bytes=32 time<1ms TTL=128`,
      "Ping statistics: 4 sent, 4 received, 0 lost",
    ],
    event: "pc.ping.success",
    eventArg: `${source.id}: ${rawCommand}`,
  };
}

function handleArpCache(state, source) {
  if (!source) return { output: ["No ARP entries found."], event: "pc.arp.show" };
  const learned = (state.arpCaches?.[source.id] || []).map((entry) => `  ${entry.ip.padEnd(15)} ${entry.mac}`);
  return {
    output: ["Interface: Ethernet0", "  Internet Address  Physical Address", ...(learned.length ? learned : ["  No dynamic entries"])],
    event: "pc.arp.show",
    eventArg: source.id,
  };
}

function parsePcInput(rawInput) {
  const trimmed = rawInput.trim();
  const prefixed = trimmed.match(/^(pc-[a-z0-9]+)\s*[:>]\s*(.+)$/i) || trimmed.match(/^(pc-[a-z0-9]+)\s+(.+)$/i);
  if (!prefixed) return { sourceId: null, command: trimmed };
  return { sourceId: prefixed[1].toUpperCase(), command: prefixed[2].trim() };
}

export function runPcCommand(state, rawInput, explicitSourceId = null) {
  const { sourceId, command } = parsePcInput(rawInput);
  const source = sourceDevice(state, explicitSourceId || sourceId);
  const trimmed = command.trim();
  if (!trimmed) return normalizeResult({ output: [] });
  state.commandLog.push({ cmd: `${source?.id || "PC"}: ${trimmed}`, canonical: "pc", ts: Date.now() });
  state.pcActions.push(trimmed);

  const pingMatch = trimmed.match(/^ping\s+(\S+)$/i);
  if (pingMatch) return normalizeResult(handlePcPing(state, source, pingMatch[1], trimmed));

  if (/^arp\s+-a$/i.test(trimmed)) return normalizeResult(handleArpCache(state, source));

  const sshMatch = trimmed.match(/^ssh\s+([^@\s]+)@(\S+)$/i);
  if (!sshMatch) return normalizeResult({ output: ["Command not available in this PC terminal."], event: "error.unknown-command" });

  const [, username, ip] = sshMatch;
  const userExists = state.users.some((user) => user.username.toLowerCase() === username.toLowerCase());
  if (ip !== state.vlan1Ip || state.vtyTransportInput !== "ssh" || !state.vtyLoginLocal || !state.rsaGenerated || !userExists) {
    return normalizeResult({ output: [`ssh: connect to host ${ip} port 22: Connection refused`], event: "pc.ssh.failed" });
  }
  return normalizeResult({ output: [`Connected to ${state.hostname} (${ip}) as ${username}.`], event: "pc.ssh.connect", eventArg: trimmed });
}

function redactCommand(cmd = "") {
  const value = String(cmd);
  if (/^pc:\s+/i.test(value)) return value;
  if (/^\[enable password\]$/i.test(value)) return "[enable password]";
  if (/^enable\s+password\s+/i.test(value)) return "enable password [redacted]";
  if (/^enable\s+secret\s+/i.test(value)) return "enable secret [redacted]";
  if (/^password\s+/i.test(value)) return "password [redacted]";
  if (/^username\s+/i.test(value)) return value.replace(/(\s+password\s+)\S+/i, "$1[redacted]");
  return value;
}

export function redactCommandLog(commandLog = []) {
  return commandLog.map((entry) => ({ ...entry, cmd: redactCommand(entry?.cmd) }));
}
