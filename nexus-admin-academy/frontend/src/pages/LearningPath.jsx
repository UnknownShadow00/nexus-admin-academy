import { useEffect, useState } from "react";
import { CheckCircle, Circle, Lock } from "lucide-react";
import { getLearningPath } from "../services/api";
import { getSelectedProfile } from "../services/profile";

function LessonRow({ lesson, moduleUnlocked }) {
  return (
    <div className="flex items-center justify-between rounded border bg-white p-3 dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-center gap-3">
        {lesson.completion_percent === 100 ? (
          <CheckCircle className="text-green-600" size={20} />
        ) : moduleUnlocked ? (
          <Circle className="text-blue-600" size={20} />
        ) : (
          <Lock className="text-slate-400" size={20} />
        )}
        <span className="font-medium">{lesson.title}</span>
      </div>
      <div className="w-24">
        <div className="mb-1 text-xs">{lesson.completion_percent}%</div>
        <div className="h-2 w-full rounded-full bg-slate-200 dark:bg-slate-700">
          <div className="h-2 rounded-full bg-blue-600" style={{ width: `${lesson.completion_percent}%` }} />
        </div>
      </div>
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
            <div className="mb-4 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
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

  useEffect(() => {
    const run = async () => {
      const res = await getLearningPath(studentId);
      setModules(res.modules || []);
    };
    run();
  }, [studentId]);

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <h1 className="text-3xl font-bold">Your Learning Path</h1>
      <div className="space-y-6">
        {modules.map((module) => (
          <ModuleCard key={module.id} module={module} />
        ))}
      </div>
    </main>
  );
}

