import { BookOpen, ExternalLink, Play } from "lucide-react";
import AcademyScene from "./AcademyScene";

// The castle is a decorative poster. The destination is always the real API URL.
export default function LessonVideo({ title, provider, duration, url, video = true, onOpen, internalCard = false, opener, opened = false }) {
  if (!internalCard && !/^https?:\/\//i.test(url || "") && !/^\/(?!\/)/.test(url || "")) return <p role="alert">This resource link is unavailable.</p>;
  const Icon = video ? Play : BookOpen;
  const action = video ? (/^(www\.)?(youtube\.com|youtu\.be)$/.test(safeHost(url)) ? "Watch on YouTube" : "Open video") : internalCard ? opened ? "View again" : "View teaching card" : opened ? "Open again" : "Open resource";
  const shared = { onClick: onOpen };
  const destination = internalCard ? {} : { href: url, target: "_blank", rel: "noopener noreferrer" };
  const Control = internalCard ? "button" : "a";
  return <section className="lesson-video" aria-label={video ? "Lesson video" : "Featured teaching resource"}>
    <AcademyScene kind="video" dark />
    <Control {...shared} {...destination} type={internalCard ? "button" : undefined} className="play" aria-label={`${video ? "Play" : "View"}: ${title}`}><Icon size={30} aria-hidden="true" /></Control>
    <div className="video-caption"><div><span className="eyebrow">{provider || (video ? "Lesson video" : "Teaching resource")}</span><h2>{title}</h2></div><div className="actions">{duration ? <span className="mono small">{duration}</span> : null}<Control {...shared} {...destination} ref={opener} type={internalCard ? "button" : undefined} className="btn btn-video">{action}<ExternalLink size={16} aria-hidden="true" /><span className="sr-only">{internalCard ? "" : " (opens in a new tab)"}</span></Control></div></div>
  </section>;
}

function safeHost(url) { try { return new URL(url).hostname; } catch { return ""; } }
