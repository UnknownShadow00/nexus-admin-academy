import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getAdminFlaggedAttempts, getQuizQuestions, updateQuiz } from "../../services/api";
import QuestionEditorCard from "../../components/admin/QuestionEditorCard";

export default function QuizEditorPage() {
  const { quizId } = useParams();
  const [quiz, setQuiz] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [publishSaving, setPublishSaving] = useState(false);
  const [publishError, setPublishError] = useState("");

  const [titleEdit, setTitleEdit] = useState("");
  const [titleSaving, setTitleSaving] = useState(false);
  const [titleSaved, setTitleSaved] = useState(false);
  const [titleError, setTitleError] = useState("");
  const [flaggedAttempts, setFlaggedAttempts] = useState([]);
  const [organizationSaving, setOrganizationSaving] = useState(false);
  const [organizationMessage, setOrganizationMessage] = useState("");

  useEffect(() => {
    const run = async () => {
      const res = await getQuizQuestions(quizId);
      const nextTitle = res.data?.title || "";
      setQuiz(res.data || { title: nextTitle, status: "draft" });
      setTitleEdit(nextTitle);
      setQuestions(res.data?.questions || []);
      getAdminFlaggedAttempts({ suppressToast: true })
        .then((flaggedRes) => {
          const data = Array.isArray(flaggedRes?.data) ? flaggedRes.data : Array.isArray(flaggedRes) ? flaggedRes : [];
          setFlaggedAttempts(data.filter((attempt) => attempt.quiz_id === Number(quizId)));
        })
        .catch(() => {});
    };
    run();
  }, [quizId]);

  const publishQuiz = async () => {
    setPublishSaving(true);
    setPublishError("");
    try {
      await updateQuiz(quizId, { status: "published" }, { suppressToast: true });
      setQuiz((prev) => ({ ...(prev || {}), status: "published" }));
    } catch (error) {
      setPublishError(error?.response?.data?.detail || "Unable to publish this quiz.");
    } finally {
      setPublishSaving(false);
    }
  };

  const saveTitle = async () => {
    const trimmed = titleEdit.trim();
    if (!trimmed || !quiz) return;

    setTitleSaving(true);
    setTitleSaved(false);
    setTitleError("");
    try {
      const res = await updateQuiz(quizId, { title: trimmed });
      const updatedTitle = res.data?.title || trimmed;
      setQuiz((prev) => ({ ...(prev || {}), title: updatedTitle }));
      setTitleEdit(updatedTitle);
      setTitleSaved(true);
      setTimeout(() => setTitleSaved(false), 1500);
    } catch (error) {
      setTitleError(error?.response?.data?.detail || "Failed to save title");
    } finally {
      setTitleSaving(false);
    }
  };

  const updateOrganization = (field, value) => setQuiz((current) => ({ ...current, [field]: value }));

  const saveOrganization = async () => {
    setOrganizationSaving(true);
    setOrganizationMessage("");
    try {
      const payload = {
        week_number: Number(quiz.week_number), quiz_purpose: quiz.quiz_purpose,
        is_required: Boolean(quiz.is_required), show_in_weekly_checklist: Boolean(quiz.show_in_weekly_checklist),
        show_in_practice_library: Boolean(quiz.show_in_practice_library), editorial_status: quiz.editorial_status,
        recommended_week: quiz.recommended_week === "" ? null : Number(quiz.recommended_week),
        prerequisite_week: quiz.prerequisite_week === "" ? null : Number(quiz.prerequisite_week),
        quality_score: quiz.quality_score === "" ? null : Number(quiz.quality_score),
        source_type: quiz.source_type, answer_keys_validated: Boolean(quiz.answer_keys_validated),
        explanations_complete: Boolean(quiz.explanations_complete), is_active: Boolean(quiz.is_active),
      };
      const res = await updateQuiz(quizId, payload);
      setQuiz((current) => ({ ...current, ...(res.data || {}) }));
      setOrganizationMessage("Organization saved.");
    } catch (error) {
      setOrganizationMessage(error?.response?.data?.detail || "Unable to save organization.");
    } finally { setOrganizationSaving(false); }
  };

  const handleQuestionSaved = (questionId, patch) => {
    setQuestions((rows) => rows.map((q) => (q.id === questionId ? { ...q, ...patch } : q)));
  };

  if (!quiz) return <main className="p-6">Loading...</main>;

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-6">
      <div className="panel space-y-3 dark:border-slate-700 dark:bg-slate-900">
        <h1 className="text-2xl font-bold dark:text-slate-100">Edit Quiz</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">{questions.length} questions</p>

        <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200">
          Quiz Title
          <span className="ml-2 text-xs font-normal text-slate-500 dark:text-slate-400">
            (must match quiz_title in curriculum for video linking)
          </span>
        </label>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <input
            className="input-field flex-1"
            value={titleEdit}
            onChange={(e) => setTitleEdit(e.target.value)}
            placeholder="Enter quiz title"
          />
          <button
            className="btn-primary shrink-0"
            onClick={saveTitle}
            disabled={titleSaving || !titleEdit.trim() || titleEdit.trim() === (quiz.title || "").trim()}
          >
            {titleSaving ? "Saving..." : titleSaved ? "Saved" : "Save Title"}
          </button>
        </div>

        {titleError ? <p className="text-sm text-red-600 dark:text-red-400">{titleError}</p> : null}

        <p className="text-xs text-slate-500 dark:text-slate-400">
          To link this quiz to a video, the title must exactly match the video's quiz_title in the Curriculum editor.
        </p>

        <div className="flex items-center gap-3 pt-2">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
              quiz.status === "published"
                ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
                : "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300"
            }`}
          >
            {quiz.status === "published" ? "Published" : "Draft"}
          </span>
          {quiz.status !== "published" ? (
            <button className="btn-primary" onClick={publishQuiz} disabled={publishSaving}>
              {publishSaving ? "Publishing..." : "Publish Quiz"}
            </button>
          ) : null}
        </div>
        {publishError ? (
          <p className="rounded border border-red-300 bg-red-50 p-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200">
            {publishError}
          </p>
        ) : null}

        <div className="grid gap-3 border-t border-slate-200 pt-4 sm:grid-cols-2 dark:border-slate-700">
          <label className="text-sm">Purpose<select className="input-field mt-1" value={quiz.quiz_purpose || "practice"} onChange={(e) => updateOrganization("quiz_purpose", e.target.value)}><option value="required">Required</option><option value="practice">Practice</option><option value="remediation">Remediation</option><option value="cumulative">Cumulative</option><option value="gate">Promotion Gate</option><option value="certification">Certification</option></select></label>
          <label className="text-sm">Editorial status<select className="input-field mt-1" value={quiz.editorial_status || "unreviewed"} onChange={(e) => updateOrganization("editorial_status", e.target.value)}><option value="unreviewed">Unreviewed</option><option value="needs_edit">Needs edit</option><option value="validated">Validated</option><option value="archived">Archived</option></select></label>
          <label className="text-sm">Week<input className="input-field mt-1" type="number" min={0} max={24} value={quiz.week_number ?? 1} onChange={(e) => updateOrganization("week_number", e.target.value)} /></label>
          <label className="text-sm">Recommended week<input className="input-field mt-1" type="number" min={0} max={24} value={quiz.recommended_week ?? ""} onChange={(e) => updateOrganization("recommended_week", e.target.value)} /></label>
          <label className="text-sm">Prerequisite week<input className="input-field mt-1" type="number" min={0} max={24} value={quiz.prerequisite_week ?? ""} onChange={(e) => updateOrganization("prerequisite_week", e.target.value)} /></label>
          <label className="text-sm">Quality score<input className="input-field mt-1" type="number" min={0} max={100} value={quiz.quality_score ?? ""} onChange={(e) => updateOrganization("quality_score", e.target.value)} /></label>
          <label className="text-sm">Source<select className="input-field mt-1" value={quiz.source_type || "unknown"} onChange={(e) => updateOrganization("source_type", e.target.value)}><option value="seed">Seed</option><option value="examcompass">ExamCompass</option><option value="ai_generated">AI generated</option><option value="manual">Manual</option><option value="scraped">Scraped</option><option value="unknown">Unknown</option></select></label>
          <div className="grid gap-2 text-sm sm:grid-cols-2">
            {[['is_required','Required'],['show_in_weekly_checklist','Weekly checklist'],['show_in_practice_library','Practice library'],['answer_keys_validated','Answers validated'],['explanations_complete','Explanations complete'],['is_active','Active']].map(([field,label]) => <label key={field} className="flex items-center gap-2"><input type="checkbox" checked={Boolean(quiz[field])} onChange={(e) => updateOrganization(field, e.target.checked)} />{label}</label>)}
          </div>
        </div>
        {quiz.source_type === "examcompass" && !quiz.answer_keys_validated && (quiz.is_required || quiz.show_in_weekly_checklist) ? <p className="rounded border border-amber-300 bg-amber-50 p-2 text-sm text-amber-800">This imported quiz cannot be required until its answer keys are independently validated.</p> : null}
        <div className="flex items-center gap-3"><button className="btn-primary" onClick={saveOrganization} disabled={organizationSaving}>{organizationSaving ? "Saving…" : "Save Organization"}</button>{organizationMessage ? <span className="text-sm text-slate-600 dark:text-slate-300">{organizationMessage}</span> : null}</div>
      </div>

      {questions.map((q, i) => (
        <QuestionEditorCard key={q.id} question={q} index={i} onSaved={handleQuestionSaved} />
      ))}

      {flaggedAttempts.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 text-base font-semibold text-slate-800 dark:text-slate-200">Speed-Flagged Attempts</h2>
          <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-slate-600 dark:text-slate-300">Student</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600 dark:text-slate-300">Score</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600 dark:text-slate-300">Avg Time/Q</th>
                  <th className="px-4 py-2 text-left font-medium text-slate-600 dark:text-slate-300">Date</th>
                </tr>
              </thead>
              <tbody>
                {flaggedAttempts.map((attempt) => (
                  <tr key={attempt.attempt_id} className="border-t border-slate-100 dark:border-slate-700">
                    <td className="px-4 py-2 text-slate-800 dark:text-slate-200">{attempt.student_name}</td>
                    <td className="px-4 py-2 text-slate-800 dark:text-slate-200">{attempt.score}</td>
                    <td className="px-4 py-2">
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
                        {attempt.avg_seconds_per_question}s avg
                      </span>
                    </td>
                    <td className="px-4 py-2 text-slate-500 dark:text-slate-400">
                      {attempt.completed_at ? new Date(attempt.completed_at).toLocaleDateString() : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </main>
  );
}
