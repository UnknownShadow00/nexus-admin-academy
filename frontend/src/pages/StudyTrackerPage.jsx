import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getCurriculum,
  getQuizzes,
  getStudyTracker,
  markVideoWatched,
  unmarkVideoWatched,
} from "../services/api";
import { getCurrentStudent } from "../hooks/useAuth";
import { setSelectedProfile } from "../services/profile";
import { scoreBand } from "../utils/theme";
import TrainingSubnav from "../components/TrainingSubnav";

const JOB_TAGS = {
  job_critical: { label: "Job Critical", shortLabel: "Job Critical", cls: "bg-indigo-600 text-white border-indigo-600" },
  know_it: { label: "Know It", shortLabel: "Know It", cls: "bg-slate-200 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-200 dark:border-slate-700" },
  awareness: { label: "Awareness", shortLabel: "Awareness Only", cls: "bg-transparent text-slate-500 border-slate-300 dark:text-slate-300 dark:border-slate-600" },
};

function ScoreBadge({ pct }) {
  if (pct == null) return null;
  const cls = scoreBand.classes[scoreBand(pct)];
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-bold ${cls}`}>
      {pct}%
    </span>
  );
}

function JobRelevanceBadge({ value }) {
  const tag = JOB_TAGS[value] || JOB_TAGS.know_it;
  return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${tag.cls}`}>{tag.label}</span>;
}

