import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";

import ActivityAccessError from "../components/ActivityAccessError";
import BackLink from "../components/BackLink";
import OrientationPracticePanel from "../components/OrientationPracticePanel";
import TicketNoteExercise from "../components/TicketNoteExercise";
import { getCurrentStudent } from "../hooks/useAuth";
import {
  completeLesson,
  getLesson,
  getLessonNote,
  saveLessonNote,
} from "../services/api";
import { activityOrigin, withActivityOrigin } from "../utils/activityOrigin";

const NOTE_SAVE_DELAY_MS = 800;

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
        code: ({ children }) => (
          <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-sm text-slate-900 dark:bg-slate-800 dark:text-slate-100">
            {children}
          </code>
        ),
        h2: ({ children }) => (
          <h3 className="border-t border-slate-200 pt-4 text-lg font-bold text-slate-950 first:border-0 first:pt-0 dark:border-slate-700 dark:text-white">
            {children}
          </h3>
        ),
        li: ({ children }) => <li className="pl-1">{children}</li>,
        ol: ({ children }) => (
          <ol className="list-decimal space-y-2 pl-6">{children}</ol>
        ),
        p: ({ children }) => <p className="max-w-3xl">{children}</p>,
        ul: ({ children }) => (
          <ul className="list-disc space-y-2 pl-6">{children}</ul>
        ),
      }}
    >
      {lessonSummaryMarkdown(summary)}
    </ReactMarkdown>
  );
}

function relatedActivityCtaLabel(activityType) {
  return activityType === "networking_lab"
    ? "Start guided practice"
    : "Start related activity";
}

function noteDraftKey(lessonId) {
  const studentId = getCurrentStudent()?.id || "unknown";
  return `nexus:lesson-note-draft:${studentId}:${lessonId}`;
}

function readDraft(key) {
  try {
    const value = JSON.parse(localStorage.getItem(key));
    return typeof value?.content === "string" ? value : null;
  } catch {
    return null;
  }
}

