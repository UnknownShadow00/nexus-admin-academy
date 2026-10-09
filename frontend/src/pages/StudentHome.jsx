import { ArrowRight, MessageSquareText } from "lucide-react";
import { useContext, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import PageContainer from "../components/ui/PageContainer";
import TodayDashboard from "../components/academy/TodayDashboard";
import { LearnerStatsContext } from "../components/academy/LearnerShell";
import V2Status from "../components/v2/V2Status";
import { mentorFollowUpStatus, stageProgressStatus } from "../components/ui/statusFoundation";
import { TrainingDestination } from "../components/TrainingDestination";
import { getCurrentStudent } from "../hooks/useAuth";
import { useV2Access } from "../hooks/useV2Access";
import { checkInStudent, getStudentStats, getTrainingDashboard, getV2Learning, getV2Module } from "../services/api";

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

export default function StudentHome({ isDark = false }) {
  const publishStats = useContext(LearnerStatsContext);
  const studentId = getCurrentStudent()?.id;
  const [stats, setStats] = useState(null);
  const [training, setTraining] = useState(null);
  const [v2Learning, setV2Learning] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [retryKey, setRetryKey] = useState(0);
  const [detail, setDetail] = useState(null);
  const [detailState, setDetailState] = useState("idle");
  const [detailRetry, setDetailRetry] = useState(0);
  useEffect(() => { publishStats(stats); }, [stats, publishStats]);
  const { studentEnabled: v2Enabled, loading: v2AccessLoading } = useV2Access(Boolean(studentId));

  useEffect(() => {
    if (!studentId) { setStats(null); setLoading(false); return; }
    if (v2AccessLoading) return;
    let active = true;
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
        if (!active) return;
        setStats(statsResponse?.data || null);
        setTraining(trainingResponse?.data || null);
        setV2Learning(learningResponse?.data || null);
      } catch {
        if (!active) return;
        setStats(null); setTraining(null); setV2Learning(null);
        setLoadError("Today could not be loaded. Check your connection, then try again.");
      } finally { if (active) setLoading(false); }
    };
    run();
    return () => { active = false; };
  }, [retryKey, studentId, v2Enabled, v2AccessLoading]);

  const moduleKey = v2Learning?.current?.module?.key;
  useEffect(() => {
    let active = true;
    setDetail(null);
    if (!moduleKey || loading || !v2Enabled) { setDetailState("idle"); return; }
    setDetailState("loading");
    getV2Module(moduleKey, { suppressToast: true })
      .then(response => { if (active) { setDetail(response?.data || null); setDetailState("ready"); } })
      .catch(() => { if (active) setDetailState("error"); });
    return () => { active = false; };
  }, [moduleKey, detailRetry, loading, v2Enabled]);

  const model = useMemo(() => buildTodayModel(v2Learning, training), [v2Learning, training]);
  if (loading || v2AccessLoading) return <div className="today-loading" role="status" aria-label="Loading Today">Loading your next step…</div>;
  if (!stats) return <PageContainer width="reading"><div className="card today-state" role="alert"><h1 className="type-page-title">Today is temporarily unavailable</h1><p className="type-secondary mt-2">{loadError || "Sign in again to continue your training."}</p><button className="btn-primary mt-4" onClick={() => setRetryKey((value) => value + 1)} type="button">Try again</button></div></PageContainer>;
  return <TodayDashboard model={model} training={training} learning={v2Learning} detail={detail} detailState={detailState} reloadDetail={() => setDetailRetry(value => value + 1)} stats={stats} dark={isDark} MentorFollowUp={MentorFollowUp} />;
}
