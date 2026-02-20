import { useEffect, useState } from "react";
import Papa from "papaparse";
import {
  createAdminCommand,
  createLesson,
  createModule,
  deleteAdminCommand,
  deleteQuiz,
  generateQuiz,
  getAdminCommands,
  getLessons,
  getModules,
  getQuizList,
  scrapeQuizPreview,
  scrapeQuizSave,
} from "../services/api";

const QUESTION_OPTIONS = [5, 10, 15, 20];

export default function ModuleManager() {
  const [modules, setModules] = useState([]);
  const [selectedModule, setSelectedModule] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [moduleForm, setModuleForm] = useState({ code: "", title: "", module_order: 1, unlock_threshold: 70 });
  const [lessonForm, setLessonForm] = useState({ title: "", lesson_order: 1, summary: "", video_url: "" });
  const [commands, setCommands] = useState([]);
  const [commandForm, setCommandForm] = useState({ command: "", syntax: "", description: "", category: "Windows", example: "" });

  const [builderTab, setBuilderTab] = useState("ai");

  const [quizForm, setQuizForm] = useState({
    title: "",
    question_count: 10,
    module_id: "",
    lesson_id: "",
    week_number: 1,
    domain_id: "1.0",
    urls: [""],
  });
  const [quizLessons, setQuizLessons] = useState([]);
  const [quizLoading, setQuizLoading] = useState(false);
  const [quizSuccess, setQuizSuccess] = useState("");
  const [quizError, setQuizError] = useState("");

  const [scrapeUrl, setScrapeUrl] = useState("");
  const [scrapeLoading, setScrapeLoading] = useState(false);
  const [scrapeError, setScrapeError] = useState("");
  const [scrapeData, setScrapeData] = useState(null);
  const [scrapeWeek, setScrapeWeek] = useState(1);
  const [scrapeLessonId, setScrapeLessonId] = useState("");

  const [csvError, setCsvError] = useState("");
  const [csvPreview, setCsvPreview] = useState(null);
  const [csvWeek, setCsvWeek] = useState(1);
  const [csvLessonId, setCsvLessonId] = useState("");
  const [csvSaving, setCsvSaving] = useState(false);

  const [recentQuizzes, setRecentQuizzes] = useState([]);
  const lessonOptions = quizLessons.length ? quizLessons : lessons;

  const loadModules = async () => {
    const res = await getModules();
    setModules(res.data || []);
  };

  const loadRecentQuizzes = async () => {
    const res = await getQuizList();
    setRecentQuizzes((res.data || []).slice(0, 10));
  };

  useEffect(() => {
    loadModules();
    loadRecentQuizzes();
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

  useEffect(() => {
    const run = async () => {
      const moduleId = Number(quizForm.module_id || 0);
      if (!moduleId) {
        setQuizLessons([]);
        return;
      }
      const res = await getLessons(moduleId);
      const rows = res.data || [];
      setQuizLessons(rows);
      if (!rows.some((x) => String(x.id) === String(quizForm.lesson_id))) {
        setQuizForm((prev) => ({ ...prev, lesson_id: "" }));
      }
    };
    run();
  }, [quizForm.module_id]);

  const setQuizUrl = (index, value) => {
    setQuizForm((prev) => {
      const urls = [...prev.urls];
      urls[index] = value;
      return { ...prev, urls };
    });
  };

  const addQuizUrl = () => {
    setQuizForm((prev) => (prev.urls.length >= 5 ? prev : { ...prev, urls: [...prev.urls, ""] }));
  };

  const removeQuizUrl = (index) => {
    setQuizForm((prev) => ({ ...prev, urls: prev.urls.filter((_, i) => i !== index) }));
  };

  const resetQuizForm = () => {
    setQuizForm({
      title: "",
      question_count: 10,
      module_id: "",
      lesson_id: "",
      week_number: 1,
      domain_id: "1.0",
      urls: [""],
    });
  };

  const handleGenerateQuiz = async () => {
    setQuizSuccess("");
    setQuizError("");
    const sourceUrls = quizForm.urls.map((url) => url.trim()).filter(Boolean);
    if (!quizForm.title.trim()) {
      setQuizError("Quiz title is required");
      return;
    }
    if (sourceUrls.length < 1 || sourceUrls.length > 5) {
      setQuizError("Provide between 1 and 5 YouTube URLs");
      return;
    }

    setQuizLoading(true);
    try {
      await generateQuiz({
        title: quizForm.title.trim(),
        source_urls: sourceUrls,
        question_count: Number(quizForm.question_count),
        week_number: Number(quizForm.week_number || 1),
        domain_id: quizForm.domain_id || "1.0",
        lesson_id: quizForm.lesson_id ? Number(quizForm.lesson_id) : null,
      });
      setQuizSuccess(`Quiz created with ${Number(quizForm.question_count)} questions`);
      resetQuizForm();
      await loadRecentQuizzes();
    } catch (error) {
      const detail = error?.response?.data?.detail;
      setQuizError(typeof detail === "string" ? detail : "Failed to generate quiz");
    } finally {
      setQuizLoading(false);
    }
  };

  const onScrapePreview = async () => {
    setScrapeError("");
    setScrapeData(null);
    if (!scrapeUrl.trim()) {
      setScrapeError("URL is required");
      return;
    }

    setScrapeLoading(true);
    try {
      const res = await scrapeQuizPreview(scrapeUrl.trim());
      setScrapeData(res.data || null);
    } catch (error) {
      const detail = error?.response?.data?.detail;
      setScrapeError(typeof detail === "string" ? detail : "Preview failed");
    } finally {
      setScrapeLoading(false);
    }
  };

  const onScrapeSave = async () => {
    if (!scrapeData?.questions?.length) return;
    await scrapeQuizSave({
      title: scrapeData.title,
      source_url: scrapeData.source_url,
      week_number: Number(scrapeWeek || 1),
      lesson_id: scrapeLessonId ? Number(scrapeLessonId) : null,
      domain_id: "1.0",
      questions: scrapeData.questions,
    });
    setScrapeData(null);
    setScrapeUrl("");
    await loadRecentQuizzes();
  };

  const handleCsvUpload = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setCsvError("");
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const questions = (results.data || [])
          .map((row) => ({
            question_text: row.question || row.question_text || "",
            option_a: row.option_a || row.a || "",
            option_b: row.option_b || row.b || "",
            option_c: row.option_c || row.c || "",
            option_d: row.option_d || row.d || "",
            correct_answer: (row.correct_answer || row.correct || "A").toUpperCase(),
            explanation: row.explanation || "",
          }))
          .filter((q) => q.question_text && q.option_a);
        setCsvPreview({ questions, title: file.name.replace(/\.csv$/i, "") });
      },
      error: (err) => setCsvError(err.message),
    });
  };

  const downloadTemplate = () => {
    const header = "question,option_a,option_b,option_c,option_d,correct_answer,explanation";
    const example = "What does DNS stand for?,Domain Name System,Dynamic Network Service,Data Node Selector,Direct Name Service,A,DNS translates domain names to IP addresses";
    const blob = new Blob([`${header}\n${example}`], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "quiz-template.csv";
    a.click();
  };

  const onCsvSave = async () => {
    if (!csvPreview?.questions?.length) return;
    setCsvSaving(true);
    try {
      await scrapeQuizSave({
        title: csvPreview.title || "CSV Imported Quiz",
        source_url: "csv_import",
        week_number: Number(csvWeek || 1),
        lesson_id: csvLessonId ? Number(csvLessonId) : null,
        domain_id: "1.0",
        questions: csvPreview.questions,
      });
      setCsvPreview(null);
      await loadRecentQuizzes();
    } finally {
      setCsvSaving(false);
    }
  };

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
          <button className="btn-primary" onClick={async () => { await createModule(moduleForm); await loadModules(); }}>Create Module</button>
        </div>
        <div className="mt-4 space-y-2">
          {modules.map((moduleItem) => (
            <button key={moduleItem.id} className={`w-full rounded border p-3 text-left ${selectedModule?.id === moduleItem.id ? "border-blue-400 bg-blue-50 dark:bg-slate-800" : "border-slate-200 dark:border-slate-700"}`} onClick={() => setSelectedModule(moduleItem)}>
              <p className="font-semibold">{moduleItem.code} - {moduleItem.title}</p>
              <p className="text-xs text-slate-500">Order {moduleItem.module_order} - Unlock {moduleItem.unlock_threshold}%</p>
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
              <input className="input-field" placeholder="YouTube video URL (optional)" value={lessonForm.video_url || ""} onChange={(e) => setLessonForm({ ...lessonForm, video_url: e.target.value })} />
              <button className="btn-primary" onClick={async () => { await createLesson({ ...lessonForm, module_id: selectedModule.id, outcomes: [] }); const res = await getLessons(selectedModule.id); setLessons(res.data || []); }}>
                Add Lesson
              </button>
            </div>
            <div className="mt-4 space-y-2">
              {lessons.map((lesson) => (
                <div key={lesson.id} className="rounded border border-slate-200 p-3 dark:border-slate-700">
                  <p className="font-medium">{lesson.lesson_order}. {lesson.title}</p>
                  <p className="text-sm text-slate-500">{lesson.summary}</p>
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
        <button className="btn-primary mt-2" onClick={async () => { await createAdminCommand(commandForm); const res = await getAdminCommands(); setCommands(res.data || []); }}>
          Add Command
        </button>
        <div className="mt-3 max-h-72 space-y-2 overflow-auto">
          {commands.map((command) => (
            <div key={command.id} className="flex items-center justify-between rounded border border-slate-200 p-2 text-sm dark:border-slate-700">
              <div>
                <p className="font-mono font-semibold">{command.command}</p>
                <p className="text-xs text-slate-500">{command.category}</p>
              </div>
              <button className="btn-secondary" onClick={async () => { await deleteAdminCommand(command.id); setCommands((prev) => prev.filter((item) => item.id !== command.id)); }}>
                Delete
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="panel lg:col-span-2 space-y-4 dark:border-slate-700 dark:bg-slate-900">
        <h2 className="text-xl font-bold">Quiz Builder</h2>

        <div className="flex gap-2 border-b border-slate-200 pb-2 dark:border-slate-700">
          <button className={`rounded px-3 py-1 text-sm ${builderTab === "ai" ? "bg-blue-600 text-white" : "bg-slate-100 dark:bg-slate-800"}`} onClick={() => setBuilderTab("ai")}>AI Generate</button>
          <button className={`rounded px-3 py-1 text-sm ${builderTab === "scrape" ? "bg-blue-600 text-white" : "bg-slate-100 dark:bg-slate-800"}`} onClick={() => setBuilderTab("scrape")}>Import from ExamCompass</button>
          <button className={`rounded px-3 py-1 text-sm ${builderTab === "csv" ? "bg-blue-600 text-white" : "bg-slate-100 dark:bg-slate-800"}`} onClick={() => setBuilderTab("csv")}>CSV Import</button>
        </div>

        {builderTab === "ai" ? (
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <input className="input-field" placeholder="Quiz Title" value={quizForm.title} onChange={(e) => setQuizForm((prev) => ({ ...prev, title: e.target.value }))} />
              <select className="input-field" value={quizForm.question_count} onChange={(e) => setQuizForm((prev) => ({ ...prev, question_count: Number(e.target.value) }))}>
                {QUESTION_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
              <select className="input-field" value={quizForm.module_id} onChange={(e) => setQuizForm((prev) => ({ ...prev, module_id: e.target.value }))}>
                <option value="">Select Module</option>
                {modules.map((moduleItem) => <option key={moduleItem.id} value={moduleItem.id}>{moduleItem.code} - {moduleItem.title}</option>)}
              </select>
              <select className="input-field" value={quizForm.lesson_id} onChange={(e) => setQuizForm((prev) => ({ ...prev, lesson_id: e.target.value }))}>
                <option value="">Select Lesson</option>
                {quizLessons.map((lesson) => <option key={lesson.id} value={lesson.id}>{lesson.lesson_order}. {lesson.title}</option>)}
              </select>
            </div>

            <div className="space-y-2">
              {quizForm.urls.map((url, index) => (
                <div key={`url-${index}`} className="flex gap-2">
                  <input className="input-field" placeholder="https://youtube.com/watch?v=..." value={url} onChange={(e) => setQuizUrl(index, e.target.value)} />
                  {index > 0 ? <button className="btn-secondary" type="button" onClick={() => removeQuizUrl(index)}>Remove</button> : null}
                </div>
              ))}
              <button className="btn-secondary" type="button" onClick={addQuizUrl} disabled={quizForm.urls.length >= 5}>+ Add URL</button>
            </div>

            <button className="btn-primary" type="button" onClick={handleGenerateQuiz} disabled={quizLoading}>
              {quizLoading ? `Generating from ${quizForm.urls.map((url) => url.trim()).filter(Boolean).length || 1} video(s)...` : "Generate Quiz"}
            </button>
            {quizSuccess ? <p className="text-sm text-green-600">{quizSuccess}</p> : null}
            {quizError ? <p className="text-sm text-red-600">{quizError}</p> : null}
          </div>
        ) : null}

        {builderTab === "scrape" ? (
          <div className="space-y-4">
            <div className="flex gap-2">
              <input className="input-field" placeholder="https://www.examcompass.com/..." value={scrapeUrl} onChange={(e) => setScrapeUrl(e.target.value)} />
              <button className="btn-primary" onClick={onScrapePreview} disabled={scrapeLoading}>Preview</button>
            </div>
            {scrapeLoading ? <p className="text-sm text-slate-500">Loading page with headless browser - takes 10-20 seconds...</p> : null}
            {scrapeError ? <p className="text-sm text-red-600">{scrapeError}</p> : null}
            {scrapeData ? (
              <div className="space-y-3 rounded border border-slate-200 p-3 dark:border-slate-700">
                <p className="font-semibold">{scrapeData.title}</p>
                <p className="text-sm text-slate-500">{scrapeData.question_count} questions found</p>
                <div className="space-y-2 text-sm">
                  {(scrapeData.questions || []).slice(0, 5).map((q, idx) => <p key={idx}>{idx + 1}. {q.question_text}</p>)}
                </div>
                <div className="grid gap-2 md:grid-cols-2">
                  <input className="input-field" type="number" min={1} value={scrapeWeek} onChange={(e) => setScrapeWeek(Number(e.target.value || 1))} />
                  <select className="input-field" value={scrapeLessonId} onChange={(e) => setScrapeLessonId(e.target.value)}>
                    <option value="">Select Lesson</option>
                    {lessonOptions.map((lesson) => <option key={lesson.id} value={lesson.id}>{lesson.lesson_order}. {lesson.title}</option>)}
                  </select>
                </div>
                <p className="rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-700 dark:bg-amber-950/20 dark:text-amber-300">Correct answers may default to A - review after saving.</p>
                <button className="btn-primary" onClick={onScrapeSave}>Save Quiz ({scrapeData.questions.length} questions)</button>
              </div>
            ) : null}
          </div>
        ) : null}

        {builderTab === "csv" ? (
          <div className="space-y-4">
            <button className="btn-secondary" onClick={downloadTemplate}>Download Template</button>
            <input className="input-field" type="file" accept=".csv" onChange={handleCsvUpload} />
            {csvError ? <p className="text-sm text-red-600">{csvError}</p> : null}
            {csvPreview ? (
              <div className="space-y-3 rounded border border-slate-200 p-3 dark:border-slate-700">
                <p className="font-semibold">{csvPreview.title}</p>
                <p className="text-sm text-slate-500">{csvPreview.questions.length} questions parsed</p>
                {(csvPreview.questions || []).slice(0, 5).map((q, i) => <p key={i} className="text-sm">{i + 1}. {q.question_text}</p>)}
                <div className="grid gap-2 md:grid-cols-2">
                  <input className="input-field" type="number" min={1} value={csvWeek} onChange={(e) => setCsvWeek(Number(e.target.value || 1))} />
                  <select className="input-field" value={csvLessonId} onChange={(e) => setCsvLessonId(e.target.value)}>
                    <option value="">Select Lesson</option>
                    {lessonOptions.map((lesson) => <option key={lesson.id} value={lesson.id}>{lesson.lesson_order}. {lesson.title}</option>)}
                  </select>
                </div>
                <button className="btn-primary" onClick={onCsvSave} disabled={csvSaving}>{csvSaving ? "Saving..." : "Save Quiz"}</button>
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="border-t border-slate-200 pt-4 dark:border-slate-700">
          <h3 className="mb-2 text-lg font-semibold">Recent Quizzes</h3>
          <div className="space-y-2">
            {recentQuizzes.length === 0 ? <p className="text-sm text-slate-500">No quizzes created yet.</p> : null}
            {recentQuizzes.map((quiz) => (
              <div key={quiz.id} className="flex items-center justify-between rounded border border-slate-200 p-3 text-sm dark:border-slate-700">
                <div>
                  <p className="font-medium">Week {quiz.week_number} - {quiz.title} ({quiz.question_count} questions)</p>
                  <p className="text-xs text-slate-500">created {quiz.created_at ? new Date(quiz.created_at).toLocaleDateString() : "-"}</p>
                </div>
                <button className="btn-secondary" onClick={async () => {
                  if (!window.confirm("Delete this quiz?")) return;
                  await deleteQuiz(quiz.id);
                  await loadRecentQuizzes();
                }}>
                  Delete
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
