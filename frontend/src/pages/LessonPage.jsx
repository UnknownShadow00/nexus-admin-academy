import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";

import { getCurrentStudent } from "../hooks/useAuth";
import BackLink from "../components/BackLink";
import LessonNotes from "../components/LessonNotes";
import OrientationPracticePanel from "../components/OrientationPracticePanel";
import TicketNoteExercise from "../components/TicketNoteExercise";
import { completeLesson, getLesson } from "../services/api";

function getYouTubeEmbedUrl(url) {
  if (!url) return null;
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/);
  return match ? `https://www.youtube.com/embed/${match[1]}` : null;
}

function lessonSummaryMarkdown(summary) {
  return String(summary || "")
    .split(/\n\s*\n/)
    .map((block) => {
      const lines = block.trim().split("\n");
      const heading = lines[0]?.match(/^([A-Z][A-Z0-9 &'’/(),-]{2,}):\s*(.*)$/);
      if (!heading) return block.trim();
      const rest = [heading[2], ...lines.slice(1)].filter(Boolean).join("\n");
      return `## ${heading[1]}${rest ? `\n${rest}` : ""}`;
    })
    .join("\n\n");
}

function LessonSummary({ summary }) {
  return (
    <ReactMarkdown
      className="mt-4 space-y-4 leading-7 text-slate-700 dark:text-slate-300"
      components={{
        code: ({ children }) => <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-sm text-slate-900 dark:bg-slate-800 dark:text-slate-100">{children}</code>,
        h2: ({ children }) => <h2 className="border-t border-slate-200 pt-4 text-lg font-bold text-slate-950 first:border-0 first:pt-0 dark:border-slate-700 dark:text-white">{children}</h2>,
        li: ({ children }) => <li className="pl-1">{children}</li>,
        ol: ({ children }) => <ol className="list-decimal space-y-2 pl-6">{children}</ol>,
        p: ({ children }) => <p className="max-w-3xl">{children}</p>,
        ul: ({ children }) => <ul className="list-disc space-y-2 pl-6">{children}</ul>,
      }}
    >
      {lessonSummaryMarkdown(summary)}
    </ReactMarkdown>
  );
}

function relatedActivityCtaLabel(activityType) {
  if (activityType === "networking_lab") return "Start CLI Practice";
  return "Start related activity";
}

export default function LessonPage() {
  const { lessonId } = useParams();
  return <LessonContent key={`${getCurrentStudent()?.id}:${lessonId}`} />;
}

function LessonContent() {
  const { lessonId } = useParams();
  const [lesson, setLesson] = useState(null);
  const [error, setError] = useState(null);
  const [orientationRefresh, setOrientationRefresh] = useState(0);
  const [completing, setCompleting] = useState(false);
  const [completionError, setCompletionError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLesson(null);
    setError(null);
    setCompletionError("");
    getLesson(lessonId, { suppressToast: true })
      .then((response) => { if (!cancelled) setLesson(response.data); })
      .catch((requestError) => {
        if (!cancelled) {
          const locked = requestError?.response?.status === 403;
          setError({
            locked,
            message: locked ? requestError?.userMessage || "Complete the current module's required work first." : "This lesson could not be loaded.",
            nextRoute: requestError?.response?.data?.data?.next_action_route || "/learning-path",
            requiredModuleTitle: requestError?.response?.data?.data?.required_module_title,
          });
        }
      });
    return () => { cancelled = true; };
  }, [lessonId, retry]);

  if (error) return <main className="mx-auto max-w-3xl p-6"><BackLink className="mb-4 inline-flex items-center gap-1 text-blue-600" fallbackLabel="Learning Path" fallbackTo="/learning-path" /><div className="panel" role="alert"><h1 className="text-xl font-bold">{error.locked ? error.requiredModuleTitle ? `${error.requiredModuleTitle} locked` : "Lesson locked" : "Lesson unavailable"}</h1><p className="mt-2 text-slate-700 dark:text-slate-300">{error.message}</p>{error.locked ? <Link className="btn-primary mt-4" to={error.nextRoute}>Complete remaining work</Link> : <button className="btn-primary mt-4" onClick={() => setRetry((value) => value + 1)} type="button">Retry lesson</button>}</div></main>;
  if (!lesson) return <main className="mx-auto max-w-4xl p-6"><div className="h-64 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" /></main>;

  async function markComplete() {
    if (completing) return;
    setCompletionError("");
    setCompleting(true);
    try {
      await completeLesson(lesson.id, { suppressToast: true });
      setLesson((current) => ({ ...current, is_complete: true }));
      setOrientationRefresh((value) => value + 1);
    } catch {
      setCompletionError("Lesson completion could not be saved. Please try Mark lesson complete again.");
    } finally {
      setCompleting(false);
    }
  }

  const embedUrl = getYouTubeEmbedUrl(lesson.video_url);
  const relatedActivityRoute = lesson.related_activity_stable_id && lesson.related_training_module_id
    ? `/training/module/${lesson.related_training_module_id}?activity=${encodeURIComponent(lesson.related_activity_stable_id)}`
    : null;
  return (
    <main className="mx-auto max-w-4xl space-y-6 p-4 pb-20 sm:p-6">
      <BackLink fallbackLabel="Learning Path" fallbackTo="/learning-path" />
      <header className="panel">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">{lesson.is_orientation ? "Welcome to Nexus" : lesson.module_code}</p>
        <h1 className="mt-2 text-3xl font-bold">{lesson.is_orientation ? "Welcome to Nexus" : lesson.title}</h1>
        {lesson.summary ? lesson.is_orientation ? (
          <ReactMarkdown
            className="mt-4 space-y-3 leading-7 text-slate-700 dark:text-slate-300"
            components={{
              ol: ({ children }) => <ol className="list-decimal space-y-1 pl-6">{children}</ol>,
              ul: ({ children }) => <ul className="grid gap-1 pl-1 sm:grid-cols-2">{children}</ul>,
              li: ({ children }) => <li className="ml-4">{children}</li>,
              p: ({ children }) => <p>{children}</p>,
            }}
          >{lesson.summary}</ReactMarkdown>
        ) : <LessonSummary summary={lesson.summary} /> : null}
      </header>
      {lesson.is_orientation ? <section className="panel space-y-3">
        <h2 className="text-xl font-bold">Before your first quiz: what goes in a ticket?</h2>
        <p>A ticket is the shared record of a support request. Imagine Maya says, “I cannot sign in to my work laptop.”</p>
        <ul className="list-disc space-y-2 pl-5">
          <li><strong>Intake:</strong> record who needs help, which device they use, and what happened. Ask for the exact error before choosing a fix.</li>
          <li><strong>Category:</strong> group similar problems, such as account access. Consistent categories help the team spot recurring issues in reports.</li>
          <li><strong>Progress notes:</strong> record each check and its result: “Confirmed the error and checked the account status.” These help the next technician continue your work.</li>
          <li><strong>Escalation:</strong> first-line support (L1) handles initial checks. If the fix needs specialist access or expertise, pass the evidence to second-line support (L2).</li>
          <li><strong>Resolution summary:</strong> when the problem is solved, record the fix and how you confirmed it worked. This is different from the running progress notes.</li>
        </ul>
        <p className="text-sm text-slate-600 dark:text-slate-300">Remember: identify the user, device, and problem; document what you tried; involve the right person. The quiz below checks these ideas. You can retry it and review explanations.</p>
      </section> : null}
      {Array.isArray(lesson.outcomes) && lesson.outcomes.length > 0 ? (
        <section className="panel">
          <h2 className="text-xl font-bold">In this lesson, you'll learn</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-700 dark:text-slate-300">
            {lesson.outcomes.map((outcome, index) => <li className="break-words" key={`${index}-${outcome}`}>{outcome}</li>)}
          </ul>
        </section>
      ) : null}
      {embedUrl ? <section className="aspect-video overflow-hidden rounded-xl bg-black"><iframe src={embedUrl} className="h-full w-full" allowFullScreen title={lesson.title} /></section> : null}
      {lesson.title === "Anatomy of a Good Ticket" ? <TicketNoteExercise /> : null}
      {relatedActivityRoute ? <section className="panel flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">Put this lesson into practice</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Continue with the related activity in this module.</p>
        </div>
        <Link className="btn-primary" to={relatedActivityRoute}>{relatedActivityCtaLabel(lesson.related_activity_type)}</Link>
      </section> : null}
      {!lesson.is_orientation ? <section className="panel flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">Ready to move on?</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Mark this lesson complete after reviewing the material above.</p>
        </div>
        <button className="btn-primary" disabled={lesson.is_complete || completing} onClick={markComplete} type="button">
          {lesson.is_complete ? "Lesson complete" : completing ? "Saving…" : "Mark lesson complete"}
        </button>
      </section> : null}
      {completionError ? <p className="panel" role="alert">{completionError}</p> : null}
      {lesson.is_orientation ? <OrientationPracticePanel completing={completing} onMarkComplete={markComplete} refreshKey={orientationRefresh} /> : null}
      <LessonNotes lessonId={lesson.id} orientation={lesson.is_orientation} />
    </main>
  );
}
