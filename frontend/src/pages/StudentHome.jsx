import { ArrowRight, BookOpen, Brain, CheckCircle2, Circle, Clock3, FlaskConical, Flame, MessageSquare, Ticket, Trophy, Zap } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import FlashcardReviewPanel from "../components/FlashcardReviewPanel";
import { XPBadge } from "../components/ui/Badge";
import PageHeader from "../components/ui/PageHeader";
import { getCurrentStudent } from "../hooks/useAuth";
import { checkInStudent, getLabs, getServiceDeskProgressSummary, getStudentStats, getTrainingDashboard } from "../services/api";
import { iconSizes, scoreBand } from "../utils/theme";

function SkeletonCard() {
  return <div className="panel h-28 animate-pulse dark:border-slate-700 dark:bg-slate-900" />;
}

export default function StudentHome() {
  const studentId = getCurrentStudent()?.id;
  const [stats, setStats] = useState(null);
  const [training, setTraining] = useState(null);
  const [serviceDeskSummary, setServiceDeskSummary] = useState(null);
  const [activeLab, setActiveLab] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    if (!studentId) {
      setStats(null);
      setLoading(false);
      return;
    }
    const run = async () => {
      setLoading(true);
      setLoadError("");
      try {
        // A failed check-in must not block Today; awaiting the handled request
        // lets the following read include the latest streak when it succeeds.
        await checkInStudent(studentId, { suppressToast: true }).catch(() => null);
        const [res, trainingRes] = await Promise.all([
          getStudentStats(studentId, { suppressToast: true }),
          getTrainingDashboard({ suppressToast: true }),
        ]);
        setStats(res?.data || null);
        setTraining(trainingRes?.data || null);
      } catch {
        setStats(null);
        setTraining(null);
        setLoadError("Today could not be loaded. Check your connection, then try again.");
      } finally {
        setLoading(false);
      }
    };
    run();
  }, [retryKey, studentId]);

  useEffect(() => {
    if (!studentId) return;
    // Best-effort widgets: an active ticket, active lab, or mentor feedback
    // missing must never block the rest of the dashboard from rendering.
    getServiceDeskProgressSummary({ suppressToast: true })
      .then((res) => setServiceDeskSummary(res?.data || null))
      .catch(() => setServiceDeskSummary(null));
    getLabs(undefined, { suppressToast: true })
      .then((res) => {
        const rows = Array.isArray(res?.data) ? res.data : [];
        setActiveLab(rows.find((lab) => lab.status === "in_progress") || null);
      })
      .catch(() => setActiveLab(null));
  }, [studentId, retryKey]);

  const continueTarget = useMemo(() => {
    const module = training?.current_module;
    const stage = training?.current_stage;
    const next = training?.next_activity;
    if (!module) return { label: "Open Learning Path", to: "/learning-path", title: "Learning Path", detail: "Open your learning path." };
    if (training.training_complete) return { label: "Review Training", to: "/learning-path", title: "Training Complete", detail: "Review completed modules or revisit course content." };
    const fresh = module.stable_id === "module.orientation.nexus" && module.required_complete === 0;
    return {
      label: fresh ? "Start Training" : "Continue Training",
      to: next?.destination_route || module.route,
      title: fresh ? "Begin Your IT Training" : "Continue where you left off",
      detail: `${stage?.title || "Learning Path"} — ${module.title}`,
    };
  }, [training]);

  if (loading) {
    return (
      <main className="mx-auto max-w-5xl space-y-4 p-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((item) => <SkeletonCard key={item} />)}
        </div>
      </main>
    );
  }

  if (!stats) {
    return (
      <main className="mx-auto max-w-3xl p-6">
        <div className="panel text-center" role="alert">
          <h1 className="text-xl font-bold text-slate-950 dark:text-white">Today is temporarily unavailable</h1>
          <p className="mt-2 text-slate-600 dark:text-slate-300">{loadError || "Sign in again to continue your training."}</p>
          <button className="btn-primary mt-4" onClick={() => setRetryKey((value) => value + 1)} type="button">Try Again</button>
        </div>
      </main>
    );
  }

  const recent = (stats.recent_activity || []).slice(0, 5);
  const moduleActivities = training?.current_module_activities || [];
  const requiredActivities = moduleActivities.filter((item) => item.is_required);
  const optionalActivities = moduleActivities.filter((item) => !item.is_required);
  const statChips = [
    { label: "Total XP", value: stats.total_xp || 0, to: "/skills", Icon: Zap },
    { label: "Day Streak", value: stats.streak || 0, to: "/skills", Icon: Flame },
    { label: "Quizzes Done", value: stats.quizzes_completed || 0, to: "/quizzes", Icon: Trophy },
    { label: "Tickets Passed", value: stats.service_desk_completed || 0, to: "/service-desk", Icon: Ticket },
  ];
  const activeTicket = serviceDeskSummary?.active_attempt;
  const recentFeedback = serviceDeskSummary?.recent_mentor_feedback;
  const needsPractice = serviceDeskSummary?.needs_practice || [];
  const hasFollowUpWidgets = Boolean(activeTicket || activeLab || recentFeedback);

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <PageHeader title={stats.name || "Dashboard"} subtitle="Your next lesson, quiz, or ticket, picked for you." />

      <section className="rounded-2xl bg-gradient-to-br from-blue-700 to-indigo-700 p-5 text-white shadow-lg sm:p-7">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-200">Learning Path</p>
        <h2 className="mt-2 text-2xl font-bold sm:text-3xl">{continueTarget.title}</h2>
        <p className="mt-2 text-blue-100">{continueTarget.detail}</p>
        {training?.next_activity ? (
          <div className="mt-4 flex flex-col gap-3 rounded-xl border border-white/20 bg-blue-950/20 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="text-xs font-bold uppercase tracking-wide text-blue-200">Next up</p>
              <p className="mt-1 truncate font-semibold text-white">{training.next_activity.activity_label} — {training.next_activity.title}</p>
              {training.next_activity.estimated_minutes ? <p className="mt-1 inline-flex items-center gap-1 text-xs text-blue-100"><Clock3 size={13} />About {training.next_activity.estimated_minutes} min</p> : null}
            </div>
            <ArrowRight className="hidden shrink-0 text-blue-200 sm:block" size={20} aria-hidden="true" />
          </div>
        ) : null}
        {training?.current_module ? <div className="mt-4 max-w-2xl"><div className="mb-1 flex justify-between text-sm"><span>{training.current_module.required_complete} of {training.current_module.required_total} required activities complete</span><strong>{training.current_module.completion_percent}%</strong></div><div className="h-2.5 overflow-hidden rounded-full bg-blue-950/40"><div className="h-full rounded-full bg-white" style={{ width: `${training.current_module.completion_percent}%` }} /></div></div> : null}
        <Link className="mt-5 inline-flex min-h-11 items-center justify-center rounded-xl bg-white px-5 py-3 font-bold text-blue-700 hover:bg-blue-50" to={continueTarget.to}>{continueTarget.label}</Link>
      </section>

      {training?.current_module ? (
        <section className="panel space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">Current Module</p><h2 className="mt-1 text-xl font-semibold text-slate-900 dark:text-white">{training.current_module.title}</h2><p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{training.current_stage?.title}</p></div>
            <Link className="text-sm font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400" to={training.current_module.route}>Open module</Link>
          </div>
          <ol className="divide-y divide-slate-200 dark:divide-slate-700">
            {requiredActivities.map((item) => {
              const isNext = item.id === training.next_activity?.id;
              return <li className={`flex items-center gap-3 py-2.5 ${isNext ? "font-semibold text-blue-700 dark:text-blue-300" : "text-slate-700 dark:text-slate-300"}`} key={item.id}>{item.complete ? <CheckCircle2 className="shrink-0 text-emerald-500" size={18} /> : isNext ? <ArrowRight className="shrink-0 text-blue-600" size={18} /> : <Circle className="shrink-0 text-slate-300 dark:text-slate-600" size={18} />}<span className="min-w-0 flex-1 truncate">{item.title}</span><span className="shrink-0 text-xs font-medium text-slate-500">{isNext ? "Next" : item.complete ? "Done" : "Upcoming"}</span></li>;
            })}
          </ol>
          {optionalActivities.length ? <p className="rounded-lg bg-violet-50 px-3 py-2 text-sm text-violet-800 dark:bg-violet-950/30 dark:text-violet-200"><strong>Optional practice:</strong> {optionalActivities.length} item{optionalActivities.length === 1 ? "" : "s"}. These do not block your next module.</p> : null}
        </section>
      ) : null}

      {hasFollowUpWidgets ? (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {activeTicket ? (
            <a href="/service-desk" className="panel flex flex-col gap-2 p-4 hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md dark:hover:border-blue-700">
              <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-violet-700 dark:text-violet-300"><Ticket size={14} aria-hidden="true" />Active Ticket</span>
              <p className="font-semibold text-slate-900 dark:text-slate-100">{activeTicket.scenario_title}</p>
              <span className="mt-auto text-sm font-medium text-blue-600 dark:text-blue-400">Resume in Tickets</span>
            </a>
          ) : null}
          {activeLab ? (
            <Link to={`/labs/${activeLab.id}`} className="panel flex flex-col gap-2 p-4 hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md dark:hover:border-blue-700">
              <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-blue-700 dark:text-blue-300"><FlaskConical size={14} aria-hidden="true" />Active Lab</span>
              <p className="font-semibold text-slate-900 dark:text-slate-100">{activeLab.title}</p>
              <span className="mt-auto text-sm font-medium text-blue-600 dark:text-blue-400">Resume lab</span>
            </Link>
          ) : null}
          {recentFeedback ? (
            <div className="panel flex flex-col gap-2 p-4">
              <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-emerald-700 dark:text-emerald-300"><MessageSquare size={14} aria-hidden="true" />Mentor Feedback</span>
              <p className="font-semibold text-slate-900 dark:text-slate-100">{recentFeedback.scenario_title}</p>
              <p className="line-clamp-3 text-sm text-slate-600 dark:text-slate-300">{recentFeedback.feedback}</p>
            </div>
          ) : null}
        </section>
      ) : null}

      {needsPractice.length ? (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/20">
          <h2 className="font-semibold text-amber-900 dark:text-amber-200">Could use more practice</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-800 dark:text-amber-300">
            {needsPractice.slice(0, 3).map((title) => <li key={title}>{title}</li>)}
          </ul>
        </section>
      ) : null}

      <section aria-label="Your stats" className="flex flex-wrap gap-3">
        {statChips.map(({ label, value, to, Icon }) => {
          const chipClassName = "group flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3.5 py-2 text-sm hover:border-blue-300 hover:shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:hover:border-blue-700";
          const chipContent = (
            <>
              <Icon className="text-slate-400 group-hover:text-blue-600 dark:text-slate-500 dark:group-hover:text-blue-400" size={iconSizes.inline} aria-hidden="true" />
              <span className="font-semibold text-slate-900 dark:text-slate-100">{value}</span>
              <span className="text-slate-500 dark:text-slate-400">{label}</span>
            </>
          );
          return to === "/service-desk" ? (
            <a key={label} href={to} className={chipClassName}>{chipContent}</a>
          ) : (
            <Link key={label} to={to} className={chipClassName}>{chipContent}</Link>
          );
        })}
      </section>

      <section className="space-y-3">
        <div className="flex items-center gap-3">
          <span className="rounded-lg bg-blue-100 p-2 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
            <Brain size={iconSizes.heading} aria-hidden="true" />
          </span>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Daily Review</h2>
        </div>
        <div className="panel">
          <FlashcardReviewPanel />
        </div>
      </section>

      <section className="panel space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Recent Activity</h2>
          <Link className="text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300" to="/skills">View skills</Link>
        </div>
        {recent.length ? recent.map((item, index) => {
          const Icon = item.type === "service_desk" ? Ticket : BookOpen;
          const scorePct = item.score != null ? item.score : null;
          return (
            <div key={`${item.type}-${index}`} className="flex items-start justify-between gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
              <div className="flex min-w-0 items-start gap-3">
                <span className="mt-0.5 rounded-lg bg-slate-100 p-2 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  <Icon size={iconSizes.inline} aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <p className="truncate font-medium text-slate-900 dark:text-slate-100">{item.title || "Activity"}</p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{item.timestamp ? new Date(item.timestamp).toLocaleString() : "Recent update"}</p>
                </div>
              </div>
              {item.score != null ? (
                <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${scoreBand.classes[scoreBand(scorePct)]}`}>Score {item.score}%</span>
              ) : item.xp != null ? (
                <div className="shrink-0"><XPBadge amount={item.xp} /></div>
              ) : null}
            </div>
          );
        }) : <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">No recent submissions yet.</p>}
      </section>
    </main>
  );
}
