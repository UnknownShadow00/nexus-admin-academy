import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { getPrompt, initialState, redactCommandLog, runCommand, runPcCommand } from "../src/features/cli-labs/engine/commandEngine.js";
import { initialDeviceStates } from "../src/features/cli-labs/engine/multiDeviceState.js";
import { runMultiPcCommand } from "../src/features/cli-labs/engine/networkSim.js";
import { applyCommandProgress, createProgress, isLabComplete } from "../src/features/cli-labs/engine/objectiveTracker.js";

const root = path.dirname(fileURLToPath(import.meta.url));
const lessonPath = path.resolve(root, "../src/features/cli-labs/data/lessons/meet-the-cli.json");
const lessonPack = JSON.parse(fs.readFileSync(lessonPath, "utf8"));
const networkFoundationsPath = path.resolve(root, "../src/features/cli-labs/data/lessons/network-foundations.json");
const networkFoundationsPack = JSON.parse(fs.readFileSync(networkFoundationsPath, "utf8"));
const learnSwitchingPath = path.resolve(root, "../src/features/cli-labs/data/lessons/learn-switching.json");
const learnSwitchingPack = JSON.parse(fs.readFileSync(learnSwitchingPath, "utf8"));

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function findLesson(id) {
  return lessonPack.lessons.find((lesson) => lesson.id === id);
}

function findNetworkFoundationsLesson(id) {
  const lesson = networkFoundationsPack.lessons.find((item) => item.id === id);
  return { ...lesson, topology: lesson.topology || networkFoundationsPack.sharedTopology };
}

function packLesson(pack, lesson) {
  return { ...lesson, topology: lesson.topology || pack.sharedTopology };
}

function commandOn(deviceStates, topology, deviceId, command) {
  return runCommand(deviceStates[deviceId], command, { topology, deviceId, deviceStates });
}

function configureTrunk(deviceStates, topology, deviceId) {
  ["enable", "configure terminal", "interface g0/24", "switchport trunk encapsulation dot1q", "switchport mode trunk", "end"].forEach((command) =>
    commandOn(deviceStates, topology, deviceId, command)
  );
}

function runOnTrunkInterface(deviceStates, topology, deviceId, command) {
  ["configure terminal", "interface g0/24", command, "end"].forEach((item) => commandOn(deviceStates, topology, deviceId, item));
}

function runOnTrunkInterfaceMany(deviceStates, topology, deviceId, commands) {
  ["configure terminal", "interface g0/24", ...commands, "end"].forEach((item) => commandOn(deviceStates, topology, deviceId, item));
}

function runOnTrunkInterfaceResult(deviceStates, topology, deviceId, command) {
  commandOn(deviceStates, topology, deviceId, "configure terminal");
  commandOn(deviceStates, topology, deviceId, "interface g0/24");
  const result = commandOn(deviceStates, topology, deviceId, command);
  commandOn(deviceStates, topology, deviceId, "end");
  return result;
}

function runLesson(id, commands) {
  const lesson = findLesson(id);
  const state = initialState(lesson);
  let progress = createProgress();
  for (const command of commands) {
    progress = applyCommandProgress(lesson, progress, runCommand(state, command), command);
  }
  assert(isLabComplete(lesson, progress, state), `${id} did not complete`);
}

function runLessonDrive(lesson, actions) {
  const state = initialState(lesson);
  let progress = createProgress();
  for (const action of actions) {
    const command = typeof action === "string" ? action : action.command;
    const result = typeof action === "string" ? runCommand(state, action) : runPcCommand(state, action.command, action.source);
    progress = applyCommandProgress(lesson, progress, result, command);
  }
  assert(isLabComplete(lesson, progress, state), `${lesson.id} did not complete`);
  return { state, progress };
}

const pc = (source, command) => ({ source, command });

function assertPermutation(values, length, label) {
  const seen = new Set(values);
  assert(Array.isArray(values) && values.length === length, `${label} length mismatch`);
  assert(seen.size === length && values.every((value) => Number.isInteger(value) && value >= 0 && value < length), `${label} is not a permutation`);
}

