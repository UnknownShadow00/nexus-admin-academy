import { ArrowRight, LockKeyhole } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getV2Learning, getV2Module } from "../../services/api";
import { V2Error, V2Loading } from "../../components/v2/V2PageState";
import V2Status from "../../components/v2/V2Status";
import V2StageSequence from "../../components/v2/V2StageSequence";
import { mentorFollowUpStatus, stageProgressStatus } from "../../components/ui/statusFoundation";
import FlashcardReviewPanel from "../../components/FlashcardReviewPanel";
import PageContainer from "../../components/ui/PageContainer";
import PageHeader from "../../components/ui/PageHeader";

const LEARNING_KINDS = new Set(["lesson", "resource", "interaction", "quick_check", "module_quiz", "practical", "service_desk", "explain", "evidence", "next_stage"]);

function courseGroups(modules) {
  const groups = new Map();
  for (const item of modules) {
    const key = item.certification.key || item.certification.name;
    if (!groups.has(key)) groups.set(key, { key, name: item.certification.name, modules: [] });
    groups.get(key).modules.push(item);
  }
  return [...groups.values()];
}

function StagePathRow({ item, current, detail, corrections }) {
  const active = item.module.key === current?.module.key;
  const beginner = item.certification.version?.key === "nexus_beginner_aplus_v1";
  const stageName = beginner ? "stage" : "module";
  const followUp = mentorFollowUpStatus(item.progress);
  const status = item.locked ? "locked" : active && stageProgressStatus(item.progress) === "not_started" ? "up_next" : stageProgressStatus(item.progress);
  const route = `/learning-v2/modules/${item.module.key}`;
  const next = item.continue;
  const nextIsLearning = active && LEARNING_KINDS.has(next?.kind) && next?.available !== false;
  const primaryAction = nextIsLearning || active && next?.kind === "correction";
  return <li className={`course-path-item ${active ? "course-path-current" : ""} ${item.locked ? "course-path-locked" : ""}`}>
    <span className="course-path-node" aria-hidden="true">{item.locked ? <LockKeyhole size={16} /> : item.progress.module_complete ? "✓" : ""}</span>
    <article className="course-path-content" aria-current={active ? "step" : undefined} aria-label={`${item.module.title}${active ? ", current " + stageName : ""}`}>
      <div className="course-path-heading">
        <div className="min-w-0">
          <p className="type-label">{active ? item.progress.module_complete ? `Completed ${stageName}` : `Current ${stageName}` : item.locked ? `Locked ${stageName}` : stageName}</p>
          <h3 className="course-path-title">{item.locked ? item.module.title : <Link to={route}>{item.module.title}</Link>}</h3>
        </div>
        <div className="course-path-status"><V2Status status={status} />{followUp ? <V2Status status={followUp} /> : null}</div>
      </div>
      {item.locked && item.lock_reason ? <p className="type-secondary mt-2">{item.lock_reason}</p> : null}
      {!item.locked && corrections.length ? <div className="course-path-follow-up" aria-label={`Changes requested for ${item.module.title}`}>
        {corrections.map((correction) => <p key={correction.assessment_key} className="type-secondary">
          <strong>{correction.practical_title}</strong>{correction.feedback ? ` · ${correction.feedback}` : " · Your mentor left feedback."}
          <Link className="course-path-follow-up-link" to={correction.route}>Review feedback</Link>
        </p>)}
      </div> : null}
      {!item.locked && followUp === "awaiting_mentor_review" ? <p className="type-secondary mt-2">Your practical is with your mentor.{active && nextIsLearning ? " You can keep learning." : ""}</p> : null}
      {active && !item.locked ? <div className="course-path-expanded">
        <div className="course-path-next">
          <div><p className="type-label">{nextIsLearning ? "Up next" : item.progress.module_complete ? `${stageName} complete` : "Current focus"}</p><p className="type-secondary mt-1">{next?.title || item.module.description}</p></div>
          {next?.route && next.kind !== "blocked" ? <Link className={`${primaryAction ? "btn-primary" : "btn-secondary"} course-path-action`} to={next.route}>
            {next.kind === "review_pending" ? "View practical status" : next.kind === "correction" ? "Update practical" : next.kind === "complete" ? `Review ${stageName}` : next.label}<ArrowRight size={16} aria-hidden="true" />
          </Link> : null}
        </div>
        {detail ? <V2StageSequence data={detail} summary next={next} /> : <p className="type-meta mt-3">Open this {stageName} to see its learning sequence.</p>}
        <Link className="btn-quiet mt-3" to={route}>View full {stageName}<ArrowRight size={16} aria-hidden="true" /></Link>
      </div> : null}
    </article>
  </li>;
}

export default function V2LearningPage() {
  const [data, setData] = useState(null);
  const [currentDetail, setCurrentDetail] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    setError("");
    getV2Learning({ suppressToast: true }).then((res) => setData(res.data)).catch((err) => setError(err?.userMessage || "Your learning path is unavailable right now."));
  }, []);
  useEffect(load, [load]);
  useEffect(() => {
    const key = data?.current?.module.key;
    if (!key) return;
    let active = true;
    setCurrentDetail(null);
    getV2Module(key, { suppressToast: true }).then((res) => { if (active) setCurrentDetail(res.data); }).catch(() => null);
    return () => { active = false; };
  }, [data?.current?.module.key]);
  if (error) return <V2Error message={error} onRetry={load} />;
  if (!data) return <V2Loading />;
  if (!data.current) return <V2Error title="No module is available yet" message="Your mentor can let you know when learning content is ready." />;
  const current = data.current;
  const groups = courseGroups(data.modules);
  const beginner = current.certification.version?.key === "nexus_beginner_aplus_v1";
  return <PageContainer className="space-y-8">
    <PageHeader eyebrow="My Course" title={current.certification.name} description={current.progress.module_complete && current.continue?.kind === "complete" ? `${current.module.title} is mastered. Review your completed learning below.` : `Your current ${beginner ? "stage" : "module"} is ${current.module.title}. Follow the course path below for completed and available work.`} />
    {groups.map((group) => <section key={group.key} aria-label={`${group.name} course path`}>
      <div className="mb-4">
        <h2 className="type-section-title">{group.key === (current.certification.key || current.certification.name) ? beginner ? "Your stages" : "Your modules" : group.name}</h2>
        <p className="type-secondary mt-1">{group.key === (current.certification.key || current.certification.name) ? `Your current work is expanded below. Earlier ${beginner ? "stages" : "modules"} remain available to review.` : "Available learning in this program."}</p>
      </div>
      <ol className="course-path">
        {group.modules.map((item) => <StagePathRow key={item.module.key} item={item} current={current}
          detail={item.module.key === current.module.key ? currentDetail : null}
          corrections={(data.corrections || []).filter((correction) => correction.module_key === item.module.key)} />)}
      </ol>
    </section>)}
    {beginner && data.modules.some((item) => item.progress.review_due) ? <section className="surface-subtle p-5" aria-labelledby="review-heading"><h2 id="review-heading" className="type-section-title">Review due</h2><p className="type-secondary mt-1 mb-4">A few questions are ready for another look. Review never blocks your stage.</p><FlashcardReviewPanel scope="beginner" /></section> : null}
  </PageContainer>;
}
