import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle, ChevronDown, ChevronUp, Circle, Lock } from "lucide-react";

import { getLearningPath } from "../services/api";
import { getSelectedProfile } from "../services/profile";

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
            <div className="mb-4 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/20 dark:text-amber-300">
              <p className="font-semibold">Unlock requirements</p>
              <ul className="ml-4 list-disc">
                {module.unlock_requirements.map((req, idx) => (
                  <li key={idx}>{req}</li>
                ))}
              </ul>
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
  const studentId = getSelectedProfile()?.id || 1;
  const [modules, setModules] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const run = async () => {
      setLoading(true);
      const res = await getLearningPath(studentId);
      setModules(res.modules || []);
      setLoading(false);
    };
    run();
  }, [studentId]);

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <h1 className="text-3xl font-bold">Your Learning Path</h1>
      <div className="space-y-6">
        {loading
          ? [1, 2, 3].map((id) => <SkeletonCard key={id} />)
          : modules.map((module) => <ModuleCard key={module.id} module={module} />)}
      </div>
    </main>
  );
}