function validateStepDemoLesson(lesson) {
  const allowed = new Set(["explanation", "multiple-choice", "observe", "forward-decision", "hex-input", "frame-builder"]);
  const objectiveIds = new Set((lesson.objectives || []).map((objective) => objective.id));
  const stepIds = new Set();
  assert(lesson.steps?.length === 6, "step demo should exercise all step types");
  for (const step of lesson.steps) {
    assert(step.id && !stepIds.has(step.id), `invalid step id ${step.id}`);
    stepIds.add(step.id);
    assert(allowed.has(step.type), `unsupported step type ${step.type}`);
    if (step.type === "multiple-choice" || step.type === "forward-decision") {
      assert(step.options.length >= 2, `${step.id} needs options`);
      assert(Number.isInteger(step.correctIndex) && step.correctIndex >= 0 && step.correctIndex < step.options.length, `${step.id} correctIndex`);
    }
    if (step.type === "hex-input") {
      assert(step.answer, `${step.id} needs answer`);
      assert((step.accept || [step.answer]).map((answer) => answer.trim().toLowerCase()).includes("0800"), `${step.id} accept normalization`);
    }
    if (step.type === "frame-builder") {
      assertPermutation(step.correctOrder, step.fields.length, `${step.id} correctOrder`);
    }
    if (step.type === "observe") {
      assert(step.objectiveIds.every((objectiveId) => objectiveIds.has(objectiveId)), `${step.id} unknown objective`);
    }
  }
}

validateStepDemoLesson({
  id: "step-demo",
  objectives: [
    { id: "enter-privileged", label: "Enter privileged mode", trigger: "mode.privileged.enter" },
    { id: "show-table", label: "Show MAC table", trigger: "cmd.show.mac-address-table" },
  ],
  steps: [
    { id: "s1", type: "explanation", title: "Read", body: "Ethernet frames have ordered fields." },
    { id: "s2", type: "multiple-choice", title: "Choose", question: "Which layer uses MAC addresses?", options: ["Layer 1", "Layer 2"], correctIndex: 1, explanation: "Switching uses Layer 2 addresses." },
    { id: "s3", type: "forward-decision", title: "Forward", question: "Unknown unicast?", options: ["Forward to g0/2 only", "Flood all ports in VLAN", "Drop the frame"], correctIndex: 1, explanation: "Unknown unicasts flood within the VLAN." },
    { id: "s4", type: "hex-input", title: "EtherType", question: "IPv4 EtherType?", answer: "0800", accept: ["0800", "0x0800"], explanation: "IPv4 uses 0x0800." },
    { id: "s5", type: "frame-builder", title: "Build", question: "Order the fields.", fields: ["Destination MAC", "Source MAC", "EtherType", "Payload", "FCS"], correctOrder: [0, 1, 2, 3, 4], explanation: "That is the Ethernet II order." },
    { id: "s6", type: "observe", title: "Observe", body: "Complete the CLI objectives.", objectiveIds: ["enter-privileged", "show-table"], explanation: "The terminal work matches the observation." },
  ],
});

const repeatedTriggerProgress = applyCommandProgress(
  {
    objectives: [
      { id: "first-interface-entry", label: "Enter interface g0/1", trigger: "mode.interface.enter" },
      { id: "second-interface-entry", label: "Enter interface g0/2 with shorthand", trigger: "mode.interface.enter" },
    ],
  },
  createProgress(),
  { events: [{ id: "mode.interface.enter", arg: "g0/1" }] },
  "interface g0/1"
);
assert(
  repeatedTriggerProgress.completed.length === 1 && repeatedTriggerProgress.completed.includes("first-interface-entry"),
  "one event must complete only one repeated-trigger objective"
);

const frameLesson = findNetworkFoundationsLesson("dev-nf-frame-001");
const frameState = initialState(frameLesson);
let frameProgress = createProgress();
[
  ["switch", "enable"],
  ["pc", "ping 192.168.10.20"],
  ["switch", "show mac address-table"],
].forEach(([target, command]) => {
  const result = target === "pc" ? runPcCommand(frameState, command) : runCommand(frameState, command);
  frameProgress = applyCommandProgress(frameLesson, frameProgress, result, command);
});
assert(
  ["ping-pc-b", "enter-privileged", "show-mac-table"].every((objectiveId) => frameProgress.completed.includes(objectiveId)),
  "out-of-order frame lesson should complete ping, enable, and show objectives"
);

const state = initialState();
assert(getPrompt(state) === "Switch>", "initial prompt");
runCommand(state, "enable");
assert(getPrompt(state) === "Switch#", "enable prompt");
runCommand(state, "config t");
runCommand(state, "hostname Branch-SW1");
assert(getPrompt(state) === "Branch-SW1(config)#", "hostname prompt");
runCommand(state, "end");
assert(runCommand(state, "sh st").event === "error.ambiguous", "ambiguous command");
assert(runCommand(state, "sh start").event === "cmd.show.startup-config", "startup resolves");
runCommand(state, "config t");
runCommand(state, "vlan 10");
assert(getPrompt(state) === "Branch-SW1(config-vlan)#", "vlan create enters vlan mode");
runCommand(state, "exit");
runCommand(state, "vlan 20");
runCommand(state, "end");
assert(runCommand(state, "show vlan brief").output.join("\n").includes("20"), "vlan brief includes 20");
runCommand(state, "config t");
runCommand(state, "interface g0/3");
runCommand(state, "no shutdown");
runCommand(state, "end");
assert(state.interfaces["g0/3"].shutdown === false, "g0/3 connected");
assert(runCommand(state, "write memory").output.includes("[OK]"), "write memory ok");

