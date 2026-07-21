import { RotateCcw } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import { completeCliLab } from "../../../services/api";
import { getPrerequisiteLock } from "../../../components/PrerequisiteLock";
import { cloneState, completeCommand, getPrompt, initialState, redactCommandLog, runCommand, runPcCommand } from "../engine/commandEngine";
import { aggregateDeviceState, cloneDeviceStates, initialDeviceStates, isMultiSwitchTopology, switchDevices } from "../engine/multiDeviceState";
import { runMultiPcCommand } from "../engine/networkSim";
import { applyCommandProgress, createProgress, isLabComplete, isObjectivesMet } from "../engine/objectiveTracker";
import CliTerminal from "./CliTerminal";
import ObjectivesPanel from "./ObjectivesPanel";
import PcTerminal from "./PcTerminal";
import StepPanel from "./StepPanel";
import TopologyPanel from "./TopologyPanel";

function initialLines(lesson) {
  return [
    { text: "Nexus Cisco IOS Simulator" },
    { text: `${lesson.title} | ${lesson.vendorId}` },
    { text: "" },
  ];
}

function commandDisplay(prompt, command, mask = false) {
  return { kind: "input", text: `${prompt}${mask ? "*".repeat(command.length) : command}` };
}

function objectiveUsesPcTerminal(objective) {
  const triggers = [objective?.trigger, ...(objective?.miniObjectives || []).map((mini) => mini.trigger)];
  return triggers.some((trigger) => String(trigger || "").startsWith("pc."));
}

function tagResultEvents(result, deviceId) {
  const events = (result.events || (result.event ? [{ id: result.event, arg: result.eventArg }] : [])).map((event) => ({
    ...event,
    device: event.device || deviceId,
  }));
  return { ...result, events, event: events[0]?.id };
}

function mapInitialLines(lesson, devices) {
  return Object.fromEntries(devices.map((device) => [device.id, initialLines({ ...lesson, title: `${lesson.title} | ${device.id}` })]));
}