function SectionBlock({ section, videos, watched, scores, quizMap, onToggleWatch }) {
  const [open, setOpen] = useState(true);

  const watchedCount = videos.filter((v) => watched[v.key]).length;
  const pct = Math.round((watchedCount / videos.length) * 100);

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between rounded-xl p-4 text-left hover:bg-slate-50 dark:hover:bg-slate-800/50"
      >
        <div className="flex items-center gap-3">
          <span className="text-base font-bold text-slate-900 dark:text-slate-100">
            {section}
          </span>
          <span className="text-sm text-slate-400">
            {watchedCount}/{videos.length} watched
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2">
            <div className="h-2 w-28 rounded-full bg-slate-200 dark:bg-slate-700">
              <div
                className="h-2 rounded-full bg-blue-500 transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs text-slate-400">{pct}%</span>
          </div>
          <span className="text-slate-400 text-sm">{open ? "▲" : "▼"}</span>
        </div>
      </button>

      {open && (
        <div className="border-t border-slate-100 dark:border-slate-800">
          {videos.map((video, idx) => {
            const isWatched = !!watched[video.key];
            const quizScore = video.quiz_title ? scores[video.quiz_title] : null;
            const quizId = video.quiz_title ? quizMap[video.quiz_title] : null;

            return (
              <div
                key={video.key}
                className={`flex flex-wrap items-center gap-3 px-4 py-3 sm:flex-nowrap ${
                  idx < videos.length - 1
                    ? "border-b border-slate-100 dark:border-slate-800"
                    : ""
                } ${isWatched ? "bg-green-50/40 dark:bg-green-950/10" : ""}`}
              >
                <button
                  onClick={() => onToggleWatch(video.key, isWatched)}
                  title={isWatched ? "Unmark watched" : "Mark as watched"}
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2 text-sm font-bold transition-all ${
                    isWatched
                      ? "border-green-500 bg-green-500 text-white"
                      : "border-slate-300 text-transparent hover:border-green-400 dark:border-slate-600"
                  }`}
                >
                  ✓
                </button>

                <a
                  href={video.url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex min-w-0 flex-1 items-center gap-2 group"
                >
                  <span
                    className={`truncate text-sm font-medium transition-colors group-hover:text-blue-600 ${
                      isWatched
                        ? "text-slate-400 line-through dark:text-slate-500"
                        : "text-slate-900 dark:text-slate-100"
                    }`}
                  >
                    {video.title}
                  </span>
                    {video.duration && (
                    <span className="shrink-0 text-xs text-slate-400">
                      ({video.duration})
                    </span>
                  )}
                  <JobRelevanceBadge value={video.job_relevance} />
                  <span className="shrink-0 text-xs text-blue-400 opacity-0 group-hover:opacity-100">
                    ↗
                  </span>
                </a>

                <div className="shrink-0">
                  {quizScore ? (
                    <div className="flex items-center gap-2">
                      <ScoreBadge pct={quizScore.pct} />
                      {quizId ? <><Link to={`/quizzes/${quizId}/review`} className="text-xs font-medium text-blue-600 hover:text-blue-700">Review</Link><Link to={`/quizzes/${quizId}`} className="text-xs text-slate-500 hover:text-blue-600">Retake</Link></> : null}
                    </div>
                  ) : quizId ? (
                    <Link
                      to={`/quizzes/${quizId}`}
                      className="inline-flex items-center rounded-lg border border-blue-300 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-100 dark:border-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                    >
                      Take Quiz →
                    </Link>
                  ) : video.quiz_title ? (
                    <span className="text-xs text-slate-500" title="No approved quiz is currently available">
                      Quiz unavailable
                    </span>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function StudyTrackerPage() {
  const studentId = getCurrentStudent()?.id;
  const [curriculum, setCurriculum] = useState([]);
  const [trackerData, setTrackerData] = useState({ watched: {}, scores: {} });
  const [quizMap, setQuizMap] = useState({});
  const [tagFilter, setTagFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const [currRes, trackerRes, quizRes] = await Promise.all([
          getCurriculum(),
          getStudyTracker(studentId),
          getQuizzes(undefined, studentId),
        ]);
        if (cancelled) return;

        setCurriculum(currRes.data || []);
        setTrackerData(trackerRes.data || { watched: {}, scores: {} });

        const map = {};
        (quizRes.data || []).forEach((q) => {
          map[q.title] = q.id;
        });
        setQuizMap(map);
      } catch {
        if (cancelled) return;
        setCurriculum([]);
        setTrackerData({ watched: {}, scores: {} });
        setQuizMap({});
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [studentId]);

  const handleToggleWatch = async (videoKey, isWatched) => {
    setTrackerData((prev) => {
      const next = { ...prev, watched: { ...prev.watched } };
      if (isWatched) delete next.watched[videoKey];
      else next.watched[videoKey] = new Date().toISOString();
      return next;
    });
    try {
      const response = isWatched
        ? await unmarkVideoWatched(videoKey, studentId)
        : await markVideoWatched(videoKey, studentId);
      const access = response?.data;
      const currentStudent = getCurrentStudent();
      if (currentStudent && typeof access?.a_plus_unlocked === "boolean") {
        setSelectedProfile({
          ...currentStudent,
          a_plus_progress_pct: access.a_plus_progress_pct,
          a_plus_unlocked: access.a_plus_unlocked,
          a_plus_unlock_threshold_pct: access.a_plus_unlock_threshold_pct,
        });
      }
    } catch {
      setTrackerData((prev) => {
        const next = { ...prev, watched: { ...prev.watched } };
        if (isWatched) next.watched[videoKey] = new Date().toISOString();
        else delete next.watched[videoKey];
        return next;
      });
    }
  };

  if (loading)
    return (
      <main className="mx-auto max-w-4xl space-y-4 p-4 pb-20">
        <div className="h-32 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-700" />
        <div className="h-10 animate-pulse rounded-xl bg-slate-200 dark:bg-slate-700" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
            <div className="mb-3 h-4 w-1/3 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
            {[1, 2, 3].map((j) => (
              <div key={j} className="mb-2 h-3 w-full animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
            ))}
          </div>
        ))}
      </main>
    );

  const totalVideos = curriculum.reduce((s, sec) => s + sec.videos.length, 0);
  const totalWatched = Object.keys(trackerData.watched).length;
  const overallPct = totalVideos ? Math.round((totalWatched / totalVideos) * 100) : 0;
  const query = searchQuery.trim().toLowerCase();
  const filteredCurriculum = curriculum
    .map((sec) => ({ ...sec, videos: sec.videos.filter((video) =>
      (tagFilter === "all" || video.job_relevance === tagFilter) &&
      (!query || video.title.toLowerCase().includes(query) || sec.section.toLowerCase().includes(query))
    ) }))
    .filter((sec) => sec.videos.length > 0);

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-4 pb-20">
      <TrainingSubnav />
      <div className="rounded-xl bg-blue-600 p-6 text-white shadow">
        <h1 className="text-2xl font-bold">All Course Content</h1>
        <p className="mt-0.5 text-sm text-blue-200">Browse, watch ahead, or review all CompTIA A+ videos.</p>
        <div className="mt-4">
          <div className="mb-1 flex justify-between text-sm">
            <span>{totalWatched} of {totalVideos} videos watched</span>
            <span className="font-bold">{overallPct}%</span>
          </div>
          <div className="h-3 w-full rounded-full bg-blue-800">
            <div
              className="h-3 rounded-full bg-white transition-all"
              style={{ width: `${overallPct}%` }}
            />
          </div>
        </div>
        <p className="mt-2 text-xs text-blue-300">
          Click ✓ to mark a video watched · Click video title to watch · Click "Take Quiz" when ready
        </p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <label className="block text-xs font-bold uppercase tracking-wide text-slate-500" htmlFor="content-search">Search course content</label>
        <input id="content-search" className="input-field mt-2 w-full" type="search" value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Search videos or sections" />
        <div className="flex flex-wrap gap-2">
          {[
            { value: "all", label: "All" },
            { value: "job_critical", label: "Job Critical" },
            { value: "know_it", label: "Know It" },
            { value: "awareness", label: "Awareness Only" },
          ].map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setTagFilter(opt.value)}
              className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                tagFilter === opt.value
                  ? "border-blue-600 bg-blue-600 text-white"
                  : "border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
          Tags show job relevance for help desk / sysadmin roles, not exam weight.
        </p>
      </div>

      {filteredCurriculum.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-slate-500 dark:text-slate-400">No videos match this filter.</p>
        </div>
      )}

      {filteredCurriculum.map((sec) => (
        <SectionBlock
          key={sec.section}
          section={sec.section}
          videos={sec.videos}
          watched={trackerData.watched}
          scores={trackerData.scores}
          quizMap={quizMap}
          onToggleWatch={handleToggleWatch}
        />
      ))}
    </main>
  );
}
