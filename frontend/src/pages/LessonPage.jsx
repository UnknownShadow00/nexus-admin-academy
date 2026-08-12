import { ChevronLeft } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";

import OrientationPracticePanel from "../components/OrientationPracticePanel";
import { completeLesson, getLesson, getLessonNote, saveLessonNote } from "../services/api";

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

function LessonNotes({ lessonId, onSaved, orientation }) {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);
  const editedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    editedRef.current = false;
    getLessonNote(lessonId, { suppressToast: true })
      .then((response) => { if (!cancelled) setContent(response.data?.content || ""); })
      .catch(() => { if (!cancelled) setContent(""); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [lessonId]);

  useEffect(() => {
    if (loading || !editedRef.current) return;
    const timer = setTimeout(async () => {
      try {
        await saveLessonNote(lessonId, content, { suppressToast: true });
        editedRef.current = false;
        setSaved(true);
        onSaved?.();
        setTimeout(() => setSaved(false), 2000);
      } catch {
        editedRef.current = true;
      }
    }, 1500);
    return () => clearTimeout(timer);
  }, [content, lessonId, loading, onSaved]);

  return (
    <section className="panel">
      <h2 className="text-xl font-bold">Optional notes</h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Notes are a study aid and never affect lesson completion. They save automatically to your account.</p>
      <textarea
        className="input-field mt-3 w-full"
        disabled={loading}
        onChange={(event) => {
          editedRef.current = true;
          setContent(event.target.value);
        }}
        placeholder={orientation ? "Optional: note where you will look when you are unsure what comes next." : "Optional notes for this lesson..."}
        rows={5}
        value={content}
      />
      <p className={`mt-2 text-sm font-medium text-emerald-600 transition-opacity dark:text-emerald-300 ${saved ? "opacity-100" : "opacity-0"}`}>Saved</p>
    </section>
  );
}

export default function LessonPage() {
  const { lessonId } = useParams();
  const [lesson, setLesson] = useState(null);
  const [error, setError] = useState(null);
  const [orientationRefresh, setOrientationRefresh] = useState(0);
  const [completing, setCompleting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLesson(null);
    setError(null);
    getLesson(lessonId, { suppressToast: true })
      .then((response) => { if (!cancelled) setLesson(response.data); })
      .catch((requestError) => {
        if (!cancelled) {
          const locked = requestError?.response?.status === 403;
          setError({
            message: locked ? requestError?.userMessage || "Complete the previous week's required work first." : "This lesson could not be loaded.",
            nextRoute: requestError?.response?.data?.data?.next_action_route || "/training",
            requiredWeek: requestError?.response?.data?.data?.required_week,
          });
        }
      });
    return () => { cancelled = true; };
  }, [lessonId]);

  if (error) return <main className="mx-auto max-w-3xl p-6"><Link className="mb-4 inline-flex items-center gap-1 text-blue-600" to="/training"><ChevronLeft size={16} />My Training</Link><div className="panel" role="alert"><h1 className="text-xl font-bold">{error.requiredWeek ? `Week ${error.requiredWeek} locked` : "Lesson locked"}</h1><p className="mt-2 text-slate-700 dark:text-slate-300">{error.message}</p><Link className="btn-primary mt-4" to={error.nextRoute}>Complete remaining work</Link></div></main>;
  if (!lesson) return <main className="mx-auto max-w-4xl p-6"><div className="h-64 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" /></main>;

  async function markComplete() {
    setCompleting(true);
    try {
      await completeLesson(lesson.id, { suppressToast: true });
      setLesson((current) => ({ ...current, is_complete: true }));
      setOrientationRefresh((value) => value + 1);
    } finally {
      setCompleting(false);
    }
  }

  const embedUrl = getYouTubeEmbedUrl(lesson.video_url);
  return (
    <main className="mx-auto max-w-4xl space-y-6 p-4 pb-20 sm:p-6">
      <Link className="inline-flex items-center gap-1 text-sm font-semibold text-blue-600" to="/training"><ChevronLeft size={16} />My Training</Link>
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
      {Array.isArray(lesson.outcomes) && lesson.outcomes.length > 0 ? (
        <section className="panel">
          <h2 className="text-xl font-bold">In this lesson, you'll learn</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-700 dark:text-slate-300">
            {lesson.outcomes.map((outcome, index) => <li className="break-words" key={`${index}-${outcome}`}>{outcome}</li>)}
          </ul>
        </section>
      ) : null}
      {embedUrl ? <section className="aspect-video overflow-hidden rounded-xl bg-black"><iframe src={embedUrl} className="h-full w-full" allowFullScreen title={lesson.title} /></section> : null}
      {!lesson.is_orientation ? <section className="panel flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">Ready to move on?</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Mark this lesson complete after reviewing the material above.</p>
        </div>
        <button className="btn-primary" disabled={lesson.is_complete || completing} onClick={markComplete} type="button">
          {lesson.is_complete ? "Lesson complete" : completing ? "Saving…" : "Mark lesson complete"}
        </button>
      </section> : null}
      {lesson.is_orientation ? <OrientationPracticePanel completing={completing} onMarkComplete={markComplete} refreshKey={orientationRefresh} /> : null}
      <LessonNotes lessonId={lesson.id} orientation={lesson.is_orientation} />
    </main>
  );
}
