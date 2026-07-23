import { CheckCircle2, Circle, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getOrientationProgress, getWeekPlan, saveOrientationPractice, uploadOrientationEvidence } from "../services/api";

function Step({ complete, children }) {
  const Icon = complete ? CheckCircle2 : Circle;
  return (
    <li className="flex items-start gap-2 text-sm text-slate-700 dark:text-slate-300">
      <Icon className={complete ? "mt-0.5 shrink-0 text-emerald-600" : "mt-0.5 shrink-0 text-slate-400"} size={18} aria-hidden="true" />
      <div className="min-w-0">{children}</div>
    </li>
  );
}

export default function OrientationPracticePanel({ onProgressChange, refreshKey = 0 }) {
  const [progress, setProgress] = useState(null);
  const [response, setResponse] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [nextAction, setNextAction] = useState(null);

  const refresh = async () => {
    const res = await getOrientationProgress({ suppressToast: true });
    const next = res.data || null;
    setProgress(next);
    onProgressChange?.(next);
    return next;
  };

  useEffect(() => {
    refresh().catch(() => setProgress(null));
  }, [refreshKey]);

  useEffect(() => {
    if (!progress?.is_complete || !progress?.week_one_unlocked) return;
    getWeekPlan(1, { suppressToast: true })
      .then((res) => setNextAction(res.data?.next_action || null))
      .catch(() => setNextAction(null));
  }, [progress?.is_complete, progress?.week_one_unlocked]);

  async function savePractice() {
    if (!response.trim()) return;
    setSaving(true);
    setMessage("");
    try {
      const res = await saveOrientationPractice(response, { suppressToast: true });
      setProgress(res.data?.onboarding || null);
      onProgressChange?.(res.data?.onboarding || null);
      setMessage(res.data?.message || "Practice response saved.");
    } catch (err) {
      setMessage(err?.userMessage || "Save your lesson note and take the quiz first.");
    } finally {
      setSaving(false);
    }
  }

  async function uploadSample(file) {
    if (!file) return;
    setUploading(true);
    setMessage("");
    try {
      const res = await uploadOrientationEvidence(file, { suppressToast: true });
      await refresh();
      setMessage(res.data?.message || "Sample evidence saved.");
    } catch (err) {
      setMessage(err?.userMessage || "Unable to upload that sample file.");
    } finally {
      setUploading(false);
    }
  }

  if (!progress) return <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">Loading your guided practice…</div>;

  const steps = progress.steps || {};
  return (
    <section className="space-y-4 rounded-xl border border-blue-200 bg-blue-50/60 p-4 dark:border-blue-900 dark:bg-blue-950/20">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700 dark:text-blue-300">Week 0 guided practice</p>
        <h4 className="mt-1 font-semibold text-slate-900 dark:text-slate-100">Try the real workflow once, safely</h4>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">This is zero-stakes: no AI grading, no mentor review, no XP, and no ticket is created.</p>
      </div>

      <ol className="space-y-3">
        <Step complete={steps.lesson_note}>
          <strong>1. Save your note.</strong> Use the note box above to answer its one-sentence prompt. It saves to your account automatically.
        </Step>
        <Step complete={steps.quiz}>
          <strong>2. Take the required Week 0 checkpoint.</strong>{" "}
          {steps.lesson_note ? <Link className="font-medium text-blue-700 underline dark:text-blue-300" to={progress.quiz_route}>Open Ticketing Systems Quiz</Link> : "First save your note, then the quiz link will be ready."}
        </Step>
        <Step complete={steps.practice_response}>
          <strong>3. Save a harmless practice response.</strong>
          {steps.quiz ? (
            <div className="mt-2 space-y-2">
              <textarea className="input-field w-full" rows={2} value={response} onChange={(event) => setResponse(event.target.value)} placeholder="Example: I would check Home → This Week to find my next task." />
              <button className="btn-primary text-sm" disabled={saving || !response.trim()} onClick={savePractice} type="button">{saving ? "Saving…" : "Save practice response"}</button>
            </div>
          ) : <p className="mt-1 text-slate-500 dark:text-slate-400">Available after the short quiz.</p>}
        </Step>
        <Step complete={steps.optional_evidence}>
          <strong>4. Optional: upload a harmless sample screenshot.</strong>
          <label className="mt-2 inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-blue-700 dark:text-blue-300">
            <Upload size={16} /> {uploading ? "Uploading…" : "Choose a sample image or text file"}
            <input className="sr-only" disabled={uploading} accept="image/jpeg,image/png,image/webp,text/plain,.jpg,.jpeg,.png,.webp,.txt,.log" type="file" onChange={(event) => uploadSample(event.target.files?.[0])} />
          </label>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Optional only. It is labeled orientation evidence and never becomes ticket evidence.</p>
        </Step>
      </ol>

      {message ? <p className="rounded-lg bg-white/80 p-3 text-sm text-emerald-700 dark:bg-slate-900/70 dark:text-emerald-300">{message}</p> : null}
      {progress.is_complete && progress.week_one_unlocked ? (
        <div className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200">
          <p className="font-semibold">You completed the platform walkthrough.</p>
          <p className="mt-1">You can revisit this lesson anytime. Next, move into the first real Week 1 item.</p>
          {nextAction ? <Link className="btn-primary mt-3 text-sm" to={nextAction.route}>Continue to Week 1: {nextAction.title}</Link> : <Link className="btn-primary mt-3 text-sm" to="/">Return Home</Link>}
        </div>
      ) : null}
      {progress.is_complete && !progress.week_one_unlocked ? (
        <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
          <p className="font-semibold">Nice work on the walkthrough. One more required Week 0 step remains before Week 1 unlocks:</p>
          {progress.week_one_remaining_lessons?.length ? (
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {progress.week_one_remaining_lessons.map((lesson) => (
                <li key={lesson.id}><Link className="font-medium underline" to={lesson.route}>Complete {lesson.title}</Link></li>
              ))}
            </ul>
          ) : <Link className="mt-2 inline-block font-medium underline" to="/training">Return to My Training</Link>}
        </div>
      ) : null}
    </section>
  );
}
