# U17 · The glass-slide interface · design

How the parts fit is the wiki page [19 The glass-slide interface](../../../architecture/19_glass.md); the reasons are
Felipe's amendment of 2026-09-30 and the management repository's dossier 18.

## What the unit delivers

| Part | Where |
|---|---|
| The glass slide's model: the object's dimensions, the four arrangements' layouts, the keys | `frontend/src/glass/model.ts` |
| The 3D scene: the glass, the labels, the coverslip, the photographed slides, the cabinet, the box, the folder, the shadows, the camera, where each slide lies on the stage | `frontend/src/glass/GlassScene.tsx`, `textures.ts` |
| A set in the page: the arrangement's choice, the stage, the caption, the accessible layer, the flat drawing | `frontend/src/glass/GlassSet.tsx`, `FlatGlassSlide.tsx` |
| Glass slides from the tree's nodes and the slides' summaries | `frontend/src/glass/items.ts` |
| Text on glass: the panel and the surface every box takes | `frontend/src/glass/GlassPanel.tsx`, `surface.css` |
| The scanner's macro photograph kept as the slide's overview; `glass_photo_url` in the summary | `app/jobs/kinds.py` (`extract_overview`), `app/services/catalog.py`, `app/base/bake.py` |
| The glass gate, the screenshots, the walk through the scene | `frontend/gates/glass.mjs`, `glass-look.mjs`, `walk.mjs`, `lib/glass.mjs` |

## Decisions

- **One object for everything.** Realms, collections, drawers, groups and specimen slides are the same glass slide;
  only what lies under the coverslip changes (an icon, an image, or the photograph that replaces the drawing). Panels
  are the same glass drawn flat, with the frosted end holding their title.
- **WebGL through three.js and @react-three/fiber** (three 0.186.1, fiber 9.8.1, drei 10.7.9, MIT): real refraction,
  Fresnel reflection and thickness need a renderer; CSS draws a picture of glass. One material for all the glass keeps
  one transmission pass per frame. The scene draws on demand; the 3D code is a chunk of its own.
- **Labels on canvases, in the page's faces.** The label face is a self-hosted woff2 file, which WebGL text renderers
  cannot parse; a canvas uses the page's loaded fonts, so the scene's labels are typed like the page's.
- **The page's surface, not a studio.** The scene's background and table are the room's colour and each slide casts
  its own soft shadow: the set lies on the page. A studio floor and drei's contact shadows were tried and dropped: the
  grey floor read as a test scene and the contact shadow darkened the whole table.
- **The arrangements are real ways of keeping slides**, drawn from their makers' figures (a filing cabinet's drawer, a
  100-place box, a 20-place folder), plus the carousel Felipe asked for; the choice is the visitor's and is kept on
  the device. None is a flat grid.
- **Reached as a visitor reaches it.** The scene's own hit test answers the pointer; the accessible layer is real links
  with the slide's place on the stage written on them, so the keyboard, a screen reader and the gates reach the same
  slide.
- **Flat where WebGL is missing**, or when the device is set to draw flat: still glass slides, at one scale.
- **Lists with a control on each slide** (the profile's label-sheet selection, a person's identifications) keep their
  layout with flat glass slides: a checkbox belongs under the slide it picks.
