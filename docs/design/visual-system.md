# The visual system

Laminario's interface is its own: it does not use the shared CAOS shell, palette or page structure (the plan's
section 3.3, by Felipe's instruction). This page is the specification every place is built from. The research
behind each choice, with the measurements, is dossier 11 of the planning record; the requirements and their gates
are R-080, R-081, R-085 and R-089 of the [design document](SDD.md).

## 1. The idea

A slide lives in four physical places in a real collection: the **cabinet** (a collection), the **drawer** (a
sub-collection, slides lying label end up), the **slide** itself, and the microscope **stage**. The interface uses
those places as its navigation, and draws them the way they look: paper labels typed on a typewriter, oak and brass
in daylight, a lamp-lit stage at night. There are two rooms, and every colour, face, shadow and movement belongs to
one of them.

| Room | Theme | Light source |
|---|---|---|
| The daylight museum room | `daylight` (light) | daylight on warm paper and oak; brass fittings |
| The microscopy room at night | `lamplit` (dark) | the lamp on the paper and on the stage; blue-black walls |

The stage is near-neutral in both rooms, so a stain's colour is judged against grey, not tinted by the frame.

## 2. Faces

| Role | Face | Used for | Files |
|---|---|---|---|
| Reading and interface | **Laminario Sans**, a Latin subset of Source Sans 3 (Paul D. Hunt, Adobe, OFL 1.1), renamed as the licence requires for a modified font with a Reserved Font Name | body text, controls, captions, data | roman and italic, variable weight 200-900 |
| Display | **Fraunces** (Undercase Type, Phaedra Charles, Flavia Zimbardi, OFL 1.1), instanced at SOFT 50, WONK 0, weight 400-700, optical size kept | realm, collection and drawer names, place titles | one variable file |
| Label | **Courier Prime** (Alan Dague-Greene, OFL 1.1) | the catalogue label on the slide, catalogue numbers, measurements in labels | regular, italic, bold |

Every file is a self-hosted WOFF2 subset (Basic Latin, Latin-1 and the symbols a catalogue writes: µ ± × ° ′ ″ ≈ ≤
≥ ‰ – “ ” ‘ ’ … • · ♀ ♂), built by `scripts/build_fonts.py` from the upstream files, whose SHA-256 it records;
each ships with its licence in `frontend/public/fonts/`. Only the reading roman is preloaded. Scientific names are
set in italic in every face; Courier Prime has no ♀ and ♂, so labels write the sex as a word.

Interface sizes (px): 13, 14, **16** (body), 18, 20, 24, 32, 40, 56. Display text uses Fraunces with
`font-optical-sizing: auto`. Numbers in tables use tabular figures (`font-variant-numeric: tabular-nums`).

## 3. Colour

Colours are tokens, authored in OKLCH and written as sRGB by `frontend/scripts/build-tokens.mjs` from
`frontend/src/design/tokens.json`; no component names a colour. The contrast gate (R-081) reads the same source.

| Token | Daylight | Lamp-lit | Role |
|---|---|---|---|
| `--c-bg` | #f9f5ee | #0c1117 | the page |
| `--c-surface` | #fefcf9 | #151a21 | raised panels, the label paper |
| `--c-sunken` | #f0e8de | #070a0f | trays, wells, fields |
| `--c-wood` | #e2cdba | #3a2a1f | cabinet and drawer fronts |
| `--c-ink` | #251c16 | #ede9e1 | text |
| `--c-ink-muted` | #5e554d | #b2aba1 | secondary text |
| `--c-rule` | #d1cbc4 | #323840 | decorative lines only |
| `--c-edge` | #867f77 | #6b727b | boundaries of controls (3:1 or more) |
| `--c-accent` | #8e5318 | #ebb25f | brass and lamp: links, the current place |
| `--c-focus` | #0056aa | #58ccff | the focus ring |
| `--c-stage` | #101213 | #050606 | the microscope stage |
| `--c-on-stage` | #edebe7 | #edebe7 | text and scale bars on the stage |
| `--c-good` / `--c-warn` / `--c-bad` | #206b38 / #915b00 / #ac312a | #76cf8a / #f0ba59 / #f47b74 | states |

