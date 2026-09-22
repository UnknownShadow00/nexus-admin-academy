import { useEffect, useRef, useState } from "react";
import { getCurrentStudent } from "../hooks/useAuth";
import { getLessonNote, saveLessonNote } from "../services/api";

export default function LessonNotes(props) {
  const studentId = getCurrentStudent()?.id;
  return <NotesEditor key={`${studentId}:${props.lessonId}`} {...props} studentId={studentId} />;
}

function NotesEditor({ lessonId, studentId, orientation }) {
  const key = studentId ? `nexus:lesson-note:${studentId}:${lessonId}` : null;
  const [content, setContent] = useState("");
  const [savedContent, setSavedContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState(null);
  const [storageUnavailable, setStorageUnavailable] = useState(false);
  const [retry, setRetry] = useState(0);
  const alive = useRef(false);
  const latest = useRef("");
  const inFlight = useRef(false);
  const dirty = content !== savedContent;

  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(false);
    getLessonNote(lessonId, { suppressToast: true }).then((response) => {
      if (cancelled) return;
      const saved = response.data?.content || "";
      latest.current = saved;
      setContent(saved);
      setSavedContent(saved);
      try {
        const local = key ? localStorage.getItem(key) : null;
        if (local !== null && local !== saved && local.length <= 20000) setDraft(local);
      } catch { setStorageUnavailable(true); }
    }).catch(() => { if (!cancelled) setLoadError(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [lessonId, key, retry]);

  function edit(value) {
    latest.current = value;
    setContent(value);
    setSaveError(false);
    try { if (key) localStorage.setItem(key, value); }
    catch { setStorageUnavailable(true); }
  }

  async function save() {
    if (inFlight.current || loading || loadError || draft !== null) return;
    const submitted = latest.current;
    inFlight.current = true;
    setSaving(true);
    setSaveError(false);
    try {
      await saveLessonNote(lessonId, submitted, { suppressToast: true });
      if (!alive.current) return;
      setSavedContent(submitted);
      try {
        // Another tab or an edit made during this request must keep its draft.
        if (key && localStorage.getItem(key) === submitted) localStorage.removeItem(key);
      } catch { setStorageUnavailable(true); }
    } catch { if (alive.current) setSaveError(true); }
    finally {
      inFlight.current = false;
      if (alive.current) setSaving(false);
    }
  }

  useEffect(() => {
    if (!dirty || loading || saving || saveError || loadError || draft !== null) return;
    const timer = setTimeout(save, 1500);
    return () => clearTimeout(timer);
  }, [content, savedContent, loading, saving, saveError, loadError, draft]);

  return <section className="panel" aria-labelledby="lesson-notes-heading">
    <h2 className="text-xl font-bold" id="lesson-notes-heading">Optional notes</h2>
    <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Notes are a study aid and never affect lesson completion. They save to your account after you pause typing, or when you select Save notes.</p>
    {loadError ? <div role="alert" className="mt-3"><p>Your saved notes could not be loaded. Retry before editing so your existing notes stay safe.</p><button className="btn-secondary mt-2" type="button" onClick={() => setRetry((value) => value + 1)}>Retry loading notes</button></div> : null}
    {draft !== null ? <div className="mt-3 rounded-lg border border-amber-300 p-3">
      <p className="font-semibold">An unsaved draft is available on this browser.</p>
      <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words text-sm">{draft || "(Empty draft)"}</pre>
      <div className="mt-3 flex flex-wrap gap-2"><button className="btn-primary" type="button" onClick={() => { edit(draft); setDraft(null); }}>Restore draft</button><button className="btn-secondary" type="button" onClick={() => {
        try { if (key && localStorage.getItem(key) === draft) localStorage.removeItem(key); } catch { setStorageUnavailable(true); }
        setDraft(null);
      }}>Keep saved notes</button></div>
    </div> : null}
    <label className="mt-3 block text-sm font-medium" htmlFor="lesson-notes-content">Your study notes</label>
    <textarea id="lesson-notes-content" className="input-field mt-2 w-full" disabled={loading || loadError || draft !== null} maxLength={20000} onChange={(event) => edit(event.target.value)} placeholder={orientation ? "Optional: note where you will look when you are unsure what comes next." : "Optional notes for this lesson..."} rows={5} value={content} />
    <div className="mt-3 flex flex-wrap items-center gap-3">
      <button className="btn-secondary" disabled={loading || loadError || saving || !dirty || draft !== null} onClick={save} type="button">{saving ? "Saving notes…" : "Save notes"}</button>
      <p role="status" className="text-sm">{loading ? "Loading notes…" : saveError ? "Notes could not be saved to your account. Your text is still here. Try Save notes again." : saving ? "Saving to your account…" : dirty ? "Unsaved changes" : loadError ? "" : "Saved to your account"}</p>
    </div>
    {storageUnavailable ? <p className="mt-2 text-sm text-amber-800 dark:text-amber-200">Browser draft storage is unavailable. Wait for “Saved to your account” before leaving this page.</p> : null}
  </section>;
}
