# U11 · The slide place and the stage · design

The research is dossier 13 of the planning record (and dossier 05, sections 2 to 4). How the parts fit together is the
wiki page [13 The slide and the stage](../../../architecture/13_slide.md). This page records the unit's decisions.

## What the unit delivers

| Part | Where |
|---|---|
| The slide's layout in millimetres, one for the screen and for print | `app/labels/layout.py` |
| The layout as SVG (inlined by the page) and as a PDF sheet at 1:1 with cut marks | `app/labels/svg.py`, `app/labels/pdf.py`, `GET /api/slides/{id}/slide.svg`, `GET /api/slides/{id}/label.pdf` |
| The QR's module matrix | `app/labels/qr.py` (segno 1.6.6, BSD-3-Clause) |
| Courier Prime as TrueType for the PDF, from the same pinned subset as the web faces | `scripts/build_fonts.py`, `app/labels/fonts/` |
| Annotations: W3C Web Annotations per asset, with their API and permissions | `app/db/migrations/versions/0009_annotations.py`, `app/services/annotations.py`, `app/routers/annotations.py` |
| The slide place and the stage place | `frontend/src/places/slide/`, `frontend/src/places/stage/`, `frontend/src/stage/` |
| The gates: QR decode, scale bar, stage, and the walk and fit over the new places | `frontend/gates/qr.mjs`, `scalebar.mjs`, `stage.mjs`, `walk.mjs`, `fit.mjs` |

## Decisions

- **One layout, two renderers.** The server computes the slide as primitives in millimetres (the glass, the mount
  window, the coverslip, the labels, text runs, the QR's modules) and renders them as SVG for the screen and as PDF
  for print. The page inlines the SVG (so it takes the room's colours and the page's faces); the PDF embeds Courier
  Prime and draws at 72 / 25.4 points per millimetre. The QR is drawn from the same matrix in both (R-1103).
- **Two labels when the slide has room, as museums do.** A 14 mm QR on a 20 x 26 mm frosted end leaves room for the
  catalogue number and the name, set at 5.5 pt: Courier Prime's advance is 0.6 em, so a line holds 15 characters and
  the server wraps exactly. The data label (preparation and stain, locality and country, date, collector) goes on the
  other end when the space beside the coverslip is at least 15 mm wide, as on NHM and NMNH slides; otherwise its
  lines follow the name on the frosted end, and the QR shrinks to no less than 12 mm (0.41 mm a module).
- **The quiet zone is paper.** The QR keeps four modules of white around it, inside the label; no text may enter it
  (R-1102), checked on the layout, not by eye.
- **The mount window shows the slide as it is.** The slide's overview photograph when it has one, else the specimen's
  macro, else the first micro asset's thumbnail, drawn inside the coverslip (or, without a coverslip, the glass
  between the labels) with `preserveAspectRatio` meet, never stretched.
- **Objectives mean what a microscopist expects.** Scanner files pair an objective with a pixel size whose product is
  close to 10 um (CMU-1: 20x at 0.499 um; the NMNH ostracod: 40x at 0.229 um), so at objective M one screen pixel
  covers 10 / M um. The turret offers 2x, 4x, 10x, 20x, 40x and 100x; a step whose screen pixel is finer than the
  image's own pixel is labelled digital zoom (R-1104). An asset without a pixel size offers free zoom only, says "not
  to scale", and draws no scale bar.
- **The scale bar is computed, not drawn once.** On every zoom the stage takes the viewport's image-to-screen ratio,
  multiplies by the pixel size, and picks the largest length of the 1-2-5 series (in um or mm) that fits a quarter of
  the viewer's width; the gate measures it against the physical distance at every objective (R-086).
- **Planes are separate images kept aligned.** A focal stack's planes are separate IIIF images of the same size
  (one pyramid per plane, U2), opened as one OpenSeadragon world with one visible at a time; changing plane keeps the
  viewport, so nothing moves but the focus (R-1105). The all-in-focus composite and the height map are the stack's
  last two entries.
- **Polarised pairs cross-fade.** PPL and XPL are two aligned images; the toggle fades one over the other (at once
  under reduced motion), and rotation turns the view, not the image, with the angle shown (R-1106).
- **Annotations are Web Annotations, stored as the standard writes them.** One table row per annotation holds the
  W3C JSON (body and target with a selector on the asset's IIIF image), its author and dates; Annotorious 3.9.3
  draws and edits them on the stage; a visitor sees them, a signed-in account adds them, and only the author or a
  curator removes one (R-1108).