const auth = initialState({ startState: { enablePassword: "netadmin" } });
runCommand(auth, "enable");
assert(getPrompt(auth) === "Password: ", "password prompt");
runCommand(auth, "netadmin");
assert(getPrompt(auth) === "Switch#", "auth success");

const ssh = initialState();
[
  "enable",
  "conf t",
  "hostname SW1",
  "ip domain-name ccna.lab",
  "username admin privilege 15 password sshadmin",
  "enable secret cisco",
  "crypto key generate rsa modulus 2048",
  "interface vlan1",
  "ip address 192.168.1.1 255.255.255.0",
  "no shutdown",
  "exit",
  "line vty 0 4",
  "login local",
  "transport input ssh",
].forEach((command) => runCommand(ssh, command));
assert(runPcCommand(ssh, "ssh admin@192.168.1.1").event === "pc.ssh.connect", "pc ssh connect");
assert(redactCommandLog(ssh.commandLog).every((entry) => !String(entry.cmd).includes("sshadmin") && !String(entry.cmd).includes("cisco")), "command log redaction");

const macLesson = { topology: lessonPack.sharedTopology };
const pingState = initialState(macLesson);
const pingResult = runPcCommand(pingState, "ping 192.168.1.20");
assert(pingResult.event === "pc.ping.success", "pc ping success event");
assert(pingResult.output.join("\n").includes("ARP request: who has 192.168.1.20?"), "pc ping arp transcript");
assert(pingState.macTable.filter((entry) => entry.type === "DYNAMIC").length === 2, "pc ping learns two dynamic macs");
const pcCSource = initialState({
  topology: {
    devices: [
      { id: "main", type: "switch", label: "Switch" },
      { id: "PC-A", type: "pc", label: "PC-A", connectedTo: "g0/1", vlan: 10, ip: "192.168.10.10" },
      { id: "PC-B", type: "pc", label: "PC-B", connectedTo: "g0/2", vlan: 10, ip: "192.168.10.20" },
      { id: "PC-C", type: "pc", label: "PC-C", connectedTo: "g0/3", vlan: 20, ip: "192.168.20.30" },
      { id: "PC-D", type: "pc", label: "PC-D", connectedTo: "g0/4", vlan: 20, ip: "192.168.20.40" },
    ],
    interfaces: {
      "g0/1": { mode: "access", accessVlan: 10, shutdown: false },
      "g0/2": { mode: "access", accessVlan: 10, shutdown: false },
      "g0/3": { mode: "access", accessVlan: 20, shutdown: false },
      "g0/4": { mode: "access", accessVlan: 20, shutdown: false },
    },
  },
});
assert(runPcCommand(pcCSource, "ping 192.168.20.40", "PC-C").event === "pc.ping.success", "pc source selector supports PC-C ping");
const pcCArp = runPcCommand(pcCSource, "arp -a", "PC-C");
assert(pcCArp.event === "pc.arp.show" && pcCArp.output.join("\n").includes("192.168.20.40"), "pc arp cache event");
const pcAArp = runPcCommand(pcCSource, "arp -a", "PC-A").output.join("\n");
assert(pcAArp.includes("No dynamic entries") && !pcAArp.includes("192.168.20.40"), "pc arp cache is scoped to source pc");
runCommand(pingState, "enable");
const learnedTable = runCommand(pingState, "show mac").output.join("\n");
assert(learnedTable.includes("DYNAMIC") && learnedTable.includes("g0/1") && learnedTable.includes("g0/2"), "show mac renders learned entries");

const downState = initialState(macLesson);
runCommand(downState, "enable");
runCommand(downState, "conf t");
runCommand(downState, "interface g0/2");
runCommand(downState, "shutdown");
const downPing = runPcCommand(downState, "ping 192.168.1.20");
assert(downPing.event === "pc.ping.failed", "pc ping down interface fails");
assert(downPing.output.join("\n").includes("4 sent, 0 received, 4 lost"), "pc ping down interface loss summary");
assert(downState.macTable.length === 0, "failed ping does not learn macs");

