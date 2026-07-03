import { RotateCcw } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import { completeCliLab } from "../../../services/api";
import { cloneState, completeCommand, getPrompt, initialState, redactCommandLog, runCommand, runPcCommand } from "../engine/commandEngine";
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

export default function LabRunner({ lesson, initialCompleted = false }) {
  const [switchState, setSwitchState] = useState(() => initialState(lesson));
  const [progress, setProgress] = useState(() => createProgress());
  const [lines, setLines] = useState(() => initialLines(lesson));
  const [pcLines, setPcLines] = useState([]);
  const [complete, setComplete] = useState(false);
  const [completion, setCompletion] = useState(initialCompleted ? { xp_awarded: 0, duplicate_completion: true } : null);
  const [posting, setPosting] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [completedStepIds, setCompletedStepIds] = useState([]);
  const startedAtRef = useRef(Date.now());
  const completionPostedRef = useRef(false);

  const prompt = getPrompt(switchState);
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
    const done = isLabComplete(lesson, nextProgress, state) && areStepsComplete(stepIds);
    setComplete(done);
    postCompletion(state, done);
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
    updateCompletionState(switchState, progress, nextStepIds);
  }, [completedStepIds, currentStepIndex, hasSteps, lesson, progress, switchState]);

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
      toast.error(error?.userMessage || "CLI lab complete locally, but progress could not be saved.");
    } finally {
      setPosting(false);
    }
  }

  function applyResult(workingState, result, rawCommand) {
    const nextProgress = applyCommandProgress(lesson, progress, result, rawCommand);
    setSwitchState(workingState);
    setProgress(nextProgress);
    updateCompletionState(workingState, nextProgress);
  }

  function completeStep(stepId) {
    if (!stepId || completedStepIds.includes(stepId)) return;
    const nextStepIds = [...completedStepIds, stepId];
    setCompletedStepIds(nextStepIds);
    updateCompletionState(switchState, progress, nextStepIds);
  }

  function continueStep() {
    setCurrentStepIndex((index) => Math.min(index + 1, Math.max((lesson.steps || []).length - 1, 0)));
  }

  function handleCommand(command) {
    const beforePrompt = getPrompt(switchState);
    const working = cloneState(switchState);
    const wasAuth = Boolean(working.pendingAuth);
    const result = runCommand(working, command);
    const output = result.output || [];
    setLines((current) => [...current, commandDisplay(beforePrompt, command, wasAuth), ...output.map((text) => ({ text }))]);
    applyResult(working, result, command);
  }

  function handleTabComplete(input) {
    const completed = completeCommand(switchState, input);
    if (completed.event) {
      const result = { events: [completed.event], output: [] };
      applyResult(cloneState(switchState), result, input);
    }
    return completed;
  }

  function handlePcCommand(command, pcId) {
    const working = cloneState(switchState);
    const result = runPcCommand(working, command, pcId);
    setPcLines((current) => [...current, `${pcId || "PC-A"}> ${command}`, ...(result.output || [])]);
    applyResult(working, result, command);
  }

  function resetSession() {
    const fresh = initialState(lesson);
    startedAtRef.current = Date.now();
    completionPostedRef.current = false;
    setSwitchState(fresh);
    setProgress(createProgress());
    setLines(initialLines(lesson));
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

        <CliTerminal prompt={prompt} lines={lines} onSubmit={handleCommand} onTabComplete={handleTabComplete} disabled={posting} />

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