export function LessonNotes({ lessonId, onSaved, orientation, registerFlush }) {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saveState, setSaveState] = useState("saved");
  const contentRef = useRef("");
  const confirmedRef = useRef("");
  const dirtyRef = useRef(false);
  const inFlightRef = useRef(null);
  const timerRef = useRef(null);
  const mountedRef = useRef(true);
  const draftKey = noteDraftKey(lessonId);

  const persistLatest = useCallback(async () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (inFlightRef.current) {
      await inFlightRef.current;
      if (dirtyRef.current) return persistLatest();
      return true;
    }
    const pendingContent = contentRef.current;
    if (!dirtyRef.current || pendingContent === confirmedRef.current) {
      dirtyRef.current = false;
      if (mountedRef.current) setSaveState("saved");
      return true;
    }
    dirtyRef.current = false;
    if (mountedRef.current) setSaveState("saving");
    const request = saveLessonNote(
      lessonId,
      pendingContent,
      confirmedRef.current,
      { suppressToast: true },
    )
      .then((response) => {
        confirmedRef.current = pendingContent;
        if (contentRef.current === pendingContent) {
          localStorage.removeItem(draftKey);
          if (mountedRef.current) setSaveState("saved");
        } else {
          dirtyRef.current = true;
        }
        onSaved?.();
        return true;
      })
      .catch(() => {
        dirtyRef.current = true;
        if (mountedRef.current) setSaveState("error");
        return false;
      })
      .finally(() => {
        inFlightRef.current = null;
      });
    inFlightRef.current = request;
    const saved = await request;
    if (saved && dirtyRef.current) return persistLatest();
    return saved;
  }, [draftKey, lessonId, onSaved]);

  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;
    const draft = readDraft(draftKey);
    setLoading(true);
    getLessonNote(lessonId, { suppressToast: true })
      .then((response) => {
        if (cancelled) return;
        const serverContent = response.data?.content || "";
        confirmedRef.current = serverContent;
        const restored = draft?.content ?? serverContent;
        contentRef.current = restored;
        setContent(restored);
        dirtyRef.current = Boolean(draft && draft.content !== serverContent);
        setSaveState(dirtyRef.current ? "error" : "saved");
        if (draft && draft.content === serverContent)
          localStorage.removeItem(draftKey);
      })
      .catch(() => {
        if (cancelled) return;
        const restored = draft?.content || "";
        contentRef.current = restored;
        setContent(restored);
        dirtyRef.current = Boolean(draft);
        setSaveState("error");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [draftKey, lessonId]);

  useEffect(() => {
    registerFlush?.(persistLatest);
    return () => registerFlush?.(null);
  }, [persistLatest, registerFlush]);

  useEffect(() => {
    if (loading || !dirtyRef.current || saveState === "error") return undefined;
    timerRef.current = setTimeout(() => {
      void persistLatest();
    }, NOTE_SAVE_DELAY_MS);
    return () => clearTimeout(timerRef.current);
  }, [content, loading, persistLatest, saveState]);

  useEffect(() => {
    const flushBeforeUnload = () => {
      void persistLatest();
    };
    window.addEventListener("pagehide", flushBeforeUnload);
    return () => {
      mountedRef.current = false;
      window.removeEventListener("pagehide", flushBeforeUnload);
      void persistLatest();
    };
  }, [persistLatest]);

  const stateCopy =
    saveState === "saving"
      ? "Saving…"
      : saveState === "error"
        ? "Couldn’t save"
        : "Saved";
  return (
    <section className="panel">
      <h2 className="text-xl font-bold">Optional notes</h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
        Notes are a study aid and never count as lesson completion or mastery. A
        local draft is kept until your account copy is confirmed.
      </p>
      <textarea
        aria-label="Lesson notes"
        className="input-field mt-3 w-full"
        disabled={loading}
        onChange={(event) => {
          const nextContent = event.target.value;
          contentRef.current = nextContent;
          dirtyRef.current = true;
          localStorage.setItem(
            draftKey,
            JSON.stringify({ content: nextContent }),
          );
          setSaveState("saving");
          setContent(nextContent);
        }}
        placeholder={
          orientation
            ? "Optional: note where you will look when you are unsure what comes next."
            : "Optional notes for this lesson..."
        }
        rows={5}
        value={content}
      />
      <div className="mt-2 flex min-h-6 items-center gap-3" aria-live="polite">
        <p
          className={`text-sm font-medium ${saveState === "error" ? "text-red-700 dark:text-red-300" : "text-slate-600 dark:text-slate-300"}`}
        >
          {stateCopy}
        </p>
        {saveState === "error" ? (
          <button
            className="text-sm font-semibold text-blue-700 underline dark:text-blue-300"
            onClick={() => {
              setSaveState("saving");
              void persistLatest();
            }}
            type="button"
          >
            Try again
          </button>
        ) : null}
      </div>
    </section>
  );
}

