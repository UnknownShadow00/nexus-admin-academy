import { ArrowRight, Clock3, MessageSquareText } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import PageContainer from "../components/ui/PageContainer";
import PageHeader from "../components/ui/PageHeader";
import V2Status from "../components/v2/V2Status";
import { mentorFollowUpStatus, stageProgressStatus } from "../components/ui/statusFoundation";
import { TrainingDestination } from "../components/TrainingDestination";
import { getCurrentStudent } from "../hooks/useAuth";
import { useV2Access } from "../hooks/useV2Access";
import { checkInStudent, getStudentStats, getTrainingDashboard, getV2Learning } from "../services/api";

const LEARNING_KINDS = new Set(["lesson", "resource", "interaction", "quick_check", "module_quiz", "practical", "service_desk", "explain", "evidence", "next_stage"]);
const ACTIVITY_NAMES = {
  lesson: "Lesson", resource: "Required resource", interaction: "Interactive practice",
  quick_check: "Quick Check", module_quiz: "Final checkpoint", practical: "Practical",
  service_desk: "Service Desk task", explain: "Explain", evidence: "Course work", next_stage: "Next stage",
};
const ACTION_VERBS = {
  lesson: ["Open lesson", "Continue lesson"], resource: ["Open resource", "Continue lesson"],
  interaction: ["Try practice", "Continue practice"], quick_check: ["Take Quick Check", "Continue Quick Check"],
  module_quiz: ["Take checkpoint", "Continue checkpoint"], practical: ["Start practical", "Continue practical"],
  service_desk: ["Open Service Desk task", "Resume Service Desk task"], explain: ["Start explanation", "Continue explanation"],
  evidence: ["Open stage", "Continue stage"], next_stage: ["Continue to next stage", "Continue to next stage"],
};

// The route and status come from the server. This function changes presentation only.
export function buildContinueTarget(v2Learning, training) {
  const current = v2Learning?.current;
  if (current?.continue) {
    const next = current.continue;
    const isLearning = LEARNING_KINDS.has(next.kind) && next.available !== false;
    const action = ACTION_VERBS[next.kind];
    return {
      kind: next.kind, activityType: ACTIVITY_NAMES[next.kind] || "Course activity",
      certification: current.certification?.name, detail: current.module?.title,
      estimatedMinutes: next.estimated_minutes,
      label: isLearning ? (action?.[next.status === "in_progress" ? 1 : 0] || "Continue learning")
        : next.kind === "correction" ? "Update your practical"
          : next.kind === "review_pending" ? "View submission" : "View stage",
      status: next.kind === "review_pending" ? "awaiting_mentor_review"
        : next.kind === "correction" ? "needs_correction"
          : next.kind === "complete" ? "mastered"
            : next.kind === "next_stage" ? "up_next"
              : next.kind === "evidence" ? stageProgressStatus(current.progress) : next.status || "not_started",
      title: next.title, to: next.route, isLearning, v2: true,
    };
  }
  const module = training?.current_module;
  const next = training?.next_activity;
  if (training?.training_complete) return { kind: "complete", label: "Review training", to: "/learning-path", title: "Training complete", detail: "You can revisit the training you have finished.", isLearning: false };
  if (!module) return { kind: "legacy_empty", label: "Open Learning Path", to: "/learning-path", title: "Your learning path", detail: "See the training available to you.", isLearning: false };
  const fresh = module.stable_id === "module.orientation.nexus" && module.required_complete === 0;
  return {
    kind: "legacy", label: fresh ? "Start Training" : "Continue Training",
    to: next?.destination_route || module.route, title: next?.title || module.title,
    detail: (training?.current_stage?.title || "Learning Path") + " · " + module.title,
    activityType: next?.activity_label || "Training", estimatedMinutes: next?.estimated_minutes, isLearning: true,
  };
}

