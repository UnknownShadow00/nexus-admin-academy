function objectiveItems(lesson) {
  return lesson.objectives || [];
}

export const SUPPORTED_REQUIRED_STATE_KEYS = Object.freeze([
  "bannerSet",
  "consolePassword",
  "domainName",
  "enablePassword",
  "enableSecret",
  "g0/3Up",
  "hostname",
  "interfaces",
  "interfaceShutdown",
  "rsaGenerated",
  "users",
  "vlan1Ip",
  "vlansDetailed",
  "vlans",
  "vtyLogin",
  "vtyLoginLocal",
  "vtyPassword",
  "vtyTransportSsh",
]);

function eventList(result) {
  if (Array.isArray(result?.events)) return result.events;
  if (result?.event) return [{ id: result.event, arg: result.eventArg }];
  return [];
}

function matchesTrigger(item, events, rawCommand) {
  if (!item?.trigger) return false;
  if (item.trigger.startsWith?.("regex:")) {
    const pattern = item.trigger.slice("regex:".length);
    return new RegExp(pattern, "i").test(rawCommand || "");
  }
  return events.some((event) => {
    if (event.id !== item.trigger) return false;
    if (item.device && event.device !== item.device) return false;
    if (item.expectedArg === undefined) return true;
    return String(event.arg || "") === String(item.expectedArg);
  });
}

export function createProgress() {
  return { completed: [], completedMini: [] };
}

export function applyCommandProgress(lesson, progress, result, rawCommand = "") {
  const completed = new Set(progress.completed || []);
  const completedMini = new Set(progress.completedMini || []);
  const events = eventList(result);

  for (const objective of objectiveItems(lesson)) {
    if (completed.has(objective.id)) continue;

    const minis = objective.miniObjectives || [];
    if (minis.length) {
      const nextMini = minis.find((mini) => !completedMini.has(`${objective.id}:${mini.id}`));
      if (nextMini && matchesTrigger(nextMini, events, rawCommand)) {
        completedMini.add(`${objective.id}:${nextMini.id}`);
        if (minis.every((mini) => completedMini.has(`${objective.id}:${mini.id}`))) {
          completed.add(objective.id);
        }
        break;
      }
      continue;
    }

    if (matchesTrigger(objective, events, rawCommand)) {
      completed.add(objective.id);
      break;
    }
  }

  return { completed: [...completed], completedMini: [...completedMini] };
}

function commandRan(state, requiredCommand) {
  const expected = String(requiredCommand).toLowerCase();
  return (state.commandLog || []).some((entry) => {
    const raw = String(entry.cmd || "").toLowerCase();
    const canonical = String(entry.canonical || "").toLowerCase();
    return raw === expected || canonical === expected;
  });
}

function stateMatchesValue(state, key, expected) {
  if (key === "hostname") return state.hostname === expected;
  if (key === "enablePassword") return state.enablePassword === expected;
  if (key === "enableSecret") return state.enableSecret === expected;
  if (key === "consolePassword") return state.consolePassword === expected;
  if (key === "vtyPassword") return state.vtyPassword === expected;
  if (key === "vtyLogin") return state.vtyLogin === expected;
  if (key === "vtyLoginLocal") return state.vtyLoginLocal === expected;
  if (key === "bannerSet") return state.bannerSet === expected;
  if (key === "domainName") return state.domainName === expected;
  if (key === "rsaGenerated") return state.rsaGenerated === expected;
  if (key === "vlan1Ip") return state.vlan1Ip === expected;
  if (key === "vtyTransportSsh") return (state.vtyTransportInput === "ssh") === expected;
  if (key === "g0/3Up") return Boolean(state.interfaces?.["g0/3"] && !state.interfaces["g0/3"].shutdown) === expected;
  if (key === "interfaceShutdown") {
    return Object.values(state.interfaces || {}).some((iface) => Number(iface.accessVlan) === 20 && iface.shutdown === true) === expected;
  }
  if (key === "interfaces") {
    return Object.entries(expected || {}).every(([rawName, wanted]) => {
      const name = rawName.replace(/\s+/g, "").replace(/^gigabitethernet/i, "g").replace(/^vlan/i, "Vlan").replace(/^g/i, "g");
      const actual = state.interfaces?.[name];
      if (!actual) return false;
      return Object.entries(wanted || {}).every(([field, value]) => actual[field] === value);
    });
  }
  if (key === "vlans") {
    const actual = Object.keys(state.vlans || {}).sort();
    const wanted = (expected || []).map(String).sort();
    return actual.length === wanted.length && actual.every((value, index) => value === wanted[index]);
  }
  if (key === "vlansDetailed") {
    return Object.entries(expected || {}).every(([id, wanted]) => {
      const actual = state.vlans?.[String(id)];
      if (!actual) return false;
      if (wanted.name !== undefined && actual.name !== wanted.name) return false;
      if (wanted.ports) {
        const actualPorts = (actual.ports || []).slice().sort();
        const wantedPorts = wanted.ports.slice().sort();
        return wantedPorts.every((port) => actualPorts.includes(port));
      }
      return true;
    });
  }
  if (key === "users") {
    const actual = (state.users || []).map((user) => user.username).sort();
    const wanted = (expected || []).map(String).sort();
    return wanted.every((username) => actual.includes(username));
  }
  return state[key] === expected;
}

function requiredStateSatisfied(state, requiredState = {}) {
  return Object.entries(requiredState).every(([key, expected]) => stateMatchesValue(state, key, expected));
}

export function isLabComplete(lesson, progress, state) {
  const criteria = lesson.successCriteria || {};
  const objectivesComplete = objectiveItems(lesson).every((objective) => progress.completed?.includes(objective.id));
  const modesComplete = (criteria.requiredModes || []).every((mode) => (state.visitedModes || []).includes(mode));
  const commandsComplete = (criteria.requiredCommands || []).every((command) => commandRan(state, command));
  const stateComplete = requiredStateSatisfied(state, criteria.requiredState || {});
  const pcActionComplete = criteria.requiredPcAction ? (state.pcActions || []).some((cmd) => cmd.toLowerCase() === criteria.requiredPcAction.toLowerCase()) : true;

  return objectivesComplete && modesComplete && commandsComplete && stateComplete && pcActionComplete;
}

export function isObjectivesMet(lesson, progress, objectiveIds = []) {
  const knownObjectiveIds = new Set(objectiveItems(lesson).map((objective) => objective.id));
  return objectiveIds.every((objectiveId) => knownObjectiveIds.has(objectiveId) && progress.completed?.includes(objectiveId));
}

export function objectiveStatuses(lesson, progress) {
  return objectiveItems(lesson).map((objective) => ({
    ...objective,
    complete: progress.completed?.includes(objective.id),
  }));
}
