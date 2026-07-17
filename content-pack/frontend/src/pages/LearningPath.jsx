import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle, ChevronDown, ChevronUp, Circle, Lock } from "lucide-react";

import { getCurrentStudent } from "../hooks/useAuth";
import { getLearningPath, getLessonNote, saveLessonNote } from "../services/api";
import Banner from "../components/ui/Banner";
import PageHeader from "../components/ui/PageHeader";

function getYouTubeEmbedUrl(url) {
  if (!url) return null;
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/);
  return match ? `https://www.youtube.com/embed/${match[1]}` : null;
}

function SkeletonCard() {
  return (
    <div className="panel animate-pulse dark:border-slate-700 dark:bg-slate-900">
      <div className="h-5 w-2/3 rounded bg-slate-200 dark:bg-slate-700" />
      <div className="mt-3 h-3 w-full rounded bg-slate-100 dark:bg-slate-800" />
      <div className="mt-2 h-3 w-4/5 rounded bg-slate-100 dark:bg-slate-800" />
      <div className="mt-4 h-9 w-full rounded bg-slate-200 dark:bg-slate-700" />
    </div>
  );
}

function LessonNotes({ lessonId }) {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);
  const editedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    editedRef.current = false;
    getLessonNote(lessonId, { suppressToast: true })
      .then((res) => {
        if (!cancelled) setContent(res.data?.content || "");
      })
      .catch(() => {
        if (!cancelled) setContent("");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [lessonId]);

  useEffect(() => {
    if (loading || !editedRef.current) return;
    const timer = setTimeout(async () => {
      try {
        await saveLessonNote(lessonId, content, { suppressToast: true });
        editedRef.current = false;
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      } catch {
        editedRef.current = true;
      }
    }, 1500);
    return () => clearTimeout(timer);
  }, [content, lessonId, loading]);

  return (
    <div className="space-y-2">
      <textarea
        className="input-field w-full"
        disabled={loading}
        onChange={(event) => {
          editedRef.current = true;
          setContent(event.target.value);
        }}
        placeholder="Your notes for this lesson..."
        rows={4}
        value={content}
      />
      <p className={`text-sm font-medium transition-opacity ${saved ? "text-emerald-600 opacity-100 dark:text-emerald-300" : "opacity-0"}`}>
        Saved
      </p>
    </div>
  );
}

function LessonRow({ lesson, moduleUnlocked }) {
  const [expanded, setExpanded] = useState(false);
  const embedUrl = getYouTubeEmbedUrl(lesson.video_url);

  return (
    <div
      className={`rounded-lg border transition-all ${
        lesson.completion_percent === 100
          ? "border-green-300 bg-green-50 dark:border-green-800 dark:bg-green-950/20"
          : moduleUnlocked
            ? "border-slate-200 bg-white hover:border-blue-300 dark:border-slate-700 dark:bg-slate-800"
            : "border-slate-200 bg-slate-50 opacity-60 dark:border-slate-800 dark:bg-slate-900"
      }`}
    >
      <button
        className="flex w-full items-center justify-between p-4 text-left disabled:cursor-not-allowed"
        disabled={!moduleUnlocked}
        onClick={() => moduleUnlocked && setExpanded((v) => !v)}
      >
        <div className="flex items-center gap-3">
          {lesson.completion_percent === 100 ? (
            <CheckCircle className="shrink-0 text-green-600" size={20} />
          ) : moduleUnlocked ? (
            <Circle className="shrink-0 text-blue-500" size={20} />
          ) : (
            <Lock className="shrink-0 text-slate-400" size={20} />
          )}
          <div>
            <p className="font-semibold text-slate-900 dark:text-slate-100">{lesson.title}</p>
            {lesson.summary ? <p className="text-sm text-slate-500 dark:text-slate-400">{lesson.summary}</p> : null}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <div className="w-16 text-right">
            <p className="text-xs text-slate-500">{lesson.completion_percent}%</p>
            <div className="mt-1 h-1.5 rounded-full bg-slate-200 dark:bg-slate-700">
              <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${lesson.completion_percent}%` }} />
            </div>
          </div>
          {moduleUnlocked ? (
            expanded ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />
          ) : null}
        </div>
      </button>

      {expanded ? (
        <div className="space-y-4 border-t border-slate-200 p-4 dark:border-slate-700">
          {embedUrl ? (
            <div className="aspect-video w-full overflow-hidden rounded-lg bg-black">
              <iframe src={embedUrl} className="h-full w-full" allowFullScreen title={lesson.title} />
            </div>
          ) : (
            <div className="rounded-lg border-2 border-dashed border-slate-200 p-6 text-center dark:border-slate-700">
              <p className="text-sm text-slate-400">No video yet - admin can add a YouTube URL in Module Manager.</p>
            </div>
          )}
          <LessonNotes lessonId={lesson.id} />
          <div className="flex gap-2">
            <Link to="/quizzes" className="btn-primary text-sm">Take Quizzes →</Link>
            <Link to="/tickets" className="btn-secondary text-sm">Practice Tickets →</Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ModuleCard({ module }) {
  const borderClass = module.mastery_percent === 100 ? "border-green-500 bg-green-50 dark:bg-green-950/20" : module.unlocked ? "border-blue-500 bg-blue-50 dark:bg-blue-950/20" : "border-slate-300 bg-slate-50 dark:bg-slate-900";

  const Icon = module.mastery_percent === 100 ? CheckCircle : module.unlocked ? Circle : Lock;
  const iconClass = module.mastery_percent === 100 ? "text-green-600" : module.unlocked ? "text-blue-600" : "text-slate-400";

  return (
    <div className={`rounded-lg border-l-4 p-6 ${borderClass}`}>
      <div className="flex items-start gap-4">
        <Icon className={iconClass} size={30} />
        <div className="flex-1">
          <div className="mb-2 flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-500">{module.code}</div>
              <h3 className="text-2xl font-bold">{module.title}</h3>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-blue-600">{module.mastery_percent}%</div>
              <div className="text-xs text-slate-500">Mastery</div>
            </div>
          </div>
          {!module.unlocked && module.unlock_requirements?.length > 0 ? (
            <div className="mb-4">
              <Banner variant="warning">
                <span className="font-semibold">Unlock requirements: </span>
                {module.unlock_requirements.join(" · ")}
              </Banner>
            </div>
          ) : null}
          <div className="space-y-2">
            {(module.lessons || []).map((lesson) => (
              <LessonRow key={lesson.id} lesson={lesson} moduleUnlocked={module.unlocked} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LearningPath() {
  const studentId = getCurrentStudent()?.id;
  const [modules, setModules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError("");
      try {
        const res = await getLearningPath(studentId, { suppressToast: true });
        if (!cancelled) setModules(res.modules || []);
      } catch (err) {
        if (!cancelled) {
          setModules([]);
          setError(err?.userMessage || "Unable to load your learning path.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [studentId]);

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <PageHeader title="Your Learning Path" />
      <div className="space-y-6">
        {loading
          ? [1, 2, 3].map((id) => <SkeletonCard key={id} />)
          : error
            ? <div className="panel text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">{error}</div>
          : modules.map((module) => <ModuleCard key={module.id} module={module} />)}
      </div>
    </main>
  );
}