const staticState = initialState(macLesson);
runCommand(staticState, "enable");
runCommand(staticState, "conf t");
const staticSet = runCommand(staticState, "mac address-table static cccc.cccc.cc0c vlan 1 interface gigabitethernet0/2");
assert(staticSet.event === "config.mac-static.set", "static mac set event");
assert(staticState.macTable.length === 1 && staticState.macTable[0].type === "STATIC", "static mac exists before traffic");
const staticShow = runCommand(staticState, "do show mac address-table").output.join("\n");
assert(staticShow.includes("STATIC") && staticShow.includes("cccc.cccc.cc0c") && staticShow.includes("g0/2"), "show mac renders static entry");

const portAdmin = initialState();
runCommand(portAdmin, "enable");
runCommand(portAdmin, "conf t");
let rangeResult = runCommand(portAdmin, "interface range g0/4 - 6");
assert(getPrompt(portAdmin) === "Switch(config-if-range)#", "interface range prompt");
assert(rangeResult.event === "mode.interface-range.enter" && rangeResult.events[0].arg === "g0/4 - 6", "interface range event");
runCommand(portAdmin, "shutdown");
assert(["g0/4", "g0/5", "g0/6"].every((name) => portAdmin.interfaces[name].shutdown), "range shutdown applies to all members");
runCommand(portAdmin, "no shutdown");
assert(["g0/4", "g0/5", "g0/6"].every((name) => !portAdmin.interfaces[name].shutdown), "range no shutdown applies to all members");
const missingVlan = runCommand(portAdmin, "switchport access vlan 30");
assert(missingVlan.output.includes("% Access VLAN does not exist. Creating vlan 30"), "missing access vlan notice");
assert(["g0/4", "g0/5", "g0/6"].every((name) => portAdmin.interfaces[name].accessVlan === 30), "range access vlan applies to all members");
assert(portAdmin.vlans["30"]?.name === "VLAN30" && portAdmin.vlans["30"].ports.includes("g0/6"), "implicit vlan created with ports");
runCommand(portAdmin, "exit");
runCommand(portAdmin, "vlan 40");
runCommand(portAdmin, "vlan 41");
assert(portAdmin.activeVlan === "41" && portAdmin.vlans["40"] && portAdmin.vlans["41"], "vlan-to-vlan context transition");
runCommand(portAdmin, "exit");
runCommand(portAdmin, "interface g0/1");
runCommand(portAdmin, "description Sales floor uplink");
runCommand(portAdmin, "interface g0/2");
runCommand(portAdmin, "description Adjacent desk");
assert(portAdmin.interfaces["g0/2"].description === "Adjacent desk", "interface-to-interface context transition");
runCommand(portAdmin, "interface g0/1");
runCommand(portAdmin, "switchport mode access");
runCommand(portAdmin, "switchport access vlan 10");
runCommand(portAdmin, "duplex half");
runCommand(portAdmin, "speed 100");
runCommand(portAdmin, "end");
assert(portAdmin.interfaces["g0/1"].description === "Sales floor uplink", "description with spaces stored intact");
const scopedConfig = runCommand(portAdmin, "show running-config interface g0/1").output.join("\n");
assert(scopedConfig.includes("description Sales floor uplink") && scopedConfig.includes("switchport access vlan 10"), "scoped running-config renders interface config");
assert(scopedConfig.includes("duplex half") && scopedConfig.includes("speed 100"), "scoped running-config renders link settings");
const switchportAudit = runCommand(portAdmin, "show interfaces g0/1 switchport").output.join("\n");
assert(switchportAudit.includes("Administrative Mode: static access") && switchportAudit.includes("Access Mode VLAN: 10"), "show interfaces switchport renders access audit");

const rangeCap = initialState();
runCommand(rangeCap, "enable");
runCommand(rangeCap, "conf t");
assert(runCommand(rangeCap, "interface range g0/1 - 49").output.includes("% Invalid input detected at '^' marker."), "interface range rejects ports above 48");

