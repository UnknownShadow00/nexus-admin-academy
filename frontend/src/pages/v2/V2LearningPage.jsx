import { ArrowRight, BookOpen, CheckCircle2, LockKeyhole } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getV2Learning } from "../../services/api";
import { V2Error, V2Loading } from "../../components/v2/V2PageState";
import V2Status, { statusLabel } from "../../components/v2/V2Status";
import { mentorFollowUpStatus, stageProgressStatus } from "../../components/ui/statusFoundation";
import FlashcardReviewPanel from "../../components/FlashcardReviewPanel";
import V2CorrectionAlerts from "../../components/v2/V2CorrectionAlerts";
import PageContainer from "../../components/ui/PageContainer";
import PageHeader from "../../components/ui/PageHeader";

export default function V2LearningPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    setError("");
    getV2Learning({ suppressToast: true }).then((res) => setData(res.data)).catch((err) => setError(err?.userMessage || "Your learning path is unavailable right now."));
  }, []);
  useEffect(load, [load]);
  if (error) return <V2Error message={error} onRetry={load} />;
  if (!data) return <V2Loading />;
  if (!data.current) return <V2Error title="No module is available yet" message="Your mentor can let you know when learning content is ready." />;
  const current = data.current;
  const beginner = current.certification.version.key === "nexus_beginner_aplus_v1";
  const lessons = current.progress.lessons;
  const examCode = current.certification.version.exam_codes?.[0] || current.certification.version.label;
  return <PageContainer className="space-y-6">
    <V2CorrectionAlerts corrections={data.corrections} />
    <PageHeader eyebrow="Your learning" title={current.certification.name} description={beginner ? `Stages 1–${data.modules.length} · Start here` : `${current.certification.version.label} · ${examCode}`} />
    <section className="surface-selected overflow-hidden p-5 sm:p-8">
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl">
          <p className="type-label">Current {beginner ? "stage" : "module"}</p>
          <h2 className="mt-2 text-2xl font-bold sm:text-3xl">{current.module.title}</h2>
          <p className="type-secondary mt-3">{current.module.description}</p>
          <div className="mt-5 flex flex-wrap gap-3 text-sm">
            <span className="status-tone status-tone-neutral gap-2 rounded-full px-3 py-1.5"><BookOpen size={16} aria-hidden="true" />{beginner ? `${lessons.total} topics` : `${lessons.completed} of ${lessons.total} lessons marked complete`}</span>
            {current.progress.module_complete ? <span className="status-tone status-tone-mastered rounded-full px-3 py-1.5"><CheckCircle2 size={16} aria-hidden="true" />{beginner ? "Stage mastered" : "Module mastered"}</span> : beginner ? <V2Status status={stageProgressStatus(current.progress)} /> : null}
            {beginner && mentorFollowUpStatus(current.progress) ? <V2Status status={mentorFollowUpStatus(current.progress)} /> : null}
          </div>
        </div>
        <Link className="btn-primary min-h-12 shrink-0 px-5" to={current.continue.route}>
          {current.continue.kind === "review_pending" ? "View practical status" : current.continue.label}<ArrowRight size={18} aria-hidden="true" />
        </Link>
      </div>
    </section>
    <section className="panel">
      <h2 className="text-lg font-bold">What comes next</h2>
      <p className="mt-2 text-slate-600 dark:text-slate-300">{current.continue.title}</p>
      <Link className="mt-3 inline-flex font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400" to={`/learning-v2/modules/${current.module.key}`}>View the whole {beginner ? "stage" : "module"} →</Link>
    </section>
    <section aria-labelledby="modules-heading">
      <h2 id="modules-heading" className="text-xl font-bold">{beginner ? "Your stages" : "A+ modules"}</h2>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {data.modules.map((item) => {
          const content = <><p className="text-xs font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">{item.locked ? "Locked" : beginner ? "Beginner A+ foundation" : item.certification.version.label}</p><h3 className="mt-1 font-bold">{item.module.title}</h3><p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{item.locked ? item.lock_reason : beginner ? `${statusLabel(stageProgressStatus(item.progress))} · ${item.progress.lessons.total} topics` : `${statusLabel(item.progress.status)} · ${item.progress.lessons.completed}/${item.progress.lessons.total} lessons marked complete`}</p>{beginner && mentorFollowUpStatus(item.progress) ? <div className="mt-2"><V2Status status={mentorFollowUpStatus(item.progress)} /></div> : null}{beginner && item.progress.status === "awaiting_mentor_review" && item.continue?.kind === "next_stage" ? <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">You can keep learning.</p> : null}</>;
          return item.locked ? <div className="panel block" key={item.module.key} aria-disabled="true"><LockKeyhole size={18} aria-hidden="true" className="mb-2 text-slate-500" />{content}</div> : <Link className="panel block hover:border-blue-300" key={item.module.key} to={`/learning-v2/modules/${item.module.key}`}>
            {content}
          </Link>;
        })}
      </div>
    </section>
    {beginner && data.modules.some((item) => item.progress.review_due) ? <section className="panel" aria-labelledby="review-heading"><h2 id="review-heading" className="text-xl font-bold">Review due</h2><p className="mt-1 mb-4 text-sm text-slate-600 dark:text-slate-300">A few questions are ready for another look. Review never blocks your stage.</p><FlashcardReviewPanel scope="beginner" /></section> : null}
  </PageContainer>;
}
