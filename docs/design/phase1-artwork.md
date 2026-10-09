# Nexus Academy original branch artwork

Created for the owner's Phase 1 visual correction on 2026-10-08 with the built-in OpenAI imagegen tool. The owner explicitly requested original usable branch assets after rejecting PR #64's empty slots. These are provisional original compositions for review, not final approved brand artwork.

Both package documents and all four supplied boards were inspected. The boards informed composition and palette only: **no board crops, third-party character images, franchise names, stock images, remote image URLs, or proprietary font files were used as generation inputs or shipped assets.** The night scene was edited from the generated daylight scene; every other raster began from a descriptive prompt. The monogram is original code-native SVG geometry written for this branch.

## Asset placement

All files are under `frontend/public/academy/`, loaded locally by `academy.css` and the learner header. `AcademyScene.jsx` composites decorative, noninteractive, `aria-hidden` layers.

| File | Dimensions | Use |
| --- | --- | --- |
| `castle-day.webp` | 1536×1024 | Light hero panorama and sidebar foot |
| `castle-night.webp` | 1536×1024 | Dark hero panorama and sidebar foot; same fortress, blue moon and violet windows |
| `hooded-wanderer.webp` | 1024×1536, alpha | Prominent off-center right hero figure; smaller sidebar figure, both themes |
| `shadow-sentinels.webp` | 1536×1024, alpha | Distant glowing-eye army beneath the foreground figure; subtle sidebar depth |
| `ambient-mist.webp` | 1536×1024 | Low-opacity page backdrop through a theme-specific gradient; reading cards remain opaque |
| `nexus-mark.svg` | 48×48 viewBox | Original angular blue/violet learner N monogram; admin mark stays separate |

The five raster WebPs total approximately 1.2 MiB. Original generated PNGs remain in the tool output directory `/home/nexus/.codex/generated_images/01a11eb2-d279-7713-bd0f-1081f7630adf/`; project copies were encoded using existing FFmpeg/libwebp at quality 88, compression level 6. No new runtime dependency or image service was added. Transparency was preserved and browser-tested. At narrow widths, artwork occupies a separate upper hero band with a solid reading surface beneath it.

## Generation recipes and original outputs

These record the actual requested composition and constraints, condensed for review. No existing artist or franchise style was requested.

1. **Day fortress** — `exec-63a05029-87b3-4412-b97f-90b2cb107b1f.png`: original panoramic cinematic fantasy matte painting; monumental gothic academy fortress in right two thirds, spires, battlements, mountain valley and mist; soft daylight, ice-blue sky, lavender clouds, violet windows, indigo stone; quiet left third for text; architecture recognizable under a wide hero crop; no characters, lettering, logos or UI.
2. **Night fortress** — `exec-8ddd7a3d-2010-4a99-8503-1fa9c24f924f.png`: edit of the original day image, retaining architecture/composition; deep navy/violet night, large icy moon, silver-blue spire edges, violet gates/windows, rolling mist, readable stone; quiet left fog; no characters, UI, text, logos or franchise imagery.
3. **Wanderer** — `exec-0ca91993-e77b-491c-831f-114cda20e3a6.png`: original isolated faceless hooded academy wanderer; three-quarter shoulders toward left, tilted head, no visible skin/eyes/mouth; navy layered weathered cloak, original silver clasp; blue left rim and violet right rim; realistic proportions, no weapons/horns/franchise costume/logos/writing; transparent portrait cutout, hips cropped at bottom.
4. **Sentinels** — `exec-491e746c-3a31-4e3e-bb32-5eb0725d2aa2.png`: original wide staggered row of cloaked spectral silhouettes, varied simple angular helmets/hoods, receding ranks, upper bodies along bottom half; indigo with blue/violet rim and small icy eyes; nonviolent, no weapons/gore/franchise armor/text/logos; isolated alpha with drifting mist, no landscape or floor.
5. **Ambient mist** — `exec-deaafe14-50d5-4192-b40d-cae18dc07793.png`: subtle deep-indigo mist, violet/blue aurora at right/bottom edges, sparse dust, faint weathered stone dissolving into fog; quiet low-contrast center/left; background material only, no characters/army/castle/text/logos/sharp geometry.

## Shipped SHA-256 hashes

```text
050093f5d37650796a171367a77e239faa9bfe005d7d463a72e3e46ce2d6badb  ambient-mist.webp
12297cba3a0e63f0f2765f8a6e35e251b0618e30bafaaaa8a8491766bd291b5a  castle-day.webp
4adabd5693e7a484328e33f0c302c5db3f616378c36a0eb125d62c3b8a55c55b  castle-night.webp
ad60356e9841890d01af2fb1bd6ca9799fb78a74f1861ab25ba34e4b73aa59d4  hooded-wanderer.webp
ef298c9a5cf960f551600f0f00bae7b051cefa02c850cd94a46e22435848b554  nexus-mark.svg
4439d80427014479292abb2e3bb1628b2adf0d084c607ed975a29894ab710bd8  shadow-sentinels.webp
```

## Remaining visual review

All requested artwork slots are filled. The provisional character, army, architecture and new monogram need the owner's visual approval. The composition intentionally preserves real API-driven task/progress panels instead of reproducing the reference boards' fictional routes, schedules and counts. System fonts remain; there is no supplied standalone brand typeface. Art-directed asset variants for other screens and Phase 2 are outside this correction.