const filterState = initialState(macLesson);
filterState.macTable = [
  { mac: "aaaa.aaaa.aaaa", vlan: 10, port: "g0/1", type: "DYNAMIC" },
  { mac: "bbbb.bbbb.bbbb", vlan: 20, port: "g0/3", type: "DYNAMIC" },
  { mac: "cccc.cccc.cccc", vlan: 10, port: "g0/2", type: "STATIC" },
];
runCommand(filterState, "enable");
const dynamicOnly = runCommand(filterState, "show mac address-table dynamic").output.join("\n");
assert(dynamicOnly.includes("aaaa.aaaa.aaaa") && dynamicOnly.includes("bbbb.bbbb.bbbb") && !dynamicOnly.includes("cccc.cccc.cccc"), "dynamic mac filter");
const vlanOnly = runCommand(filterState, "show mac address-table vlan 10").output.join("\n");
assert(vlanOnly.includes("aaaa.aaaa.aaaa") && vlanOnly.includes("cccc.cccc.cccc") && !vlanOnly.includes("bbbb.bbbb.bbbb"), "vlan mac filter");
const interfaceOnly = runCommand(filterState, "show mac address-table interface g0/3").output.join("\n");
assert(interfaceOnly.includes("bbbb.bbbb.bbbb") && !interfaceOnly.includes("aaaa.aaaa.aaaa"), "interface mac filter");
const logLengthBeforeMissingMac = filterState.commandLog.length;
const missingVlanFilter = runCommand(filterState, "show mac address-table vlan");
assert(missingVlanFilter.output.includes("% Incomplete command.") && !missingVlanFilter.event, "missing vlan mac filter is incomplete");
assert(filterState.commandLog.length === logLengthBeforeMissingMac, "missing vlan mac filter is not logged");
const missingInterfaceFilter = runCommand(filterState, "show mac address-table interface");
assert(missingInterfaceFilter.output.includes("% Incomplete command.") && !missingInterfaceFilter.event, "missing interface mac filter is incomplete");
assert(filterState.commandLog.length === logLengthBeforeMissingMac, "missing interface mac filter is not logged");

const broadcastLesson = findNetworkFoundationsLesson("dev-nf-broadcast-001");
const broadcastState = initialState(broadcastLesson);
runCommand(broadcastState, "enable");
const broadcastVlans = runCommand(broadcastState, "show vlan brief").output.join("\n");
assert(broadcastVlans.includes("10   SALES") && broadcastVlans.includes("20   ENG"), "broadcast lesson vlan brief includes SALES and ENG");

const multiTopology = {
  devices: [
    { id: "SW1", type: "switch", hostname: "SW1" },
    { id: "SW2", type: "switch", hostname: "SW2" },
    { id: "PC-A", type: "pc", label: "PC-A", switch: "SW1", connectedTo: "g0/1", vlan: 10, ip: "192.168.10.10" },
    { id: "PC-B", type: "pc", label: "PC-B", switch: "SW2", connectedTo: "g0/1", vlan: 10, ip: "192.168.10.20" },
    { id: "PC-C", type: "pc", label: "PC-C", switch: "SW1", connectedTo: "g0/2", vlan: 20, ip: "192.168.20.30" },
    { id: "PC-D", type: "pc", label: "PC-D", switch: "SW2", connectedTo: "g0/2", vlan: 20, ip: "192.168.20.40" },
    { id: "PC-E", type: "pc", label: "PC-E", switch: "SW1", connectedTo: "g0/3", vlan: 1, ip: "192.168.1.10" },
    { id: "PC-F", type: "pc", label: "PC-F", switch: "SW2", connectedTo: "g0/3", vlan: 1, ip: "192.168.1.20" },
  ],
  interfaces: {
    SW1: {
      "g0/1": { mode: "access", accessVlan: 10, shutdown: false },
      "g0/2": { mode: "access", accessVlan: 20, shutdown: false },
      "g0/3": { mode: "access", accessVlan: 1, shutdown: false },
      "g0/24": { mode: "access", accessVlan: 1, shutdown: false },
    },
    SW2: {
      "g0/1": { mode: "access", accessVlan: 10, shutdown: false },
      "g0/2": { mode: "access", accessVlan: 20, shutdown: false },
      "g0/3": { mode: "access", accessVlan: 1, shutdown: false },
      "g0/24": { mode: "access", accessVlan: 1, shutdown: false },
    },
  },
  vlans: {
    SW1: { "10": { name: "SALES", ports: ["g0/1"] }, "20": { name: "IT", ports: ["g0/2"] } },
    SW2: { "10": { name: "SALES", ports: ["g0/1"] }, "20": { name: "IT", ports: ["g0/2"] } },
  },
  links: [{ a: "SW1:g0/24", b: "SW2:g0/24" }],
};
const multiLesson = { id: "multi-sanity", title: "multi", topology: multiTopology };
const rangeTopology = {
  ...multiTopology,
  devices: [
    ...multiTopology.devices,
    { id: "PC-G", type: "pc", label: "PC-G", switch: "SW1", connectedTo: "g0/4", vlan: 15, ip: "192.168.15.10" },
    { id: "PC-H", type: "pc", label: "PC-H", switch: "SW2", connectedTo: "g0/4", vlan: 15, ip: "192.168.15.20" },
  ],
  interfaces: {
    SW1: { ...multiTopology.interfaces.SW1, "g0/4": { mode: "access", accessVlan: 15, shutdown: false } },
    SW2: { ...multiTopology.interfaces.SW2, "g0/4": { mode: "access", accessVlan: 15, shutdown: false } },
  },
  vlans: {
    SW1: { ...multiTopology.vlans.SW1, "15": { name: "VOICE", ports: ["g0/4"] } },
    SW2: { ...multiTopology.vlans.SW2, "15": { name: "VOICE", ports: ["g0/4"] } },
  },
};

