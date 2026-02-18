import { useEffect, useState } from "react";
import { createLesson, createModule, getLessons, getModules } from "../services/api";

export default function ModuleManager() {
  const [modules, setModules] = useState([]);
  const [selectedModule, setSelectedModule] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [moduleForm, setModuleForm] = useState({ code: "", title: "", module_order: 1, unlock_threshold: 70 });
  const [lessonForm, setLessonForm] = useState({ title: "", lesson_order: 1, summary: "" });

  const loadModules = async () => {
    const res = await getModules();
    setModules(res.data || []);
  };

  useEffect(() => {
    loadModules();
  }, []);

  useEffect(() => {
    const run = async () => {
      if (!selectedModule) return;
      const res = await getLessons(selectedModule.id);
      setLessons(res.data || []);
    };
    run();
  }, [selectedModule]);

  return (
    <main className="mx-auto grid max-w-7xl gap-6 p-6 lg:grid-cols-2">
      <section className="panel dark:border-slate-700 dark:bg-slate-900">
        <h1 className="mb-3 text-2xl font-bold">Module Manager</h1>
        <div className="space-y-2">
          <input className="input-field" placeholder="Code (MOD-101)" value={moduleForm.code} onChange={(e) => setModuleForm({ ...moduleForm, code: e.target.value })} />
          <input className="input-field" placeholder="Title" value={moduleForm.title} onChange={(e) => setModuleForm({ ...moduleForm, title: e.target.value })} />
          <div className="grid grid-cols-2 gap-2">
            <input className="input-field" type="number" placeholder="Order" value={moduleForm.module_order} onChange={(e) => setModuleForm({ ...moduleForm, module_order: Number(e.target.value || 1) })} />
            <input className="input-field" type="number" placeholder="Unlock %" value={moduleForm.unlock_threshold} onChange={(e) => setModuleForm({ ...moduleForm, unlock_threshold: Number(e.target.value || 70) })} />
          </div>
          <button
            className="btn-primary"
            onClick={async () => {
              await createModule(moduleForm);
              await loadModules();
            }}
          >
            Create Module
          </button>
        </div>
        <div className="mt-4 space-y-2">
          {modules.map((m) => (
            <button key={m.id} className={`w-full rounded border p-3 text-left ${selectedModule?.id === m.id ? "border-blue-400 bg-blue-50 dark:bg-slate-800" : "border-slate-200 dark:border-slate-700"}`} onClick={() => setSelectedModule(m)}>
              <p className="font-semibold">{m.code} - {m.title}</p>
              <p className="text-xs text-slate-500">Order {m.module_order} - Unlock {m.unlock_threshold}%</p>
            </button>
          ))}
        </div>
      </section>

      <section className="panel dark:border-slate-700 dark:bg-slate-900">
        <h2 className="mb-3 text-xl font-bold">Lessons</h2>
        {!selectedModule ? <p className="text-sm text-slate-500">Select a module.</p> : null}
        {selectedModule ? (
          <>
            <div className="space-y-2">
              <input className="input-field" placeholder="Lesson title" value={lessonForm.title} onChange={(e) => setLessonForm({ ...lessonForm, title: e.target.value })} />
              <input className="input-field" type="number" placeholder="Lesson order" value={lessonForm.lesson_order} onChange={(e) => setLessonForm({ ...lessonForm, lesson_order: Number(e.target.value || 1) })} />
              <textarea className="input-field" placeholder="Summary" value={lessonForm.summary} onChange={(e) => setLessonForm({ ...lessonForm, summary: e.target.value })} />
              <button
                className="btn-primary"
                onClick={async () => {
                  await createLesson({ ...lessonForm, module_id: selectedModule.id, outcomes: [] });
                  const res = await getLessons(selectedModule.id);
                  setLessons(res.data || []);
                }}
              >
                Add Lesson
              </button>
            </div>
            <div className="mt-4 space-y-2">
              {lessons.map((l) => (
                <div key={l.id} className="rounded border border-slate-200 p-3 dark:border-slate-700">
                  <p className="font-medium">{l.lesson_order}. {l.title}</p>
                  <p className="text-sm text-slate-500">{l.summary}</p>
                </div>
              ))}
            </div>
          </>
        ) : null}
      </section>
    </main>
  );
}

