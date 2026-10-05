import { ArrowRight } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import V2Breadcrumbs from "../../components/v2/V2Breadcrumbs";
import { V2Error, V2Loading } from "../../components/v2/V2PageState";
import V2ResourceCard from "../../components/v2/V2ResourceCard";
import V2StageSequence from "../../components/v2/V2StageSequence";
import V2Status from "../../components/v2/V2Status";
import { getV2Module } from "../../services/api";
import { practicalDisplayStatus, stageProgressStatus } from "../../components/ui/statusFoundation";
import PageContainer from "../../components/ui/PageContainer";
import PageHeader from "../../components/ui/PageHeader";

function MentorFollowUp({ practicals, beginner, next }) {
  const items = practicals.map((item) => ({ item, status: practicalDisplayStatus(item.progress, beginner) }))
    .filter(({ status }) => ["awaiting_mentor_review", "needs_correction"].includes(status));
  if (!items.length) return null;
  return <section className="stage-follow-up" aria-labelledby="stage-follow-up-heading">
    <div><p className="type-label">Separate from learning progress</p><h2 id="stage-follow-up-heading" className="type-section-title mt-1">Mentor follow-up</h2></div>
    <ul className="stage-follow-up-list">{items.map(({ item, status }) => {
      const correction = status === "needs_correction";
      const feedback = item.progress?.detail?.review_feedback;
      return <li className={`stage-follow-up-item ${correction ? "stage-follow-up-changes" : "stage-follow-up-pending"}`} key={item.key}>
        <div className="flex flex-wrap items-center gap-2"><V2Status status={status} /><strong>{item.title}</strong></div>
        <p className="type-secondary mt-2">{correction ? "Your mentor left feedback on this practical. You can keep learning while you update it." : "Your practical is with your mentor. Review your submission while you wait."}</p>
        {feedback ? <p className="stage-follow-up-feedback mt-2 whitespace-pre-wrap"><strong>Mentor feedback:</strong> {feedback}</p> : null}
        <Link className="btn-quiet mt-2" to={`/learning-v2/modules/${next.moduleKey}/practical/${item.key}`}>
          {correction ? "Fix & resubmit" : "View practical status"}<ArrowRight size={16} aria-hidden="true" />
        </Link>
      </li>;
    })}</ul>
    {next.kind === "next_stage" ? <p className="type-secondary mt-3">You can continue learning in a later stage while this practical is being reviewed or updated.</p> : null}
  </section>;
}

export default function V2ModulePage() {
  const { moduleKey } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => { setError(""); return getV2Module(moduleKey, { suppressToast: true }).then((res) => setData(res.data)).catch((err) => setError(err?.response?.status === 404 ? "That module could not be found." : err?.userMessage || "The module could not be loaded.")); }, [moduleKey]);
  useEffect(() => { void load(); }, [load]);
  if (error) return <V2Error title="Module unavailable" message={error} onRetry={load} />;
  if (!data) return <V2Loading text="Loading module..." />;
  const beginner = data.certification.version?.key === "nexus_beginner_aplus_v1";
  const workName = beginner ? "stage" : "module";
  const practicals = data.assessments.filter((item) => item.role === "practical");
  const next = data.continue;
  const nextAction = next?.route && next.kind !== "blocked" ? <Link className={`${["review_pending", "complete"].includes(next.kind) ? "btn-secondary" : "btn-primary"} stage-header-action`} to={next.route}>
    {next.kind === "review_pending" ? "View practical status" : next.kind === "correction" ? "Update practical" : next.kind === "complete" ? `Review ${workName}` : next.label}<ArrowRight size={17} aria-hidden="true" />
  </Link> : null;
  return <PageContainer className="stage-page space-y-8">
    <PageHeader breadcrumb={<V2Breadcrumbs certification={data.certification} module={data.module} />}
      eyebrow={data.certification.name} title={data.module.title} description={data.module.description}
      status={<><V2Status status={stageProgressStatus(data.progress)} />{data.progress.review_due ? <V2Status status="review_due" /> : null}</>}
      actions={nextAction} />
    <section id="stage-work-plan" aria-labelledby="stage-work-plan-heading" className="stage-work-plan">
      <div className="stage-section-heading"><p className="type-label">Current learning and requirements</p><h2 id="stage-work-plan-heading" className="type-section-title mt-1">Your work plan</h2><p className="type-secondary mt-1">Follow the authored learning sequence. Opening a resource is separate from passing a check or mastering this {workName}.</p></div>
      <V2StageSequence data={data} next={next} />
    </section>
    {data.module_resources?.length ? <section aria-labelledby="module-resources-heading" className="stage-resources"><h2 id="module-resources-heading" className="type-section-title">Further resources</h2><p className="type-secondary mt-1 mb-4">Opening a link does not count as mastery.</p><div className="space-y-3">{data.module_resources.map((resource) => <V2ResourceCard key={resource.key} resource={resource} moduleKey={moduleKey} onChanged={load} />)}</div></section> : null}
    <MentorFollowUp practicals={practicals} beginner={beginner} next={{ ...next, moduleKey: data.module.key }} />
    <section aria-labelledby="stage-mastery-heading" className="stage-mastery">
      <div><p className="type-label">Completion record</p><h2 id="stage-mastery-heading" className="type-section-title mt-1">{beginner ? "Stage" : "Module"} mastery</h2><p className="type-secondary mt-1">{data.progress.module_complete ? `This ${workName} is mastered.` : `This ${workName} is not yet mastered. Practical approval and other learning requirements are tracked separately.`}</p></div>
      {data.progress.module_complete ? <V2Status status="mastered" /> : <span className="type-secondary font-semibold">Not yet mastered</span>}
    </section>
  </PageContainer>;
}
