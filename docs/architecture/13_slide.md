# 13 · The slide and the stage

![The slide and the stage: the API computes one layout of the slide in millimetres from its record and draws it as SVG for the page and as a PDF sheet for print, with the QR from segno in both; the slide place inlines the SVG in the room's colours and lists the stage items; the stage opens OpenSeadragon over the IIIF image with objectives from the pixel size, a scale bar, planes, polarisers and Annotorious annotations stored through the API; gates decode the QR, measure the print, the scale bar and the stage](svg/slide-stage.svg)

A slide has an address, `/s/<short id>`, which its QR encodes (dossier 05, section 3); its images are looked at on
the stage, `/s/<short id>/stage/<asset>`. The research, with every measurement, is dossier 13 of the planning
record; the requirements are R-082, R-083, R-086 and R-1101 to R-1108 ([U11 requirements](../design/features/u11-slide/requirements.md)).

## 1. The slide place

At the top the slide as an object, drawn from its record; under it what can be done with it: print its labels at
1:1, read the label (the drawn label large, beside the scanner's photograph of the real one when the source has it),
download the drawing, open the IIIF manifest. Then the stage items (section 5), the photographs, the record (name
with its rank in the reader's language, host, type status, preparation, where and when it was collected and
prepared, catalogue number, format, coverslip, drawer, the quality checks) and where every image came from: source
and record, author or rights holder, licence, retrieval date, and the SHA-256 of the file each image was made from
(the source's for the base collection, the verified upload's for a contribution: R-1107, R-1208). On a
phone the provenance table becomes one block per image, each field with its name.

## 2. One layout for the screen and for print

`app/labels/layout.py` computes the slide as primitives in millimetres, from its top-left corner, the long side
across (R-1101). With $L$ and $S$ the format's long and short sides:

- the frosted label end is $L_w = 20$ mm when $L \ge 70$ mm (ISO 8037-1's marking end), else $0.3\,L$;
- the coverslip keeps its recorded size (clamped to the glass) and is centred between the labels,
  $x_c = \dfrac{L_w + (L - R_w)}{2}$, where $R_w$ is the data label's width, or 0;
- the data label exists when the glass beside the coverslip is wide enough, $\dfrac{L - L_w - C}{2} - 1 \ge 15$ mm
  for a coverslip of long side $C$, and is then $R_w = \min(20, \dfrac{L - L_w - C}{2} - 1)$ mm wide.

Text is Courier Prime, whose advance is 0.6 em for every character, so a line of text of size $s$ in a label of
width $w$ holds exactly $\lfloor (w - 2) / (0.6\,s) \rfloor$ characters and the server wraps it; the catalogue number
and the name are set at 5.5 pt, the data at 5 pt (1 pt = 25.4 / 72 mm). A word longer than a line breaks with a
hyphen; a catalogue number breaks between its letters and its digits. What does not fit ends with an ellipsis: the
record on the page has everything. The name's epithets are italic and its authorship roman; the date is written the
collections' way (31.VIII.1962), the collector as `leg.`, the preparer as `prep.`, a type status in red capitals.

The QR takes a square of side $q$ at the bottom of the frosted end, quiet zone included: 14 mm, or down to 12 mm when
there is no data label and its lines must follow the name. For a symbol of $n$ modules,

$$m = \dfrac{q}{n + 8}, \qquad \mathrm{QR}_{\mathrm{side}} = n \cdot m,$$

so the four modules of paper on every side are inside the label, and no text may enter them (R-1102, checked on the
layout). For Laminario's address $n = 29$ and $m = 0.378$ mm at 14 mm.

The mount window shows the slide's overview photograph, else the specimen's macro, else the first micro image, inside
the coverslip (or the glass between the labels), never stretched; a photograph whose orientation differs from the
window's (a slide photographed standing) is turned a quarter to lie with the slide.

**Two renderers.** `svg.py` draws the layout with class names; the slide place inlines it, so the paper, the glass,
the collection's hue and the inks come from the room's tokens (the labels are paper in both rooms: daylight paper, or
paper under the lamp, so the QR stays dark on light). Served on its own it carries the daylight colours. `pdf.py` draws
the labels on an A4 sheet at 72 / 25.4 points per millimetre with Courier Prime embedded (the TrueType subset built
from the same pinned files as the web faces): the slide's outline at its format's size so a print at 100 % can be
checked with a ruler, the labels as cut lines to print on label paper and stick on the physical slide, the
coverslip's place dotted, a cut mark at each corner, and under it the permalink and the size the outline must
measure. The print is reproducible: the same slide gives the same bytes. The QR's modules are one filled path, since
separate fills leave anti-aliased seams between rows.

## 3. The QR

The payload is the permalink in upper case, `HTTPS://LAMINARIO.ML.FASL-WORK.COM/S/<SHORT ID>`, in alphanumeric mode
at error correction M: version 3, 29 x 29 modules (segno 1.6.6). The alphanumeric mode has no lower-case letters, and
the same address in lower case needs byte mode and version 4; host names are case-insensitive and the server reads a
short id in any case, so the upper-case address opens the slide (R-1103). The SVG and the PDF draw the same matrix.

## 4. Plain images

A photograph or a height map is stored as a JPEG under a content-addressed key, and its address is `/media/<key>`. The
API serves it for a ready image of a published slide, with the check the IIIF tiles have, cached for a year since a
key never changes; nginx passes `/media/` to the API and keeps a copy. The route was missing until the slide place
first drew photographs (finding F-039).

## 5. The stage

`frontend/src/slide/assets.ts` groups a slide's ready micro images as the microscope sees them: a focal stack (its
planes by index, named by depth, with the all-in-focus composites and the height map), a polarised pair
(plane-polarised and crossed polars of one field), or a single field. Each is addressed by its first image.

The viewer is OpenSeadragon 6.1.1 over the image's IIIF `info.json` (or the plain image), loaded only on the stage.

**Objectives.** Scanner files pair an objective with a pixel size whose product is close to 10 um (CMU-1: 20x at
0.499 um; the NMNH ostracod: 40x at 0.229 um), so at objective $M$ a screen pixel covers $10/M$ um and an image
whose pixel covers $p$ um is shown at

$$z = \dfrac{p \cdot M}{10}$$

screen pixels per image pixel. The turret offers 2x to 100x; a step with $z > 1$ shows the screen finer than the
image and is labelled digital zoom; an image without a pixel size offers free zoom only and says it is not to scale
(R-1104). The readout shows the objective the current zoom corresponds to.

**The scale bar** is recomputed on every change of the view: with $u = p / z$ um per screen pixel and a viewer $W$
pixels wide, it is the longest length $\ell$ of the 1-2-5 series (in um, or mm from 1000 um) with $\ell / u \le W/4$,
drawn $\ell / u$ pixels long (R-086).

**Planes** are separate IIIF images of one size: the next plane is added on top and the one below leaves once the
new one is fully drawn, so the view never goes blank and never moves (R-1105). **Polarisers**: both images of a pair
are open; the toggle fades one over the other in 240 ms (at once under reduced motion), and rotation turns the view in
quarter turns, shown in degrees (R-1106).

**Annotations** are W3C Web Annotations on one image (R-1108). Annotorious 3.9.3 draws rectangles and polygons; the
comment is asked in the stage's own dialog and saved through `POST /api/slides/<id>/assets/<asset>/annotations`; the
list beside the viewer is the keyboard and screen-reader way to them. The server stores the bodies (text only) and the
selector (a `xywh=pixel:` rectangle, or an SVG with one polygon of numbers and nothing else), and sets the rest: the
id, the target source (the image's own IIIF id, whatever the client sent), the creator and the dates. Anyone reads
them; a signed-in account adds them (the `annotate` capability); the author or a curator removes one.
`GET /api/session` tells the page whether someone is signed in, with a 200 either way.

## 6. Gates and tests

| Gate | Checks |
|---|---|
| `tests/labels/test_layout.py` | every format at its size, the coverslip centred, the label end's width, the assumed format said in words (R-1101); the quiet zone kept, the label's contents, text within its label, hyphenation, dates, a photograph turned (R-1102) |
| `tests/labels/test_qr.py` | version 3, alphanumeric; the SVG and the PDF draw the same modules (R-1103) |
| `tests/labels/test_print.py` | the outline measures the format within 0.1 mm on A4 (R-083); the face embedded; the print reproducible |
| `tests/labels/test_endpoints.py`, `tests/delivery/test_media.py` | the drawing and the sheet over HTTP; plain images for published slides only |
| `tests/annotations/test_annotations.py` | reading, adding, removing, the server's target, only text and plain shapes (R-1108) |
| `frontend/src/stage/optics.test.ts`, `frontend/src/slide/assets.test.ts` | the turret, digital zoom, the scale bar within 1 percent at every step; the stage items |
| `frontend/gates/qr.mjs` | the label's QR, screenshotted at its on-screen size in both rooms at two widths, decodes to the permalink (R-082) |
| `frontend/gates/walk.mjs` | the slide and its stage reached by pointer (R-084), every image's provenance shown (R-1107) |
| `frontend/gates/scalebar.mjs`, `stage.mjs` | the bar against the viewer's own zoom at every objective (R-086); planes aligned and named, polarisers on one field, rotation (R-1105, R-1106); both need the tile server |