let multiStates = initialDeviceStates(multiLesson);
assert(runMultiPcCommand(multiStates, multiTopology, "ping 192.168.10.20", "PC-A").event === "pc.ping.failed", "cross-switch ping fails before trunk");
configureTrunk(multiStates, multiTopology, "SW1");
configureTrunk(multiStates, multiTopology, "SW2");
const trunkPing = runMultiPcCommand(multiStates, multiTopology, "ping 192.168.10.20", "PC-A");
assert(trunkPing.event === "pc.ping.success" && trunkPing.output.join("\n").includes("802.1Q tag VLAN 10 added"), "cross-switch trunk ping succeeds with transcript");
const pcAMac = multiStates.SW1.pcDevices.find((pcDevice) => pcDevice.id === "PC-A").mac;
assert(multiStates.SW2.macTable.some((entry) => entry.mac === pcAMac && entry.port === "g0/24"), "remote switch learns source MAC on trunk port");
assert(commandOn(multiStates, multiTopology, "SW1", "show cdp neighbors").event === "cmd.show.cdp-neighbors", "cdp neighbors event");
assert(commandOn(multiStates, multiTopology, "SW1", "show lldp neighbors").output.join("\n").includes("SW2"), "lldp neighbors renders peer");

multiStates = initialDeviceStates({
  ...multiLesson,
  startState: { devices: { SW1: { interfaces: { "g0/24": { encapsulationRequired: true } } } } },
});
commandOn(multiStates, multiTopology, "SW1", "enable");
configureTrunk(multiStates, multiTopology, "SW2");
runOnTrunkInterface(multiStates, multiTopology, "SW1", "switchport mode trunk");
assert(runMultiPcCommand(multiStates, multiTopology, "ping 192.168.10.20", "PC-A").event === "pc.ping.failed", "encapsulationRequired trunk without dot1q fails");
runOnTrunkInterface(multiStates, multiTopology, "SW1", "switchport trunk encapsulation dot1q");
assert(runMultiPcCommand(multiStates, multiTopology, "ping 192.168.10.20", "PC-A").event === "pc.ping.success", "encapsulationRequired trunk with dot1q succeeds");

multiStates = initialDeviceStates(multiLesson);
configureTrunk(multiStates, multiTopology, "SW1");
configureTrunk(multiStates, multiTopology, "SW2");
runOnTrunkInterface(multiStates, multiTopology, "SW2", "switchport trunk native vlan 99");
assert(runMultiPcCommand(multiStates, multiTopology, "ping 192.168.1.20", "PC-E").event === "pc.ping.failed", "native vlan mismatch fails vlan 1 ping");
runOnTrunkInterface(multiStates, multiTopology, "SW1", "switchport trunk native vlan 99");
assert(runMultiPcCommand(multiStates, multiTopology, "ping 192.168.1.20", "PC-E").event === "pc.ping.success", "matching native vlans restore vlan 1 ping");

multiStates = initialDeviceStates(multiLesson);
configureTrunk(multiStates, multiTopology, "SW1");
configureTrunk(multiStates, multiTopology, "SW2");
runOnTrunkInterface(multiStates, multiTopology, "SW2", "switchport trunk allowed vlan 20");
assert(runMultiPcCommand(multiStates, multiTopology, "ping 192.168.10.20", "PC-A").event === "pc.ping.failed", "allowed vlan pruning blocks vlan 10");
runOnTrunkInterface(multiStates, multiTopology, "SW2", "switchport trunk allowed vlan add 10");
assert(runMultiPcCommand(multiStates, multiTopology, "ping 192.168.10.20", "PC-A").event === "pc.ping.success", "allowed vlan add restores vlan 10");

multiStates = initialDeviceStates({ id: "range-sanity", title: "range", topology: rangeTopology });
configureTrunk(multiStates, rangeTopology, "SW1");
configureTrunk(multiStates, rangeTopology, "SW2");
runOnTrunkInterface(multiStates, rangeTopology, "SW2", "switchport trunk allowed vlan 10-20");
assert(runMultiPcCommand(multiStates, rangeTopology, "ping 192.168.15.20", "PC-G").event === "pc.ping.success", "allowed vlan range permits vlan 15");
const allowedBeforeInvalid = JSON.stringify(multiStates.SW2.interfaces["g0/24"].allowedVlans);
const invalidAllowed = runOnTrunkInterfaceResult(multiStates, rangeTopology, "SW2", "switchport trunk allowed vlan 10,abc");
assert(invalidAllowed.output.includes("% Invalid input detected at '^' marker.") && invalidAllowed.events.length === 0, "invalid allowed vlan token is rejected without event");
assert(JSON.stringify(multiStates.SW2.interfaces["g0/24"].allowedVlans) === allowedBeforeInvalid, "invalid allowed vlan token does not change state");