function WorkedExample({ example }) {
  const rows = [
    ["Symptom", example.symptom],
    ["Technician checks", example.check],
    ["Observation", example.observation],
    ["This suggests", example.suggests],
    ["This does not prove", example.does_not_prove],
    ["Next check", example.next_check],
  ];
  return (
    <section className="panel">
      <h2 className="text-xl font-bold">Worked example</h2>
      <dl className="mt-4 grid gap-4">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs font-bold uppercase tracking-wider text-blue-700 dark:text-blue-300">
              {label}
            </dt>
            <dd className="mt-1 text-slate-700 dark:text-slate-300">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export default function LessonPage() {
  const { lessonId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [lesson, setLesson] = useState(null);
  const [error, setError] = useState(null);
  const [completionError, setCompletionError] = useState(false);
  const [orientationRefresh, setOrientationRefresh] = useState(0);
  const [completing, setCompleting] = useState(false);
  const noteFlushRef = useRef(null);
  const registerNoteFlush = useCallback((flush) => {
    noteFlushRef.current = flush;
  }, []);
  const flushNotes = useCallback(async () => noteFlushRef.current?.(), []);

  useEffect(() => {
    let cancelled = false;
    setLesson(null);
    setError(null);
    getLesson(lessonId, { suppressToast: true })
      .then((response) => {
        if (!cancelled) setLesson(response.data);
      })
      .catch((requestError) => {
        if (!cancelled) setError(requestError);
      });
    return () => {
      cancelled = true;
    };
  }, [lessonId]);

  if (error)
    return (
      <main className="mx-auto max-w-3xl p-6">
        <BackLink fallbackLabel="My Course" fallbackTo="/learning-path" />
        <ActivityAccessError
          error={error}
          kind="Lesson"
          onRetry={() => window.location.reload()}
        />
      </main>
    );
  if (!lesson)
    return (
      <main className="mx-auto max-w-4xl p-6">
        <div className="h-64 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" />
      </main>
    );

  async function markComplete() {
    setCompleting(true);
    setCompletionError(false);
    try {
      await completeLesson(lesson.id, { suppressToast: true });
      setLesson((current) => ({ ...current, is_complete: true }));
      setOrientationRefresh((value) => value + 1);
    } catch {
      setCompletionError(true);
    } finally {
      setCompleting(false);
    }
  }

  async function navigateAfterFlush(event, route) {
    event.preventDefault();
    await flushNotes();
    navigate(route);
  }

  const presentation = lesson.presentation || {};
  const readiness = presentation.readiness?.length
    ? presentation.readiness
    : lesson.outcomes;
  const embedUrl = getYouTubeEmbedUrl(lesson.video_url);
  const origin = activityOrigin(location);
  const rawRelatedActivityRoute =
    lesson.related_activity_stable_id && lesson.related_training_module_id
      ? `/training/module/${lesson.related_training_module_id}?activity=${encodeURIComponent(lesson.related_activity_stable_id)}`
      : null;
  const relatedActivityRoute = withActivityOrigin(
    rawRelatedActivityRoute,
    origin?.route,
    origin?.label,
  );
  const nextActivityRoute = withActivityOrigin(
    lesson.next_activity?.route,
    origin?.route,
    origin?.label,
  );
  return (
    <main className="mx-auto max-w-4xl space-y-6 overflow-x-hidden p-4 pb-20 sm:p-6">
      <BackLink
        beforeNavigate={flushNotes}
        fallbackLabel="My Course"
        fallbackTo="/learning-path"
      />
      <header className="panel">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">
          {lesson.is_orientation ? "Welcome to Nexus" : "A+ Foundations"}
        </p>
        <h1 className="mt-2 break-words text-3xl font-bold">
          {lesson.is_orientation ? "Welcome to Nexus" : lesson.title}
        </h1>
      </header>
      {Array.isArray(lesson.outcomes) && lesson.outcomes.length > 0 ? (
        <section className="panel" data-testid="lesson-objectives">
          <h2 className="text-xl font-bold">What you’ll learn</h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            By the end of this lesson, you should be able to:
          </p>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-700 dark:text-slate-300">
            {lesson.outcomes.map((outcome, index) => (
              <li className="break-words" key={`${index}-${outcome}`}>
                {outcome}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {presentation.workplace_purpose ? (
        <section className="panel">
          <h2 className="text-xl font-bold">Why this matters</h2>
          <p className="mt-3 text-slate-700 dark:text-slate-300">
            {presentation.workplace_purpose}
          </p>
        </section>
      ) : null}
      {presentation.mental_model?.length ? (
        <section className="panel">
          <h2 className="text-xl font-bold">Core idea / mental model</h2>
          <ol className="mt-4 flex flex-col gap-2 text-sm font-semibold text-slate-800 dark:text-slate-100 sm:flex-row sm:flex-wrap sm:items-center">
            {presentation.mental_model.map((item, index) => (
              <li className="flex min-w-0 items-center gap-2" key={item}>
                <span className="min-w-0 rounded-lg bg-blue-50 px-3 py-2 dark:bg-blue-950/50">
                  {item}
                </span>
                {index < presentation.mental_model.length - 1 ? (
                  <span aria-hidden="true" className="text-blue-600">
                    →
                  </span>
                ) : null}
              </li>
            ))}
          </ol>
        </section>
      ) : null}
      {lesson.summary ? (
        <section className="panel" data-testid="lesson-body">
          <h2 className="text-xl font-bold">Core lesson</h2>
          {lesson.is_orientation ? (
            <ReactMarkdown className="mt-4 space-y-3 leading-7 text-slate-700 dark:text-slate-300">
              {lesson.summary}
            </ReactMarkdown>
          ) : (
            <LessonSummary summary={lesson.summary} />
          )}
        </section>
      ) : null}
      {embedUrl ? (
        <section className="aspect-video overflow-hidden rounded-xl bg-black">
          <iframe
            src={embedUrl}
            className="h-full w-full"
            allowFullScreen
            title={lesson.title}
          />
        </section>
      ) : null}
      {presentation.worked_example ? (
        <WorkedExample example={presentation.worked_example} />
      ) : null}
      {presentation.evidence_guidance ? (
        <section className="panel">
          <h2 className="text-xl font-bold">What the evidence means</h2>
          <p className="mt-3 text-slate-700 dark:text-slate-300">
            {presentation.evidence_guidance}
          </p>
        </section>
      ) : null}
      {presentation.understanding_prompt || relatedActivityRoute ? (
        <section className="panel">
          <h2 className="text-xl font-bold">
            Quick understanding prompt / next practice
          </h2>
          {presentation.understanding_prompt ? (
            <p className="mt-3 text-slate-700 dark:text-slate-300">
              {presentation.understanding_prompt}
            </p>
          ) : null}
          {relatedActivityRoute ? (
            <Link
              className="btn-primary mt-4 inline-flex"
              onClick={(event) =>
                navigateAfterFlush(event, relatedActivityRoute)
              }
              to={relatedActivityRoute}
            >
              {relatedActivityCtaLabel(lesson.related_activity_type)}
            </Link>
          ) : null}
        </section>
      ) : null}
      {lesson.title === "Anatomy of a Good Ticket" ? (
        <TicketNoteExercise />
      ) : null}
      {!lesson.is_orientation ? (
        <section className="panel" data-testid="completion-readiness">
          <h2 className="text-xl font-bold">Ready to finish this lesson?</h2>
          {readiness?.length ? (
            <>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                You should now be able to:
              </p>
              <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-700 dark:text-slate-300">
                {readiness.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </>
          ) : (
            <p className="mt-2 text-slate-700 dark:text-slate-300">
              Review the lesson’s main idea and identify the next safe check you
              would make.
            </p>
          )}
          <p className="mt-4 text-sm text-slate-600 dark:text-slate-300">
            This records that you finished the lesson. Quizzes and practical
            work provide separate evidence of understanding.
          </p>
          <button
            className="btn-primary mt-4"
            disabled={lesson.is_complete || completing}
            onClick={markComplete}
            type="button"
          >
            {lesson.is_complete
              ? "Lesson complete"
              : completing
                ? "Saving…"
                : "Mark lesson complete"}
          </button>
          {completionError ? (
            <div
              className="mt-4 rounded-lg border border-red-300 bg-red-50 p-3 text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100"
              role="alert"
            >
              <p className="font-semibold">
                We couldn’t save your lesson completion.
              </p>
              <button
                className="mt-2 font-semibold underline"
                onClick={markComplete}
                type="button"
              >
                Try again
              </button>
            </div>
          ) : null}
        </section>
      ) : null}
      {lesson.is_orientation ? (
        <OrientationPracticePanel
          completing={completing}
          onMarkComplete={markComplete}
          refreshKey={orientationRefresh}
        />
      ) : null}
      {lesson.is_complete ? (
        <section className="panel" aria-live="polite">
          <h2 className="text-xl font-bold">Lesson completion saved.</h2>
          {lesson.next_activity ? (
            <>
              <p className="mt-2 text-sm font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-300">
                Next activity
              </p>
              <Link
                className="btn-primary mt-3 inline-flex"
                onClick={(event) =>
                  navigateAfterFlush(event, nextActivityRoute)
                }
                to={nextActivityRoute}
              >
                {lesson.next_activity.title}
              </Link>
            </>
          ) : (
            <BackLink
              beforeNavigate={flushNotes}
              className="btn-primary mt-3 inline-flex"
              fallbackLabel="Continue in My Course"
              fallbackTo="/learning-path"
            />
          )}
        </section>
      ) : null}
      <LessonNotes
        lessonId={lesson.id}
        orientation={lesson.is_orientation}
        registerFlush={registerNoteFlush}
      />
    </main>
  );
}
