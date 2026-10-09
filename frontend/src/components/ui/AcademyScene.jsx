// Original branch artwork; provenance and usage are in docs/design/phase1-artwork.md.
// Decorative layers stay outside the accessibility tree and never intercept input.
export default function AcademyScene({ variant = "hero" }) {
  return <div className={`academy-scene academy-scene-${variant}`} aria-hidden="true">
    <div className="academy-scene-sky" />
    <div className="academy-art-slot academy-art-castle" data-art-slot="castle" />
    <div className="academy-art-slot academy-art-shadows" data-art-slot="shadow-army" />
    <div className="academy-art-slot academy-art-protagonist" data-art-slot="hooded-protagonist" />
    <div className="academy-scene-scrim" />
  </div>;
}
