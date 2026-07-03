import { CheckCircle2 } from "lucide-react";
import { useEffect, useState } from "react";
import FrameBuilderStep from "./steps/FrameBuilderStep";
import HexInputStep from "./steps/HexInputStep";
import McqStep from "./steps/McqStep";

function stepBody(step) {
  if (step.type === "explanation" || step.type === "observe") return step.body;
  return null;
}

export default function StepPanel({ lesson, currentStepIndex, completedStepIds, onCompleteStep, onContinue }) {
  const steps = lesson.steps || [];
  const step = steps[currentStepIndex];
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
  }, [step?.id]);

  if (!step) return null;

  const complete = completedStepIds.includes(step.id);
  const isLastStep = currentStepIndex >= steps.length - 1;

  function handleResult(correct = true) {
    if (!correct) {
      setError(true);
      return;
    }
    setError(false);
    onCompleteStep(step.id);
  }

  function handleExplanationContinue() {
    onCompleteStep(step.id);
    onContinue();
  }

  function renderStep() {
    if (step.type === "multiple-choice") return <McqStep key={step.id} step={step} onCorrect={handleResult} />;
    if (step.type === "forward-decision") return <McqStep key={step.id} step={step} decision onCorrect={handleResult} />;
    if (step.type === "hex-input") return <HexInputStep key={step.id} step={step} onCorrect={handleResult} />;
    if (step.type === "frame-builder") return <FrameBuilderStep key={step.id} step={step} onCorrect={handleResult} />;
    return <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">{stepBody(step)}</p>;
  }

  return (
    <section className="panel space-y-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-cyan-700 dark:text-cyan-300">
            Step {currentStepIndex + 1} of {steps.length}
          </p>
          <h2 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">{step.title}</h2>
        </div>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium capitalize text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          {step.type.replace("-", " ")}
        </span>
      </div>

      {renderStep()}

      {step.type === "observe" && !complete ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">Complete the listed objectives in the terminal to continue.</p>
      ) : null}

      {error ? (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
          Not quite — try again.
        </p>
      ) : null}

      {complete ? (
        <div className="space-y-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 dark:border-emerald-900/60 dark:bg-emerald-950/30">
          <div className="flex items-start gap-2 text-sm font-medium text-emerald-800 dark:text-emerald-200">
            <CheckCircle2 className="mt-0.5 shrink-0" size={17} />
            <span>{step.explanation || "Step complete."}</span>
          </div>
          {!isLastStep ? (
            <button className="btn-primary" type="button" onClick={onContinue}>
              Continue
            </button>
          ) : null}
        </div>
      ) : step.type === "explanation" ? (
        <button className="btn-primary" type="button" onClick={handleExplanationContinue}>
          Continue
        </button>
      ) : null}
    </section>
  );
}