Text contrast is at least 4.5:1 on `bg`, `surface` and `sunken` in both rooms (the lowest is `warn` on daylight
`sunken`, 4.68); `edge` is at least 3:1, as WCAG 2.2 SC 1.4.11 asks of component boundaries. `rule` never bounds a
control on its own.

**Collection hues.** Each of the 18 collections has a hue (`--h-<collection>`), 20° apart in OKLCH at one
lightness and chroma per room, assigned by meaning where one exists: plants green, fishes water-blue, crystals
ice-blue, fossils ochre, mammals blood-red, molluscs murex purple. Each reaches at least 5.2:1 on the daylight
surfaces and 8.6:1 on the lamp-lit ones, so it may colour text. Neighbouring hues are close (ΔE in OKLab about
0.03), so **a collection is never identified by its hue alone**: its icon and its name always accompany it.

## 4. Space, shape, depth

| Scale | Values |
|---|---|
| Spacing (`--s-*`) | 2, 4, 8, 12, 16, 24, 32, 48, 64, 96 px |
| Radii | 3 px controls, 6 px panels; a slide's glass corner is drawn to scale (about 0.5 mm) |
| Depth | `--lift` (a slide resting on a tray), `--float` (a panel over the page); in the lamp-lit room a faint lamp rim on the upper edge replaces the shadow |
| Physical size | 1 mm = 3.7795 px at the CSS reference; the slide object is drawn from its format in millimetres, and printed at exact size |

## 5. Motion

| Token | Value | For |
|---|---|---|
| `--t-quick` | 120 ms | press, hover, toggles |
| `--t-move` | 240 ms | panels, the label flip |
| `--t-travel` | 420 ms | the slide travelling from the drawer to the stage (View Transitions) |
| `--ease-out` | cubic-bezier(0.2, 0, 0, 1) | arriving |
| `--ease-in` | cubic-bezier(0.3, 0, 1, 1) | leaving |

Motion always means something: a slide moves because the visitor moved it. Nothing moves by itself or flashes.
Under `prefers-reduced-motion: reduce` every duration is 0 except opacity fades of at most 150 ms (R-085). Where the
View Transitions API is missing, the state changes at once.

## 6. Themes and languages

- The room follows the system's light or dark preference until the visitor chooses one; the choice is remembered on
  that device. The page is painted in the right room from the first frame.
- The interface speaks English and Spanish (neutral Spanish), following the browser's languages until the visitor
  chooses. Every string exists in both (R-089); plurals, dates, numbers and lists come from the platform's `Intl`.
  Scientific names, catalogue numbers and source texts are never translated.

## 7. Icons

The 186 icons of the collection tree (U7) come from one sprite; an icon takes the colour of its text
(`currentColor`) and is drawn at 16, 20, 24, 32 or 48 px. An icon that carries meaning has a text alternative (its
node's name in the page's language); one beside its own label is hidden from assistive technology.

## 8. Primitives and their states

Every primitive has these states, each visibly different: rest, hover, active (pressed), focus-visible (a 2 px ring
in `--c-focus` with a 2 px gap), disabled, busy, invalid. Targets are at least 24 by 24 px (WCAG 2.2 SC 2.5.8), 40 px
for primary actions.

| Primitive | Variants |
|---|---|
| Button | primary, secondary, quiet, danger; small, medium |
| Icon button | quiet, secondary; with a text label always given to assistive technology |
| Link | inline, standalone |
| Text field, search field, select | with label, hint and error text |
| Checkbox, radio, switch | with label |
| Chip | facet (toggle), removable |
| Collection tag | hue band, icon, name |
| Tabs | underline in the accent |
| Place trail | realm > cabinet > drawer > slide > stage |
| Tooltip, dialog, toast | dialog traps focus and returns it |
| Progress | determinate bar, indeterminate |
| Skeleton, empty state | |
| Theme switch, language switch | |

The specimen place (`/design`) shows every token and primitive in the current room and language; it is what the
screenshots and the gates look at until the places of U10 and U11 exist.