export default function LabRunner({ lesson, initialCompleted = false, onPrerequisiteLocked }) {
  const topology = lesson.topology || {};
  const devices = useMemo(() => switchDevices(topology), [topology]);
  const isMultiSwitch = isMultiSwitchTopology(topology);
  const [switchState, setSwitchState] = useState(() => initialState(lesson));
  const [deviceStates, setDeviceStates] = useState(() => (isMultiSwitch ? initialDeviceStates(lesson) : {}));
  const [activeDeviceId, setActiveDeviceId] = useState(() => devices[0]?.id || "main");
  const [progress, setProgress] = useState(() => createProgress());
  const [lines, setLines] = useState(() => initialLines(lesson));
  const [deviceLines, setDeviceLines] = useState(() => (isMultiSwitch ? mapInitialLines(lesson, devices) : {}));
  const [pcLines, setPcLines] = useState([]);
  const [complete, setComplete] = useState(false);
  const [completion, setCompletion] = useState(initialCompleted ? { xp_awarded: 0, duplicate_completion: true } : null);
  const [posting, setPosting] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [completedStepIds, setCompletedStepIds] = useState([]);
  const startedAtRef = useRef(Date.now());
  const completionPostedRef = useRef(false);

  const activeSwitchState = isMultiSwitch ? deviceStates[activeDeviceId] || Object.values(deviceStates)[0] : switchState;
  const prompt = getPrompt(activeSwitchState);
  const requiresPcTerminal = Boolean(
    lesson.successCriteria?.requiredPcAction || lesson.objectives?.some((objective) => objectiveUsesPcTerminal(objective))
  );
  const scenario = useMemo(() => lesson.scenario || "", [lesson.scenario]);
  const hasSteps = Boolean(lesson.steps?.length);
  const pcDevices = useMemo(() => (lesson.topology?.devices || []).filter((device) => device.type === "pc"), [lesson.topology]);

  useEffect(() => {
    if (initialCompleted) {
      setCompletion({ xp_awarded: 0, duplicate_completion: true });
    }
  }, [initialCompleted]);

  function areStepsComplete(stepIds = completedStepIds) {
    return !hasSteps || lesson.steps.every((step) => stepIds.includes(step.id));
  }

  function updateCompletionState(state, nextProgress, stepIds = completedStepIds) {
    const completionState = isMultiSwitch ? aggregateDeviceState(state) : state;
    const done = isLabComplete(lesson, nextProgress, completionState) && areStepsComplete(stepIds);
    setComplete(done);
    postCompletion(completionState, done);
    return done;
  }

  useEffect(() => {
    if (!hasSteps) return;
    const currentStep = lesson.steps[currentStepIndex];
    if (currentStep?.type !== "observe") return;
    if (completedStepIds.includes(currentStep.id)) return;
    if (!isObjectivesMet(lesson, progress, currentStep.objectiveIds || [])) return;

    const nextStepIds = [...completedStepIds, currentStep.id];
    setCompletedStepIds(nextStepIds);
    updateCompletionState(isMultiSwitch ? deviceStates : switchState, progress, nextStepIds);
  }, [completedStepIds, currentStepIndex, deviceStates, hasSteps, isMultiSwitch, lesson, progress, switchState]);

  async function postCompletion(state, done) {
    if (!done || completionPostedRef.current) return;
    completionPostedRef.current = true;
    setPosting(true);
    try {
      const response = await completeCliLab(
        lesson.id,
        { commandLog: redactCommandLog(state.commandLog || []), durationMs: Date.now() - startedAtRef.current },
        { suppressToast: true }
      );
      setCompletion(response.data);
      toast.success(response.data?.xp_awarded ? `CLI lab complete: +${response.data.xp_awarded} XP` : "CLI lab complete");
    } catch (error) {
      completionPostedRef.current = false;
      const lock = getPrerequisiteLock(error);
      if (lock) onPrerequisiteLocked?.(lock);
      else toast.error(error?.userMessage || "CLI lab complete locally, but progress could not be saved.");
    } finally {
      setPosting(false);
    }
  }

  function applyResult(workingState, result, rawCommand) {
    const nextProgress = applyCommandProgress(lesson, progress, result, rawCommand);
    if (isMultiSwitch) setDeviceStates(workingState);
    else setSwitchState(workingState);
    setProgress(nextProgress);
    updateCompletionState(workingState, nextProgress);
  }

  function completeStep(stepId) {
    if (!stepId || completedStepIds.includes(stepId)) return;
    const nextStepIds = [...completedStepIds, stepId];
    setCompletedStepIds(nextStepIds);
    updateCompletionState(isMultiSwitch ? deviceStates : switchState, progress, nextStepIds);
  }

  function continueStep() {
    setCurrentStepIndex((index) => Math.min(index + 1, Math.max((lesson.steps || []).length - 1, 0)));
  }

  function handleCommand(command) {
    const currentState = isMultiSwitch ? deviceStates[activeDeviceId] : switchState;
    const beforePrompt = getPrompt(currentState);
    const working = cloneState(currentState);
    const wasAuth = Boolean(working.pendingAuth);
    const context = isMultiSwitch ? { topology, deviceId: activeDeviceId, deviceStates: { ...deviceStates, [activeDeviceId]: working } } : {};
    const result = isMultiSwitch ? tagResultEvents(runCommand(working, command, context), activeDeviceId) : runCommand(working, command);
    const output = result.output || [];
    if (isMultiSwitch) {
      setDeviceLines((current) => ({
        ...current,
        [activeDeviceId]: [...(current[activeDeviceId] || []), commandDisplay(beforePrompt, command, wasAuth), ...output.map((text) => ({ text }))],
      }));
      applyResult({ ...deviceStates, [activeDeviceId]: working }, result, command);
      return;
    }
    setLines((current) => [...current, commandDisplay(beforePrompt, command, wasAuth), ...output.map((text) => ({ text }))]);
    applyResult(working, result, command);
  }

  function handleTabComplete(input) {
    const completed = completeCommand(activeSwitchState, input);
    if (completed.event) {
      const result = { events: [isMultiSwitch ? { ...completed.event, device: activeDeviceId } : completed.event], output: [] };
      applyResult(isMultiSwitch ? cloneDeviceStates(deviceStates) : cloneState(switchState), result, input);
    }
    return completed;
  }

  function handlePcCommand(command, pcId) {
    const working = isMultiSwitch ? cloneDeviceStates(deviceStates) : cloneState(switchState);
    const result = isMultiSwitch ? runMultiPcCommand(working, topology, command, pcId) : runPcCommand(working, command, pcId);
    setPcLines((current) => [...current, `${pcId || "PC-A"}> ${command}`, ...(result.output || [])]);
    applyResult(working, result, command);
  }

  function resetSession() {
    const fresh = initialState(lesson);
    const freshDevices = isMultiSwitch ? initialDeviceStates(lesson) : {};
    startedAtRef.current = Date.now();
    completionPostedRef.current = false;
    setSwitchState(fresh);
    setDeviceStates(freshDevices);
    setActiveDeviceId(devices[0]?.id || "main");
    setProgress(createProgress());
    setLines(initialLines(lesson));
    setDeviceLines(isMultiSwitch ? mapInitialLines(lesson, devices) : {});
    setPcLines([]);
    setComplete(false);
    setCompletion(null);
    setCurrentStepIndex(0);
    setCompletedStepIds([]);
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <section className="space-y-4">
        <div className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Scenario</h2>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600 dark:text-slate-300">{scenario}</p>
            </div>
            <button className="btn-secondary gap-2" type="button" onClick={resetSession}>
              <RotateCcw size={16} />
              Restart
            </button>
          </div>
          {lesson.hints?.length ? (
            <div className="flex flex-wrap gap-2">
              {lesson.hints.map((hint) => (
                <span key={hint} className="rounded-lg bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
                  {hint}
                </span>
              ))}
            </div>
          ) : null}
        </div>

        {hasSteps ? (
          <StepPanel
            lesson={lesson}
            currentStepIndex={currentStepIndex}
            completedStepIds={completedStepIds}
            onCompleteStep={completeStep}
            onContinue={continueStep}
          />
        ) : null}

        {isMultiSwitch ? (
          <div className="flex flex-wrap gap-2">
            {devices.map((device) => (
              <button
                key={device.id}
                type="button"
                onClick={() => setActiveDeviceId(device.id)}
                className={`rounded-lg border px-3 py-1.5 text-sm font-semibold transition ${
                  activeDeviceId === device.id
                    ? "border-blue-500 bg-blue-600 text-white dark:border-blue-400 dark:bg-blue-500"
                    : "border-slate-300 bg-white text-slate-700 hover:border-blue-300 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                }`}
              >
                {device.label || device.hostname || device.id}
              </button>
            ))}
          </div>
        ) : null}

        <CliTerminal
          prompt={prompt}
          lines={isMultiSwitch ? deviceLines[activeDeviceId] || [] : lines}
          onSubmit={handleCommand}
          onTabComplete={handleTabComplete}
          disabled={posting}
        />

        {requiresPcTerminal ? <PcTerminal lines={pcLines} onSubmit={handlePcCommand} disabled={posting} devices={pcDevices} /> : null}
      </section>

      <aside className="space-y-4">
        <ObjectivesPanel lesson={lesson} progress={progress} complete={complete} />
        <TopologyPanel topology={lesson.topology} />
        <section className="panel space-y-2 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Progress</h2>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {completion
              ? completion.xp_awarded
                ? `Saved with ${completion.xp_awarded} XP awarded.`
                : "Completion saved. XP was already awarded for this lab."
              : complete
                ? posting
                  ? "Saving completion..."
                  : "Complete locally."
                : "In progress."}
          </p>
        </section>
      </aside>
    </div>
  );
}
