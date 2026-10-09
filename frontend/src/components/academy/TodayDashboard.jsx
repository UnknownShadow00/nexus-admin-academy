import { ArrowRight, BookOpen, CheckCircle2, Circle, Flame, Headphones, Lock, Monitor, ClipboardCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { stageSequenceItems } from "../v2/V2StageSequence";
import V2Status from "../v2/V2Status";
import { practicalDisplayStatus, stageProgressStatus } from "../ui/statusFoundation";
import { TrainingDestination } from "../TrainingDestination";
import AcademyScene from "./AcademyScene";

const DONE = new Set(["completed", "passed", "approved", "done"]);
const number = value => typeof value === "number" && Number.isFinite(value) && value >= 0;
const percent = (done, total) => number(done) && number(total) && total > 0 ? Math.min(100, Math.round(done / total * 100)) : null;

// These are counts of distinct evidence, never a client-computed mastery score.
export function todayProgress(current, training) {
  const p = current?.progress;
  if (!p) {
    const module = training?.current_module;
    return { percent: number(module?.completion_percent) ? module.completion_percent : null, label: "Required work", rows: number(module?.required_total) && number(module?.required_complete) ? [{ label: "Required", value: `${module.required_complete}/${module.required_total}`, color: "blue" }] : [] };
  }
  const rows = [];
  if (number(p.lessons?.total) && number(p.lessons?.completed)) rows.push({ label: "Lessons", value: `${p.lessons.completed}/${p.lessons.total}`, color: "blue" });
  if (number(p.quick_checks?.total) && number(p.quick_checks?.completed)) rows.push({ label: "Quick Checks", value: `${p.quick_checks.completed}/${p.quick_checks.total}`, color: "purple" });
  if (p.module_quiz) rows.push({ label: "Checkpoint", value: p.module_quiz.activity?.passed ? "Passed" : "Not passed", color: "purple" });
  if (p.service_desk) rows.push({ label: "Practiced", value: p.service_desk.activity?.passed ? "Passed" : "Not passed", color: "cyan" });
  if (p.practical) {
    const status = practicalDisplayStatus(p.practical.activity, current.certification?.version?.key === "nexus_beginner_aplus_v1");
    rows.push({ label: "Practical", value: status === "approved" || status === "passed" ? "Approved" : status === "awaiting_mentor_review" ? "With mentor" : status === "needs_correction" ? "Changes requested" : "Not approved", color: "mute" });
  }
  const grouped = number(p.groups?.total) && p.groups.total > 0;
  return { percent: grouped ? percent(p.groups.completed, p.groups.total) : percent(p.lessons?.completed, p.lessons?.total), label: grouped ? "Lesson groups" : "Lessons", rows };
}

export function todayActivities(detail, training) {
  if (detail?.module && detail?.certification) return stageSequenceItems(detail)
    .filter(item => item.kind !== "resource")
    .map(item => ({ ...item, complete: DONE.has(item.status) }));
  return (training?.current_module_activities || []).map(item => ({ key: item.stable_id || item.id, kind: item.activity_type, type: item.activity_label, title: item.title, route: item.destination_route, available: !item.broken_reference && item.status !== "locked" && Boolean(item.destination_route), complete: Boolean(item.complete), status: item.status, estimatedMinutes: item.estimated_minutes, activity: item }));
}

const ProgressBar = ({ value, label }) => value === null ? null : <div className="progress-line"><div className="bar" role="progressbar" aria-label={label} aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${value}%`, background: "var(--purple)" }} /></div><small>{value}%</small></div>;

function LearningPath({ current, learning, training }) {
  const path = learning ? (learning.modules || []).map(item => ({ key: item.module.key, title: item.module.title, route: `/learning-v2/modules/${item.module.key}`, locked: item.locked, reason: item.lock_reason, complete: item.progress?.module_complete, current: item.module.key === current?.module?.key }))
    : (training?.stages || []).map(item => ({ key: item.stable_id, title: item.title, route: item.modules?.find(m => !m.locked)?.route, locked: item.locked, reason: item.modules?.find(m => m.lock_reason)?.lock_reason, complete: item.is_complete, current: item.stable_id === training.current_stage?.stable_id }));
  if (!path.length) return null;
  return <section className="card path-card" aria-labelledby="learning-path-heading"><div className="section-title"><h2 id="learning-path-heading">Your learning path</h2><span className="small muted">{path.length} {learning ? "stages" : "learning stages"}</span></div><ol className="path">{path.map((item, i) => {
    const content = <><span className="stage-number">{item.locked ? <Lock size={13} aria-hidden="true" /> : item.complete ? <CheckCircle2 size={16} aria-hidden="true" /> : i + 1}</span><span><strong>{item.title}</strong><small>{item.locked ? "Locked" : item.complete ? learning ? "Mastered" : "Complete" : item.current ? "Current stage" : "Available"}</small></span></>;
    return <li key={item.key}>{item.locked || !item.route ? <div className="stage" aria-disabled="true" title={item.reason}>{content}</div> : <Link className={`stage ${item.current ? "current" : ""}`} to={item.route} aria-current={item.current ? "step" : undefined}>{content}</Link>}</li>;
  })}</ol></section>;
}

export default function TodayDashboard({ model, training, learning, detail, detailState, reloadDetail, stats, dark, MentorFollowUp }) {
  const { target, followUps, correction, mode } = model;
  const current = learning?.current;
  const progress = todayProgress(current, training);
  const activities = todayActivities(detail, learning ? null : training);
  const work = mode === "learning" ? activities.filter(item => item.available && item.route && !item.complete && !["needs_review", "awaiting_mentor_review", "needs_correction"].includes(item.status)) : [];
  const upNext = work.filter(item => item.route !== target.to).slice(0, 4);
  const courseRoute = learning ? "/learning-v2" : "/learning-path";
  const primaryTitle = mode === "learning" ? target.title : mode === "correction" ? correction?.title || target.title : mode === "waiting" ? "Learning is up to date" : mode === "mastered" ? current?.module?.title || target.title : mode === "legacy_complete" ? target.title : "Nothing else to do here yet";
  const description = mode === "learning" ? (target.activityType || "Course work") + " is ready when you are."
    : mode === "correction" ? "Your mentor left feedback on this practical. This is a normal part of the process."
      : mode === "waiting" ? "You've finished the learning currently available here. Your practical is with your mentor."
        : mode === "mastered" ? "This stage is mastered. You can review your work in My Course."
          : mode === "legacy_complete" ? target.detail : current ? "Check My Course for the learning currently available to you." : "Open your learning path to see what is available.";
  const primaryLink = mode === "learning" ? { label: target.label, to: target.to } : mode === "correction" ? { label: "Update your practical", to: correction?.route } : mode === "mastered" ? { label: "View My Course", to: "/learning-v2" } : mode === "legacy_complete" ? { label: target.label, to: target.to } : { label: learning ? "View My Course" : "View course", to: courseRoute };
  const secondaryFollowUps = mode === "correction" ? followUps.filter(item => item.key !== correction?.key) : followUps;
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
  const name = stats.name?.trim().split(/\s+/)[0];
  const nextLesson = detail?.lessons?.find(lesson => target.to?.endsWith(`/lessons/${lesson.key}`));
  return <main className="today-dashboard">
    <section className="hero" aria-label="Your next learning step"><AcademyScene kind="hero" dark={dark} />
      <div className="hero-quote"><p>{dark ? "“A stronger tomorrow is built in the shadows.”" : "“A stronger you, for a bigger tomorrow.”"}</p><small>— NEXUS ACADEMY</small></div>
      <div className="hero-content"><span className="hero-stage">{current?.module?.title || training?.current_module?.title || training?.current_stage?.title || "Your learning path"}</span><h1>Good {greeting}{name ? `, ${name}` : ""}</h1><p className="hero-tagline">Small steps. Real skills. A stronger you.</p><p>{mode === "learning" ? `Your next step: ${target.title}. Keep building your skills at your own pace.` : mode === "correction" ? "Your mentor has feedback ready. Review the changes and take your next step." : mode === "mastered" || mode === "legacy_complete" ? "Take a moment to see how far you've come. Your completed work is ready to revisit." : "See your current learning and follow-ups below."}</p><div className="actions"><a className="btn btn-primary" href="#continue-learning">View next step</a><Link className="btn btn-glass" to={courseRoute}>View learning path</Link></div></div>
    </section>
    <div className="dashboard-top">
      <section className="card continue" aria-labelledby="today-primary-heading" id="continue-learning"><div className="section-title"><h2>{mode === "correction" ? "Changes requested" : mode === "mastered" ? "Stage mastered" : mode === "legacy_complete" ? "Your training" : "Continue learning"}</h2><Link to={courseRoute}>View course</Link></div>
        <div className="continue-card"><div className="lesson-thumb"><AcademyScene kind="thumbnail" dark={dark} /></div><div className="continue-copy"><span className="small muted">{target.activityType || current?.certification?.name || target.detail}</span><h2 id="today-primary-heading">{primaryTitle}</h2><p className="small sub">{description}</p>
          {mode === "correction" && correction?.feedback ? <p className="today-feedback"><strong>Mentor feedback:</strong> {correction.feedback}</p> : null}
          {mode === "correction" && correction?.stage ? <p className="small muted">{correction.stage}</p> : null}
          <ProgressBar value={progress.percent} label={`${progress.label} completion`} />
          <div className="section-title">{target.estimatedMinutes || nextLesson?.estimated_minutes ? <span className="small muted">About {target.estimatedMinutes || nextLesson.estimated_minutes} min</span> : null}{primaryLink?.to ? <TrainingDestination activity={target.v2 ? null : training?.next_activity} to={primaryLink.to} className={`btn ${mode === "learning" || mode === "correction" ? "btn-primary" : "btn-secondary"}`}>{primaryLink.label}<ArrowRight size={16} aria-hidden="true" /></TrainingDestination> : null}</div>
        </div></div>
      </section>
      <section className="card progress-summary" aria-labelledby="today-progress-heading" id="progress"><div className="section-title"><h2 id="today-progress-heading">Your progress</h2>{current ? <V2Status status={stageProgressStatus(current.progress)} /> : null}</div><div className="progress-details">
        {progress.percent !== null ? <div className="progress-ring"><svg viewBox="0 0 112 112" width="112" height="112" aria-hidden="true"><circle cx="56" cy="56" r="46" fill="none" stroke="var(--line)" strokeWidth="10" /><circle cx="56" cy="56" r="46" fill="none" stroke="var(--blue)" strokeWidth="10" strokeLinecap="round" opacity={progress.percent ? 1 : 0} strokeDasharray={`${progress.percent * 2.89} 289`} transform="rotate(-90 56 56)" /></svg><div><strong>{progress.percent}%</strong><small>{progress.label}</small></div></div> : null}
        <ul>{progress.rows.map(row => <li key={row.label}><i style={{ background: `var(--${row.color})` }} /><span>{row.label}</span><b className="mono">{row.value}</b></li>)}</ul>
      </div><p className="small muted">{progress.rows.length ? "Lessons, checks and practicals are counted separately." : "Your course record will appear as learning becomes available."}</p></section>
      <section className="card task-card" aria-labelledby="today-work-plan-heading"><div className="section-title"><h2 id="today-work-plan-heading">Your work plan</h2><Link to={courseRoute}>View all</Link></div>
        {detailState === "error" ? <><p className="small sub" role="alert">Your work plan could not be loaded.</p><button type="button" className="btn btn-secondary" onClick={reloadDetail}>Retry work plan</button></> : detailState === "loading" ? <p className="small muted" role="status">Loading your work plan…</p> : work.length ? <ul className="today-work-plan">{work.slice(0, 4).map(item => <li key={item.key}><Circle size={17} aria-hidden="true" /><span><TrainingDestination activity={item.activity} to={item.route}>{item.title}</TrainingDestination><span className="small">{item.type}</span></span></li>)}</ul> : <p className="small sub">{mode === "mastered" || mode === "legacy_complete" ? "Your available work is complete." : "Open your course for current requirements."}</p>}
        <p className="small task-xp">Learn at your own pace.</p>
      </section>
    </div>
    <div className="dashboard-middle">
      {upNext.length ? <section className="card" aria-labelledby="today-up-next-heading"><h2 id="today-up-next-heading">Up next{current?.module?.title ? ` in ${current.module.title}` : " in your learning path"}</h2><div className="up-grid">{upNext.map((item, i) => {
        const Icon = item.kind === "service_desk" ? Headphones : item.kind === "module_quiz" || item.kind === "quick_check" ? ClipboardCheck : item.kind === "practical" ? Monitor : BookOpen;
        return <TrainingDestination key={item.key} activity={item.activity} to={item.route} className="up"><span className={`tile ${["blue", "cyan", "violet", "green"][i]}`}><Icon size={20} aria-hidden="true" /></span><strong>{item.title}</strong><span className="sub">{item.type}</span><small className="muted">{item.estimatedMinutes ? `About ${item.estimatedMinutes} min` : "Available in your course"}</small></TrainingDestination>;
      })}</div></section>  : mode !== "correction" || secondaryFollowUps.length ? <MentorFollowUp items={secondaryFollowUps} learningAvailable={mode === "learning"} /> : <section className="card"><h2>Your next step</h2><p className="small sub">Review your mentor’s feedback, then update the practical above.</p></section>}
      <div className="stack">{number(stats.streak) ? <section className="card streak" aria-labelledby="today-streak-heading"><h2 id="today-streak-heading">Streak</h2><div className="streak-line"><div className="streak-count"><Flame size={34} aria-hidden="true" /><div><strong>{stats.streak}</strong><small>{stats.streak === 1 ? "day" : "days"}</small></div></div>{number(stats.longest_streak) ? <p className="streak-longest">Longest streak<br /><strong>{stats.longest_streak} {stats.longest_streak === 1 ? "day" : "days"}</strong></p> : null}</div></section> : null}<section className="quote"><AcademyScene kind="quote" dark={dark} /><div className="quote-content"><p>“Progress isn’t always seen. Sometimes it’s just you showing up anyway.”</p></div></section></div>
    </div>
    {upNext.length && secondaryFollowUps.length ? <MentorFollowUp items={secondaryFollowUps} learningAvailable={mode === "learning"} /> : null}
    <LearningPath current={current} learning={learning} training={training} />
    {current ? <footer className="small sub">Your full stage record is in <Link to="/learning-v2">My Course</Link>. Want more practice? <Link to="/learning-path">Open Extra Practice</Link>.</footer> : null}
  </main>;
}
