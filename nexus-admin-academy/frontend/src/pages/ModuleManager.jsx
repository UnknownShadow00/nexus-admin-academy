import { useEffect, useState } from "react";
import { createAdminCommand, createLesson, createModule, deleteAdminCommand, getAdminCommands, getLessons, getModules } from "../services/api";

export default function ModuleManager() {
  const [modules, setModules] = useState([]);
  const [selectedModule, setSelectedModule] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [moduleForm, setModuleForm] = useState({ code: "", title: "", module_order: 1, unlock_threshold: 70 });
  const [lessonForm, setLessonForm] = useState({ title: "", lesson_order: 1, summary: "" });
  const [commands, setCommands] = useState([]);
  const [commandForm, setCommandForm] = useState({ command: "", syntax: "", description: "", category: "Windows", example: "" });

  const loadModules = async () => {
    const res = await getModules();
    setModules(res.data || []);
  };

  useEffect(() => {
    loadModules();
    const loadCommands = async () => {
      const res = await getAdminCommands();
      setCommands(res.data || []);
    };
    loadCommands();
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

      <section className="panel lg:col-span-2 dark:border-slate-700 dark:bg-slate-900">
        <h2 className="mb-3 text-xl font-bold">Command Library</h2>
        <div className="grid gap-2 md:grid-cols-5">
          <input className="input-field" placeholder="Command" value={commandForm.command} onChange={(e) => setCommandForm({ ...commandForm, command: e.target.value })} />
          <input className="input-field" placeholder="Syntax" value={commandForm.syntax} onChange={(e) => setCommandForm({ ...commandForm, syntax: e.target.value })} />
          <input className="input-field md:col-span-2" placeholder="Description" value={commandForm.description} onChange={(e) => setCommandForm({ ...commandForm, description: e.target.value })} />
          <input className="input-field" placeholder="Category" value={commandForm.category} onChange={(e) => setCommandForm({ ...commandForm, category: e.target.value })} />
        </div>
        <textarea className="input-field mt-2" placeholder="Example" value={commandForm.example} onChange={(e) => setCommandForm({ ...commandForm, example: e.target.value })} />
        <button
          className="btn-primary mt-2"
          onClick={async () => {
            await createAdminCommand(commandForm);
            const res = await getAdminCommands();
            setCommands(res.data || []);
          }}
        >
          Add Command
        </button>
        <div className="mt-3 max-h-72 space-y-2 overflow-auto">
          {commands.map((c) => (
            <div key={c.id} className="flex items-center justify-between rounded border border-slate-200 p-2 text-sm dark:border-slate-700">
              <div>
                <p className="font-mono font-semibold">{c.command}</p>
                <p className="text-xs text-slate-500">{c.category}</p>
              </div>
              <button
                className="btn-secondary"
                onClick={async () => {
                  await deleteAdminCommand(c.id);
                  setCommands((prev) => prev.filter((x) => x.id !== c.id));
                }}
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
