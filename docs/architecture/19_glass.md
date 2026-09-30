# 19 · The glass-slide interface

![The glass slide as it is made and drawn (76 x 26 x 1 mm, frosted ends of 20 mm with the name on the left and the facts on the right, a coverslip over the icon, the specimen's image or none), and the four arrangements the visitor chooses: a carousel, a cabinet drawer, a slide box, a folder](svg/glass.svg)

The interface is a set of glass slides. Every set of the collection (a realm's collections, a collection's drawers, a
drawer's groups and its slides, a search's results, the Identify queue) is drawn as realistic glass slides in a 3D
scene, in the arrangement the visitor chooses; every box of a place (a panel, a card, a dialog, a menu, a form, an
empty state) is a glass plate with its frosted end. This is Felipe's amendment of 2026-09-30, the reading of his
first request ("the app go around microscope slides") that the cabinet fronts of U10 missed. The requirements are
R-1701 to R-1708 ([U17 requirements](../design/features/u17-glass/requirements.md)); the research is the management
repository's dossier 18.

## 1. The object

| Part | As made | Source | As drawn |
|---|---|---|---|
| Glass | about 76 x 26 mm, 1 mm (+/- 0.05 mm) thick, soda-lime glass | ISO 8037-1; Marienfeld's slides (DIN ISO 8037-1) | a box of the slide's own format, 1 mm thick |
| Marking end | a frosted area of about 20 mm | Marienfeld ("silky frosted marking area of approx. 20 mm") | both ends frosted: the name, typed in the label face, on the left; the facts on the right; the collection's band along the top |
| Coverslip | design thickness 0.17 mm, length and width within +/- 0.5 mm | ISO 8255-1:2017, clauses 4.2 and 4.3 | 22 mm square (never wider than the space between the ends), 0.17 mm thick |
| Sample | the specimen, under the coverslip | | the node's icon, or the specimen's image; a slide whose glass was photographed is that photograph |

The glass is one physically based material for every slide and coverslip of a set (three.js `MeshPhysicalMaterial`):
transmission 1, thickness 1 mm, index of refraction 1.5, a faint green attenuation colour (the tint soda-lime glass
shows through its edge), a clear coat. Transmission costs the renderer one extra pass per frame, shared by every
transmissive object: the opaque scene is drawn into a texture that all the glass samples, so a drawer of 40 slides
costs about what 4 do. Things under the glass must be opaque to be seen through it: the icon is a cut-out (alpha
test), not a transparent picture, or the coverslip, drawn after the transparent objects' depth, would hide it. The
labels are drawn on canvases in the page's own faces (the self-hosted woff2 files, which a WebGL text renderer cannot
read), after the fonts have loaded. Every set stands on the page's own surface, the scene's background and table in
the room's colour, so the glass refracts the page, and each slide casts a soft shadow that follows it.

**Real glass.** 15 base slides have a photograph of their whole glass (`slide_overview`), and 13 of the 14 whole-slide
scans keep the scanner's macro photograph of the whole slide in their file. A job, `extract_overview`, stores that
photograph as the slide's overview beside the scan, credited as the scan, without processing the scan again; it is
queued after a scan's processing, and the bake queues it for the scans already baked (R-1707). The summary of a slide
names it (`glass_photo_url`), and the slide is then drawn as its photograph. The other 477 base slides are drawn glass
with their micro image under the coverslip.

**The slide's own place** shows the slide as the same glass slide, seen close: its photograph when its glass was
photographed, else its first micro image under the coverslip, its label's name and catalogue number on the left end,
and on the right its preparation, place and date with the QR the server draws for it (the one path of the drawing's
`lam-qr`, typed in with the ink of the label, on its quiet zone). A drag tilts it within a few degrees, as a slide is
turned in the hand, and it springs back; under reduced motion it stays still. The server's drawing stays where it
reads best: without WebGL, while the 3D code loads, and in "Read the label", where the QR is read at size.

## 2. The arrangements

The visitor chooses how every set of the page is laid out; the choice is kept on the device (R-1704). Each is a real
way slides are kept, drawn at the scene's scale of 1 unit = 1 mm.

| Arrangement | As kept | Source | As drawn |
|---|---|---|---|
| Carousel | (a way to leaf through a set) | | the slides stand round a ring, leaning back 7 degrees; the ring turns the chosen slide to the front |
| Cabinet drawer | steel filing cabinets, slides on edge in drawers of 465 (14 drawers to a 25 mm section) held by backstops | Sakura Finetek, Tissue-Tek Lab Aid | a steel cabinet with the drawer pulled out, its label holder naming the set; slides stand one behind the other and the chosen one rises 30 mm to show its label |
| Slide box | 100 grooved, numbered slots, a hinged lid with an inventory sheet | Heathrow Scientific | two rows of slots, the lid open with the set's name on its sheet |
| Folder | 20 flat, numbered recesses, a cover that folds under | Globe Scientific | two columns of ten numbered recesses; the page holding the chosen slide |

The carousel keeps neighbours from touching: with $n$ slides the angular step and the ring's radius are

$$s = \min\left(\frac{2\pi}{n},\ 0.62\right), \qquad R = \max\left(80,\ \frac{43}{\sin(s/2)}\right),$$

so the chord between two neighbours, $2R\sin(s/2)$, is at least 86 mm for slides 76 mm long. Slide $i$ of a set whose
chosen slide is $c$ stands at the angle $a_i = (i - c)\,s$, at $(R\sin a_i,\ 0,\ R\cos a_i - R)$, turned by $a_i$; the
far side of the ring is not drawn. In a drawer the slides are drawn 7 mm apart (real slots are about 3 mm), so the top
strip of each one shows above the one in front, where a hand would find it.

## 3. Reaching the slides

The scene answers the pointer itself: a click chooses a slide, a click on the chosen slide opens it, a drag turns the
carousel. Over the scene, an accessible layer follows the W3C carousel pattern (R-1705): the set is a labelled group
of slides; previous and next buttons move the chosen slide without moving the focus; the arrow keys, Home, End and
Page Up and Down move it from the keyboard; Enter opens it; a ring on the stage shows the focused slide. Every slide of
the layer is a real link, and the scene writes on it where the slide lies on the stage, so a gate (or any tool) reaches
the same slide the eye sees. The chosen slide's name, facts and an Open link are written under the stage. Nothing
turns by itself; under reduced motion the scene cuts to each placement (R-1706); the scene draws only when something
changes, so a hidden tab draws nothing.

Where the device draws no WebGL, or is set to draw flat (the gates set it to measure proportions), the same slides are
drawn flat, as glass slides at one scale for the set (R-1708, R-1007). The 3D code is its own chunk, loaded by the
places that show a set: 1,003 KB (271 KB compressed) beside the 350 KB of the app.

## 4. The glass of every box

Every box of a place is a glass plate: clear glass that lets the room show through, a bright bevel with the green of
the glass inside it, a soft shadow, and a frosted band along its top end in the box's hue (R-1702). The two surface
tokens (`--glass-bg`, `--glass-shadow`) are defined for each room in `glass/surface.css`; a panel that names what it
holds (a drawer's description, the filters, an empty state) is a `GlassPanel`, its frosted end at the left with the
band, the icon and the title, as a slide's label names it (at the top on a narrow screen). Where a box carried a
meaning in its border (a warning, a verified slide), that tone is the band's hue.

## 5. How it is verified

| Gate | Checks |
|---|---|
| `frontend/src/glass/model.test.ts` | the coverslip between the ends; the carousel's neighbours never touch at any size; the chosen slide in front; the drawer's order and lift; the box's two rows; the folder's pages of 20; the keys |
| `frontend/src/glass/items.test.ts` | a node's icon, name, counts and hue; an empty drawer; a slide's image, italic name, facts and format; a photographed slide drawn as its photograph (R-1703) |
| `tests/worker/test_processing.py` | the scanner's macro photograph stored as the overview, once, credited as the scan, offered by the summary (R-1707) |
| `frontend/gates/glass.mjs` | every set drawn in 3D and placed, as many as the place holds; no box and no cabinet front left; an arrangement for every set, kept after a reload; the carousel pattern; the cut under reduced motion; the flat drawing (R-1701, R-1702, R-1704, R-1705, R-1706, R-1708) |
| `frontend/gates/walk.mjs` | the landing, a collection, a drawer and a slide reached by pointer through the scene; R-1007 on the flat drawing |
| `frontend/gates/glass-look.mjs` | screenshots of every arrangement of the landing, a collection and a drawer, both rooms, a desktop and a phone width, for review |

## References

- ISO 8037-1:1986, Optics and optical instruments, Microscopes, Slides, Part 1: Dimensions, optical properties and
  marking. [iso.org/standard/15048](https://www.iso.org/standard/15048.html).
- ISO 8255-1:2017, Microscopes, Cover glasses, Part 1: Dimensional tolerances, thickness and optical properties.
  [iso.org/standard/72610](https://www.iso.org/standard/72610.html).
- Paul Marienfeld, Microscope slides, thickness approx. 1 mm.
  [marienfeld-superior.com](https://www.marienfeld-superior.com/microscope-slides-thickness-approx-1-mm.html).
- Sakura Finetek, Tissue-Tek Lab Aid filing cabinet system.
  [sakuraus.com](https://www.sakuraus.com/Products/Filing-Systems/Tissue-Tek-Lab-Aid-Slide-Filing-System.html).
- Heathrow Scientific, 100-place microscope slide box.
  [heathrowscientific.com](https://www.heathrowscientific.com/100-place-microscope-slide-box/).
- Globe Scientific, cardboard slide mailers and folders.
  [globescientific.com](https://www.globescientific.com/cardboard-slide-mailers.html).
- three.js, `MeshPhysicalMaterial` and `WebGLRenderer` (the transmission pass), release 0.186.
  [github.com/mrdoob/three.js](https://github.com/mrdoob/three.js).
- W3C WAI-ARIA Authoring Practices, Carousel pattern.
  [w3.org/WAI/ARIA/apg/patterns/carousel](https://www.w3.org/WAI/ARIA/apg/patterns/carousel/).