multiStates = initialDeviceStates(multiLesson);
commandOn(multiStates, multiTopology, "SW1", "enable");
commandOn(multiStates, multiTopology, "SW2", "enable");
runOnTrunkInterfaceMany(multiStates, multiTopology, "SW1", ["switchport trunk encapsulation dot1q", "switchport mode dynamic desirable"]);
runOnTrunkInterfaceMany(multiStates, multiTopology, "SW2", ["switchport trunk encapsulation dot1q", "switchport mode dynamic auto"]);
const dtpTrunk = commandOn(multiStates, multiTopology, "SW1", "show interfaces trunk").output.join("\n");
assert(dtpTrunk.includes("desirable") && runMultiPcCommand(multiStates, multiTopology, "ping 192.168.10.20", "PC-A").event === "pc.ping.success", "desirable/auto negotiates trunk");
runOnTrunkInterface(multiStates, multiTopology, "SW1", "switchport mode dynamic auto");
assert(runMultiPcCommand(multiStates, multiTopology, "ping 192.168.10.20", "PC-A").event === "pc.ping.failed", "auto/auto does not negotiate trunk");

multiStates = initialDeviceStates(multiLesson);
commandOn(multiStates, multiTopology, "SW1", "enable");
commandOn(multiStates, multiTopology, "SW2", "enable");
commandOn(multiStates, multiTopology, "SW1", "configure terminal");
commandOn(multiStates, multiTopology, "SW1", "interface g0/24");
commandOn(multiStates, multiTopology, "SW1", "switchport mode dynamic auto");
const rejectedNonegotiate = commandOn(multiStates, multiTopology, "SW1", "switchport nonegotiate");
assert(
  rejectedNonegotiate.output.includes("Command rejected: Conflict between 'nonegotiate' and 'dynamic' status.") &&
    rejectedNonegotiate.events.length === 0 &&
    multiStates.SW1.interfaces["g0/24"].nonegotiate !== true,
  "nonegotiate on dynamic mode is rejected without state change"
);
commandOn(multiStates, multiTopology, "SW1", "end");
runOnTrunkInterfaceMany(multiStates, multiTopology, "SW1", ["switchport trunk encapsulation dot1q", "switchport mode trunk", "switchport nonegotiate"]);
runOnTrunkInterfaceMany(multiStates, multiTopology, "SW2", ["switchport trunk encapsulation dot1q", "switchport mode dynamic desirable"]);
assert(runMultiPcCommand(multiStates, multiTopology, "ping 192.168.10.20", "PC-A").event === "pc.ping.failed", "trunk nonegotiate does not form trunk with dynamic peer");
runOnTrunkInterface(multiStates, multiTopology, "SW2", "switchport mode trunk");
assert(runMultiPcCommand(multiStates, multiTopology, "ping 192.168.10.20", "PC-A").event === "pc.ping.success", "trunk nonegotiate forms trunk with static trunk peer");

const nativeArgState = initialState();
["enable", "configure terminal", "interface g0/1"].forEach((command) => runCommand(nativeArgState, command));
const invalidNative = runCommand(nativeArgState, "switchport trunk native vlan abc");
assert(invalidNative.output.includes("% Invalid input detected at '^' marker.") && invalidNative.events.length === 0, "native vlan non-numeric arg is invalid without event");
assert(nativeArgState.interfaces["g0/1"].nativeVlan === undefined, "invalid native vlan arg does not change state");

let scopedProgress = applyCommandProgress(
  { objectives: [{ id: "sw2-only", label: "SW2 only", trigger: "cmd.show.interfaces-trunk", device: "SW2" }] },
  createProgress(),
  { events: [{ id: "cmd.show.interfaces-trunk", device: "SW1" }] },
  "show interfaces trunk"
);
assert(!scopedProgress.completed.includes("sw2-only"), "SW1 event must not complete SW2-scoped objective");
scopedProgress = applyCommandProgress(
  { objectives: [{ id: "sw2-only", label: "SW2 only", trigger: "cmd.show.interfaces-trunk", device: "SW2" }] },
  scopedProgress,
  { events: [{ id: "cmd.show.interfaces-trunk", device: "SW2" }] },
  "show interfaces trunk"
);
assert(scopedProgress.completed.includes("sw2-only"), "SW2 event completes SW2-scoped objective");

