import { useEffect, useMemo, useState } from "react";
import { toast } from "react-hot-toast";

import Spinner from "../../components/Spinner";
import { getCurriculum, getCurriculumLinkStatus, updateCurriculumVideo } from "../../services/api";

function EditableCell({ value, onSave, placeholder, type = "text", forceEditing = false, onEditFinish }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(value || "");

  useEffect(() => {
    setVal(value || "");
  }, [value]);

  useEffect(() => {
    if (forceEditing) setEditing(true);
  }, [forceEditing]);

  const save = async () => {
    setEditing(false);
    onEditFinish?.();
    if (val !== value) await onSave(val);
  };

  const cancel = () => {
    setEditing(false);
    setVal(value || "");
    onEditFinish?.();
  };

  if (editing) {
    return (
      <input
        autoFocus
        type={type}
        className="w-full rounded border border-blue-400 bg-white px-2 py-1 text-sm focus:outline-none dark:bg-slate-800"
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onBlur={save}
        onKeyDown={(e) => {
          if (e.key === "Enter") save();
          if (e.key === "Escape") cancel();
        }}
      />
    );
  }

  return (
    <span
      onClick={() => setEditing(true)}
      className="block cursor-pointer truncate rounded px-1 py-0.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-700"
      title="Click to edit"
    >
      {value || <span className="text-slate-400 italic">{placeholder || "click to add"}</span>}
    </span>
  );
}

export default function CurriculumEditorPage() {
  const [curriculum, setCurriculum] = useState([]);
  const [linkStatus, setLinkStatus] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingQuizTitleId, setEditingQuizTitleId] = useState(null);

  useEffect(() => {
    const run = async () => {
      const [curriculumRes, linkStatusRes] = await Promise.all([
        getCurriculum(),
        getCurriculumLinkStatus(),
      ]);
      setCurriculum(curriculumRes.data || []);
      setLinkStatus(linkStatusRes.data || []);
      setLoading(false);
    };
    run();
  }, []);

  const refreshLinkStatus = async () => {
    const linkStatusRes = await getCurriculumLinkStatus();
    setLinkStatus(linkStatusRes.data || []);
  };

  const handleUpdate = async (videoId, field, value) => {
    try {
      await updateCurriculumVideo(videoId, { [field]: value });
      toast.success("Saved");
      setCurriculum((prev) =>
        prev.map((sec) => ({
          ...sec,
          videos: sec.videos.map((v) =>
            v.id === videoId ? { ...v, [field]: value } : v
          ),
        }))
      );
      if (field === "quiz_title") {
        await refreshLinkStatus();
      }
    } catch {
      toast.error("Save failed");
    }
  };

  const unlinked = useMemo(
    () => (linkStatus || []).filter((row) => !row.linked),
    [linkStatus]
  );

  const startInlineQuizTitleEdit = (videoId) => {
    setEditingQuizTitleId(videoId);
    const rowEl = document.getElementById(`video-row-${videoId}`);
    if (rowEl) {
      rowEl.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  if (loading)
    return (
      <main className="mx-auto max-w-6xl p-6">
        <Spinner text="Loading..." />
      </main>
    );

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-4 pb-20">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Curriculum Editor
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Click any cell to edit. Changes save instantly.
        </p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">Link Status</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          {(linkStatus.length || 0) - unlinked.length}/{linkStatus.length || 0} videos linked to quizzes
        </p>

        {unlinked.length === 0 ? (
          <p className="mt-3 text-sm text-green-700 dark:text-green-300">All curriculum videos are linked.</p>
        ) : (
          <div className="mt-3 space-y-2">
            {unlinked.map((row) => (
              <div key={row.id} className="rounded border border-amber-200 bg-amber-50 p-2 text-sm dark:border-amber-800 dark:bg-amber-950/30">
                <div className="font-medium text-slate-900 dark:text-slate-100">{row.title}</div>
                <div className="text-slate-600 dark:text-slate-300">Expected quiz_title: {row.quiz_title || "(empty)"}</div>
                <button
                  type="button"
                  className="mt-1 text-xs font-semibold text-blue-600 hover:text-blue-700"
                  onClick={() => startInlineQuizTitleEdit(row.id)}
                >
                  Edit
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {curriculum.map((sec) => (
        <div key={sec.section} className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="border-b border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800">
            <h2 className="font-bold text-slate-800 dark:text-slate-200">{sec.section}</h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs text-slate-500 dark:border-slate-800">
                  <th className="w-48 px-3 py-2 text-left font-medium">Video Title</th>
                  <th className="w-16 px-3 py-2 text-left font-medium">Duration</th>
                  <th className="px-3 py-2 text-left font-medium">Professor Messer URL</th>
                  <th className="w-56 px-3 py-2 text-left font-medium">Linked Quiz Title</th>
                </tr>
              </thead>
              <tbody>
                {sec.videos.map((video, idx) => (
                  <tr
                    key={video.id}
                    id={`video-row-${video.id}`}
                    className={`border-b border-slate-50 dark:border-slate-800/50 ${
                      idx % 2 === 0 ? "" : "bg-slate-50/50 dark:bg-slate-800/20"
                    }`}
                  >
                    <td className="px-3 py-2">
                      <EditableCell
                        value={video.title}
                        placeholder="Video title"
                        onSave={(v) => handleUpdate(video.id, "title", v)}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <EditableCell
                        value={video.duration}
                        placeholder="0:00"
                        onSave={(v) => handleUpdate(video.id, "duration", v)}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <EditableCell
                          value={video.url}
                          placeholder="https://..."
                          onSave={(v) => handleUpdate(video.id, "url", v)}
                        />
                        {video.url && (
                          <a
                            href={video.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="shrink-0 text-xs text-blue-500 hover:text-blue-700"
                          >
                            ?
                          </a>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <EditableCell
                        value={video.quiz_title}
                        placeholder="Quiz name (must match exactly)"
                        onSave={(v) => handleUpdate(video.id, "quiz_title", v)}
                        forceEditing={editingQuizTitleId === video.id}
                        onEditFinish={() => {
                          if (editingQuizTitleId === video.id) setEditingQuizTitleId(null);
                        }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </main>
  );
}
