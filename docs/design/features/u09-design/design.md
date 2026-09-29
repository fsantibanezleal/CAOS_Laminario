# U9 · The design system · design

The specification is [the visual system](../../visual-system.md); how the interface is put together is the wiki page
[11 The interface foundation](../../../architecture/11_interface.md). The research, with every measurement, is
dossier 11 of the planning record (and dossier 05, section 5). This page records the unit's decisions.

## What the unit delivers

| Part | Where |
|---|---|
| The visual-system specification | `docs/design/visual-system.md` |
| Colour tokens in OKLCH for two rooms and 18 collection hues, written as sRGB | `frontend/src/design/tokens.json`, `frontend/scripts/build-tokens.mjs`, `frontend/src/design/tokens.css` |
| The contrast gate over every declared pair (164) | `frontend/scripts/check-contrast.mjs`, `frontend/scripts/lib/color.mjs` |
| Three self-hosted faces, subset, instanced and renamed where the licence requires, with their licences | `scripts/build_fonts.py`, `frontend/public/fonts/`, `frontend/src/design/fonts.css` |
| The room and language machinery, painted from the first frame | `frontend/index.html`, `frontend/src/design/theme.tsx`, `frontend/src/i18n/` |
| Interface glyphs on the icon grid, and the icon component over the U7 sprite | `frontend/public/glyphs.svg`, `frontend/src/ui/Icon.tsx` |
| The primitives with their states | `frontend/src/ui/` |
| The specimen place | `frontend/src/places/design/` |
| The browser gates (fit, motion, states) against the real build | `frontend/gates/` |

## Decisions

- **The reading face is chosen by what it can write.** Atkinson Hyperlegible Next was the legibility candidate, but
  it has no micro sign, and a microscopy interface writes µm everywhere. Source Sans 3 is the one sans measured with
  every symbol needed (µ ± × ° ′ ″ ≈ ≤ ≥ ♀ ♂). Its Reserved Font Name "Source" is dropped from the subset, which is
  shipped as Laminario Sans (OFL FAQ 2.7: a subset is not functionally equivalent to the original).
- **Colours are authored in OKLCH and checked in sRGB.** OKLCH keeps lightness even while hue changes, so 18
  collection hues can share one lightness and all pass contrast; the gate checks the hex the browser actually draws,
  from the same source file the stylesheet is generated from.
- **A collection is never identified by its hue alone.** Eighteen hues cannot all be told apart (neighbours are
  about 0.03 apart in OKLab), so the tag always carries the icon and the name.
- **Two rooms, not a light and a dark palette.** Each room has a light source (daylight on paper, a lamp on the
  stage); shadows exist only in daylight, the lamp-lit room uses a warm rim instead. The stage is near-neutral in
  both, so a specimen's stain is not tinted by its frame.
- **No flash of the other room.** A few lines in `index.html` set the room and the language from the device's
  stored choice (or the system and the browser) before the first paint.
- **Languages without a library.** Two languages and a few hundred strings do not need a message compiler: typed
  catalogues (Spanish typed against the English keys, so a missing string fails the build) and the platform's
  `Intl` for plurals, numbers, dates and lists.
- **Nothing moves by itself, and nothing disappears on a timer.** Motion follows the visitor's action (the slide's
  move uses View Transitions where the browser has them); toasts stay until dismissed.
- **Found while building, and fixed with a test:** a date-only value ("1962-08-31") is read by JavaScript as
  midnight UTC, so the first specimen label showed 30 August for a slide collected on 31 August; calendar dates are
  now formatted in UTC (R-903). The fit gate found the closed tooltip still taking width at the right edge, which
  scrolled the Spanish page sideways; a closed tooltip is now not laid out, and an open one is kept inside the
  viewport.
