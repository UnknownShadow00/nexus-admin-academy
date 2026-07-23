import { ChevronLeft } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import OrientationPracticePanel from "../components/OrientationPracticePanel";
import { getLesson, getLessonNote, saveLessonNote } from "../services/api";

function getYouTubeEmbedUrl(url) {
  if (!url) return null;
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/);
  return match ? `https://www.youtube.com/embed/${match[1]}` : null;
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
      <h2 className="text-xl font-bold">Lesson notes</h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Notes save automatically to your account.</p>
      <textarea
        className="input-field mt-3 w-full"
        disabled={loading}
        onChange={(event) => {
          editedRef.current = true;
          setContent(event.target.value);
        }}
        placeholder={orientation ? "Write one sentence: Where will you look when you are unsure what comes next?" : "Your notes for this lesson..."}
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
  const [error, setError] = useState("");
  const [orientationRefresh, setOrientationRefresh] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLesson(null);
    setError("");
    getLesson(lessonId, { suppressToast: true })
      .then((response) => { if (!cancelled) setLesson(response.data); })
      .catch((requestError) => {
        if (!cancelled) setError(requestError?.response?.status === 403 ? "This lesson is still locked." : "This lesson could not be loaded.");
      });
    return () => { cancelled = true; };
  }, [lessonId]);

  if (error) return <main className="mx-auto max-w-3xl p-6"><Link className="mb-4 inline-flex items-center gap-1 text-blue-600" to="/training"><ChevronLeft size={16} />My Training</Link><div className="panel" role="alert">{error}</div></main>;
  if (!lesson) return <main className="mx-auto max-w-4xl p-6"><div className="h-64 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-800" /></main>;

  const embedUrl = getYouTubeEmbedUrl(lesson.video_url);
  return (
    <main className="mx-auto max-w-4xl space-y-6 p-4 pb-20 sm:p-6">
      <Link className="inline-flex items-center gap-1 text-sm font-semibold text-blue-600" to="/training"><ChevronLeft size={16} />My Training</Link>
      <header className="panel">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-blue-600">{lesson.module_code}</p>
        <h1 className="mt-2 text-3xl font-bold">{lesson.title}</h1>
        {lesson.summary ? <div className="mt-4 whitespace-pre-line leading-7 text-slate-700 dark:text-slate-300">{lesson.summary}</div> : null}
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
      <LessonNotes lessonId={lesson.id} orientation={lesson.is_orientation} onSaved={() => setOrientationRefresh((value) => value + 1)} />
      {lesson.is_orientation ? <OrientationPracticePanel refreshKey={orientationRefresh} /> : null}
    </main>
  );
}
