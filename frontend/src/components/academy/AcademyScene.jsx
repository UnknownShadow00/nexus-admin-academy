// Cleared artwork from approved prototype 76b4a15. Art never supplies UI or data.
export default function AcademyScene({ kind, dark = false }) {
  const portrait = kind === "sidebar" || kind === "thumbnail";
  return <div className={`scene scene-${kind}`} aria-hidden="true">
    {kind !== "quote" ? <img className="castle" src={`/academy/${portrait ? "academy-tower-refined" : `castle-${dark ? "night" : "day"}-refined`}.webp`} alt="" decoding="async" /> : null}
    {["hero", "quote", "footer"].includes(kind) ? <img className="mist" src="/academy/ambient-mist.webp" alt="" decoding="async" /> : null}
    {["hero", "quote"].includes(kind) ? <img className="army" src="/academy/shadow-sentinels.webp" alt="" decoding="async" /> : null}
    {kind === "hero" ? <img className="wanderer" src="/academy/hooded-wanderer.webp" alt="" decoding="async" /> : null}
    <div className="scene-fade" />
  </div>;
}