export function buildTodayModel(v2Learning, training) {
  const target = buildContinueTarget(v2Learning, training);
  const current = v2Learning?.current;
  const followUps = (v2Learning?.corrections || []).map((item) => ({
    type: "needs_correction", key: item.module_key + "-" + item.assessment_key,
    title: item.practical_title, stage: item.stage_title, route: item.route, feedback: item.feedback,
  }));
  for (const module of v2Learning?.modules || (current ? [current] : [])) {
    if (mentorFollowUpStatus(module.progress) !== "awaiting_mentor_review") continue;
    const practical = module.progress?.practical;
    const route = module.continue?.kind === "review_pending" ? module.continue.route
      : practical?.assessment_key ? "/learning-v2/modules/" + module.module.key + "/practical/" + practical.assessment_key
        : "/learning-v2/modules/" + module.module.key;
    followUps.push({ type: "awaiting_mentor_review", key: "pending-" + module.module.key, title: practical?.title || module.module.title, stage: module.module.title, route, sentAt: practical?.activity?.updated_at });
  }
  if (target.kind === "review_pending" && !followUps.some((item) => item.type === "awaiting_mentor_review")) {
    followUps.push({ type: "awaiting_mentor_review", key: "current-pending", title: target.title, stage: target.detail, route: target.to });
  }
  if (target.kind === "correction" && !followUps.some((item) => item.route === target.to)) {
    followUps.unshift({ type: "needs_correction", key: "current-correction", title: target.title, stage: target.detail, route: target.to });
  }
  const correction = followUps.find((item) => item.type === "needs_correction");
  const mode = target.isLearning ? "learning"
    : correction ? "correction"
      : current?.progress?.module_complete ? "mastered"
        : !current && target.kind === "complete" ? "legacy_complete"
          : followUps.some((item) => item.type === "awaiting_mentor_review") ? "waiting" : "up_to_date";
  return { target, followUps, correction, mode };
}

function MentorFollowUp({ items, learningAvailable = false }) {
  return <aside aria-label="Mentor follow-up" className="today-follow-up">
    <div className="flex items-center gap-2"><MessageSquareText size={17} aria-hidden="true" /><h2 className="type-section-title">Mentor follow-up</h2></div>
    {items.length ? <ul className="mt-4 space-y-3">{items.map((item) => <li className={"today-follow-up-item " + (item.type === "needs_correction" ? "today-follow-up-changes" : "today-follow-up-mentor")} key={item.key}>
      <V2Status status={item.type} />
      <p className="mt-3 font-semibold text-[var(--nexus-text)]">{item.title}</p>
      <p className="type-meta mt-1">{item.stage}</p>
      <p className="type-secondary mt-3">{item.type === "needs_correction"
        ? learningAvailable ? "Your mentor left feedback. You can keep learning while you update this." : "Your mentor left feedback. Update this practical when you're ready."
        : learningAvailable ? "Your practical is with your mentor. You can keep learning while it is reviewed." : "Your practical is with your mentor. You can review your work while you wait."}</p>
      {item.feedback ? <p className="today-feedback mt-3 whitespace-pre-wrap"><strong>Mentor feedback:</strong> {item.feedback}</p> : null}
      {item.sentAt ? <p className="type-meta mt-2">Sent {new Date(item.sentAt).toLocaleDateString()}</p> : null}
      <Link className="btn-quiet mt-3" to={item.route}>{item.type === "needs_correction" ? "See changes" : "View submission"}<ArrowRight size={16} aria-hidden="true" /></Link>
    </li>)}</ul> : <p className="type-secondary mt-3">Nothing waiting right now.</p>}
  </aside>;
}