const learnSwitchingDrives = {
  "dev-sw-act-01": ["enable", "show interfaces status"],
  "dev-sw-act-02": [
    "enable",
    "config t",
    "interface g0/1",
    "description Sales-PC",
    "interface g0/2",
    "description File-Server",
    "end",
    "show running-config interface g0/1",
  ],
  "dev-sw-act-03": ["enable", "config t", "interface g0/3", "shutdown", "interface g0/4", "no shutdown", "end", "show interfaces status"],
  "dev-sw-act-04": ["enable", "show interfaces status", "config t", "interface g0/2", "no shutdown", "end", "show vlan brief"],
  "dev-sw-act-05": ["enable", "config t", "interface range g0/4 - 6", "shutdown", "end", "show ip int brief"],
  "dev-sw-act-06": ["enable", "show interfaces status", "config t", "interface g0/2", "duplex half"],
  "dev-sw-act-07": [pc("PC-A", "ping 192.168.10.20")],
  "dev-sw-act-08": ["enable", "show interfaces status"],
  "dev-sw-act-09": [
    "enable",
    "show mac address-table",
    pc("PC-A", "ping 192.168.10.20"),
    pc("PC-A", "ping 192.168.10.20"),
    "show mac address-table",
    pc("PC-A", "ping 192.168.10.30"),
    pc("PC-A", "ping 192.168.10.40"),
    "show mac address-table",
  ],
  "dev-sw-act-10": [
    pc("PC-A", "ping 192.168.10.20"),
    pc("PC-C", "ping 192.168.20.40"),
    "enable",
    "show mac address-table dynamic",
    "show mac address-table vlan 10",
    "show mac address-table interface g0/3",
  ],
  "dev-sw-act-11": [pc("PC-A", "ping 192.168.10.20"), pc("PC-A", "arp -a")],
  "dev-sw-act-12": [pc("PC-A", "ping 192.168.10.20"), pc("PC-A", "ping 192.168.20.30")],
  "dev-sw-act-13": ["enable", "show interfaces status"],
  "dev-sw-act-14": ["enable", "config t", "vlan 10", "name SALES", "end", "show vlan brief"],
  "dev-sw-act-15": ["enable", "config t", "vlan 10", "name SALES", "vlan 20", "name HR", "vlan 30", "name IT", "end", "show vlan brief"],
  "dev-sw-act-16": ["enable", "show vlan brief", "config t", "vlan 10", "name SALES", "vlan 20", "name HR"],
  "dev-sw-act-17": ["enable", "config t", "vlan 10", "name SALES", "vlan 20", "name HR", "vlan 30", "name IT", "end", "show vlan brief"],
  "dev-sw-act-18": ["enable", "config t", "interface g0/1", "switchport mode access", "switchport access vlan 10", "end", "show vlan brief"],
  "dev-sw-act-19": ["enable", "config t", "interface range g0/2 - 4", "switchport mode access", "switchport access vlan 10", "end", "show vlan brief"],
  "dev-sw-act-20": [
    "enable",
    "config t",
    "interface g0/1",
    "switchport mode access",
    "switchport access vlan 10",
    "interface g0/2",
    "switchport mode access",
    "switchport access vlan 10",
    pc("PC-A", "ping 192.168.10.20"),
  ],
  "dev-sw-act-21": ["enable", "show vlan brief", "config t", "interface g0/3", "switchport access vlan 10", pc("PC-A", "ping 192.168.10.30")],
  "dev-sw-act-22": ["enable", "show interfaces switchport"],
  "dev-sw-act-23": [
    "enable",
    "config t",
    "interface g0/1",
    "switchport mode access",
    "switchport access vlan 10",
    "interface g0/3",
    "switchport mode access",
    "switchport access vlan 20",
    "interface g0/2",
    "switchport mode access",
    "switchport access vlan 10",
    pc("PC-A", "ping 192.168.10.20"),
  ],
};

for (const lesson of learnSwitchingPack.lessons) {
  const actions = learnSwitchingDrives[lesson.id];
  assert(actions, `missing learn-switching drive for ${lesson.id}`);
  const { state } = runLessonDrive(packLesson(learnSwitchingPack, lesson), actions);
  if (lesson.id === "dev-sw-act-06") {
    assert(
      state.commandLog.some((entry) => entry.cmd === "show interfaces status") &&
        !state.commandLog.some((entry) => entry.cmd === "show interfaces"),
      "dev-sw-act-06 must complete through show interfaces status path"
    );
  }
}

runLesson("meet-cli-001", ["enable", "?", "config t"]);
runLesson("meet-cli-002", ["enable", "config t", "hostname Branch-SW1", "end", "show running-config"]);
runLessonDrive(findNetworkFoundationsLesson("dev-nf-encap-001"), ["enable", "show interfaces status"]);

console.log("CLI engine sanity passed.");
