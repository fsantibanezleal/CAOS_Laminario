# 11 · The interface foundation

![The interface foundation: tokens.json and the upstream fonts are built into the stylesheet and the font files; index.html paints the stored room and language before the first frame; the providers carry them through the app; the primitives and places draw only with tokens; the gates check the source and the real build](svg/interface.svg)

The interface is written in React 19 with TypeScript and built by Vite; it is styled with plain CSS custom
properties and CSS Modules, and it uses no shared shell and no component library (the plan, sections 3.1 and 3.3).
This page describes the foundation every place stands on. What it looks like is specified in
[the visual system](../design/visual-system.md).

## 1. From sources to the page

| Source | Built by | Output | Checked by |
|---|---|---|---|
| `frontend/src/design/tokens.json`: colours in OKLCH per room, collection hues, the contrast pairs | `frontend/scripts/build-tokens.mjs` | `frontend/src/design/tokens.css` | `build-tokens.mjs --check` (the file is the rebuild), `check-contrast.mjs` (R-081) |
| The fonts at a pinned google/fonts commit, with their SHA-256 | `scripts/build_fonts.py` (fontTools: subset, instance, rename) | `frontend/public/fonts/*.woff2` and their `OFL.txt` | `build_fonts.py --check` |
| `app/collections/data/tree.yaml` and the icon drawings (U7) | `scripts/build_icons.py` | `frontend/public/icons.svg` | the icon gate of U7 |
| `frontend/public/glyphs.svg` | drawn by hand on the icon grid | itself | read in the specimen place |
| `frontend/src/i18n/en.ts`, `es.ts` | the TypeScript compiler (Spanish typed against the English keys) | the bundle | `check-i18n.mjs` (R-089) |

The colour conversion is the CSS Color 4 one: OKLCH to OKLab to linear sRGB (Ottosson's matrices), gamut-mapped by
lowering chroma at the same lightness and hue, then encoded to 8-bit sRGB. The contrast ratio is WCAG 2.2's,
(L1 + 0.05) / (L2 + 0.05), with relative luminance L = 0.2126 R + 0.7152 G + 0.0722 B of the linearised channels
(threshold 0.04045). The same module (`frontend/scripts/lib/color.mjs`) serves the build and the gate, so what is
checked is what is drawn.

## 2. The first frame

`index.html` holds a few lines that run before the stylesheet paints anything: they read the room and the language
the visitor chose on this device (`localStorage`, inside try and catch for private windows), fall back to the
system's colour preference and the browser's first English or Spanish language, and set `data-theme` and `lang` on
`<html>`. The generated stylesheet has the daylight room on `:root`, the lamp-lit room on
`[data-theme="lamplit"]`, and the lamp-lit room again under the system's dark preference when no `data-theme` is set,
so the page is right even without JavaScript. Only the reading face is preloaded.

## 3. The providers

| Provider | Holds | Notes |
|---|---|---|
| `RoomProvider` (`src/design/theme.tsx`) | the choice (system, daylight, lamp-lit) and the room in force | follows system changes while the choice is "system"; writes `data-theme` |
| `LanguageProvider` (`src/i18n/index.tsx`) | the language, `t`, `plural`, `number`, `date`, `list` | writes `<html lang>`; plurals by `Intl.PluralRules` with a fallback to "other"; calendar dates in UTC (`src/i18n/format.ts`) |
| `ToastRegion` (`src/ui/Overlay.tsx`) | toasts in a polite live region | a toast stays until dismissed |

## 4. The primitives

Every primitive is in `frontend/src/ui/`, with its CSS Module, and draws only with tokens. The platform's own
elements are used wherever they carry the right behaviour: `<button>`, `<input type="checkbox|radio|search">`,
`<select>`, `<fieldset>` with `<legend>`, `<dialog>` with `showModal()` (it keeps focus inside and makes the page
inert), `<progress>` semantics through `role="progressbar"`. Where the platform has no element, the WAI-ARIA
Authoring Practices pattern is followed: tabs (one tab stop, arrow keys, Home and End), the switch
(`role="switch"`), the tooltip (`role="tooltip"`, opened by hover and focus, closed by Escape, hoverable).

## 5. The gates

| Gate | Runs | Measures |
|---|---|---|
| `check-contrast.mjs` | Node, in CI | 164 colour pairs of both rooms against their WCAG 2.2 minimum |
| `check-i18n.mjs` | Node, in CI | the same keys in both catalogues, no empty value, the same placeholders |
| `build-tokens.mjs --check` | Node, in CI | the committed stylesheet is the rebuild of its source |
| `npm test` (Vitest) | Node, in CI | date and plural formatting |
| `gates/fit.mjs` | Playwright's Chromium against `vite preview` of the real build, locally | no sideways scroll at 360, 768, 1280 and 1920 px, both rooms, both languages; the page painted in the room and language asked for; a full-page screenshot of each case |
| `gates/motion.mjs` | same | with reduced motion emulated, the computed transition and animation durations of every element and pseudo-element |
| `gates/states.mjs` | same | keyboard focus, tooltip, dialog (focus in and back), toast, with screenshots in both rooms |

The browser gates need `PLAYWRIGHT_BROWSERS_PATH` pointing at the browser cache (outside the repository) and a
build in `frontend/dist`. Their screenshots go to `frontend/.gates/`, which git ignores, and are read before a unit
closes.