function TodayContent({ model, training, v2Learning }) {
  const { target, followUps, correction, mode } = model;
  const current = v2Learning?.current;
  const secondaryFollowUps = mode === "correction" ? followUps.filter((item) => item.key !== correction?.key) : followUps;
  const primaryTitle = mode === "learning" ? target.title
    : mode === "correction" ? correction?.title || target.title
      : mode === "waiting" ? "Learning is up to date"
        : mode === "mastered" ? current?.module?.title || target.title
          : mode === "legacy_complete" ? target.title : "Nothing else to do here yet";
  const description = mode === "learning" ? (target.activityType || "Course work") + " is ready when you are."
    : mode === "correction" ? "Your mentor left feedback on this practical. This is a normal part of the process."
      : mode === "waiting" ? "You've finished the learning currently available here. Your practical is with your mentor."
        : mode === "mastered" ? "This stage is mastered. You can review your work in My Course."
          : mode === "legacy_complete" ? target.detail
          : current ? "Check My Course for the learning currently available to you." : "Open your learning path to see what is available.";
  const primaryLink = mode === "learning" ? { label: target.label, to: target.to }
    : mode === "correction" ? { label: "Update your practical", to: correction?.route }
      : mode === "mastered" ? { label: "View My Course", to: "/learning-v2" }
        : mode === "legacy_complete" ? { label: target.label, to: target.to } : null;
  return <>
    <div className={"today-layout" + (mode === "correction" && !secondaryFollowUps.length ? " today-layout-solo" : "")}>
      <section aria-labelledby="today-primary-heading" className={"today-primary" + (mode === "correction" ? " today-primary-correction" : "")}>
        <p className="type-label">{mode === "learning" ? "Up next" : mode === "correction" ? "Changes requested" : mode === "mastered" ? "Stage mastered" : mode === "legacy_complete" ? "Training complete" : "Current learning"}</p>
        <h2 id="today-primary-heading" className="today-primary-title">{primaryTitle}</h2>
        {current ? <p className="today-context">{current.certification?.name} <span aria-hidden="true">·</span> {mode === "correction" ? correction?.stage : current.module?.title}</p> : target.detail ? <p className="today-context">{target.detail}</p> : null}
        {mode === "learning" && target.v2 ? <div className="mt-4"><V2Status status={target.status} /></div> : mode === "mastered" && current ? <div className="mt-4"><V2Status status="mastered" /></div> : mode === "correction" ? <div className="mt-4"><V2Status status="needs_correction" /></div> : null}
        <p className="type-secondary mt-5 max-w-2xl">{description}</p>
        {mode === "correction" && correction?.feedback ? <p className="today-feedback mt-4 whitespace-pre-wrap"><strong>Mentor feedback:</strong> {correction.feedback}</p> : null}
        {primaryLink?.to ? <TrainingDestination activity={target.v2 ? null : training?.next_activity} to={primaryLink.to} className={(mode === "learning" || mode === "correction" ? "btn-primary" : "btn-secondary") + " today-primary-action mt-6"}>{primaryLink.label}<ArrowRight size={17} aria-hidden="true" /></TrainingDestination>
          : mode === "waiting" ? <Link className="btn-secondary mt-6" to="/learning-v2">View My Course</Link>
            : mode === "up_to_date" ? <Link className="btn-secondary mt-6" to={current ? "/learning-v2" : "/learning-path"}>View course</Link> : null}
        {mode === "learning" && target.estimatedMinutes ? <p className="type-meta mt-3 flex items-center gap-1.5"><Clock3 size={14} aria-hidden="true" />About {target.estimatedMinutes} min</p> : null}
      </section>
      {mode !== "correction" || secondaryFollowUps.length ? <MentorFollowUp items={secondaryFollowUps} learningAvailable={mode === "learning"} /> : null}
    </div>
    {current ? <footer className="today-quiet-links">
      <p className="today-bottom-line">Your full stage record is in <Link to="/learning-v2">My Course</Link>.</p>
      <p className="today-bottom-line">Want more practice? <Link to="/learning-path">Open Extra Practice</Link>.</p>
    </footer> : null}
  </>;
}

export default function StudentHome() {
  const studentId = getCurrentStudent()?.id;
  const [stats, setStats] = useState(null);
  const [training, setTraining] = useState(null);
  const [v2Learning, setV2Learning] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [retryKey, setRetryKey] = useState(0);
  const { studentEnabled: v2Enabled, loading: v2AccessLoading } = useV2Access(Boolean(studentId));

  useEffect(() => {
    if (!studentId) { setStats(null); setLoading(false); return; }
    if (v2AccessLoading) return;
    const run = async () => {
      setLoading(true);
      setLoadError("");
      try {
        await checkInStudent(studentId, { suppressToast: true }).catch(() => null);
        const [statsResponse, trainingResponse, learningResponse] = await Promise.all([
          getStudentStats(studentId, { suppressToast: true }),
          getTrainingDashboard({ suppressToast: true }),
          v2Enabled ? getV2Learning({ suppressToast: true }) : Promise.resolve(null),
        ]);
        setStats(statsResponse?.data || null);
        setTraining(trainingResponse?.data || null);
        setV2Learning(learningResponse?.data || null);
      } catch {
        setStats(null); setTraining(null); setV2Learning(null);
        setLoadError("Today could not be loaded. Check your connection, then try again.");
      } finally { setLoading(false); }
    };
    run();
  }, [retryKey, studentId, v2Enabled, v2AccessLoading]);

  const model = useMemo(() => buildTodayModel(v2Learning, training), [v2Learning, training]);
  if (loading) return <PageContainer><div className="panel h-48 animate-pulse" role="status" aria-label="Loading Today" /></PageContainer>;
  if (!stats) return <PageContainer width="reading"><div className="panel" role="alert"><h1 className="type-page-title">Today is temporarily unavailable</h1><p className="type-secondary mt-2">{loadError || "Sign in again to continue your training."}</p><button className="btn-primary mt-4" onClick={() => setRetryKey((value) => value + 1)} type="button">Try again</button></div></PageContainer>;
  return <PageContainer className="today-page space-y-8">
    <PageHeader title="Today" subtitle={stats.name ? "Good to see you, " + stats.name + ". Here is your next step." : "Here is your next step."} />
    <TodayContent model={model} training={training} v2Learning={v2Learning} />
  </PageContainer>;
}
