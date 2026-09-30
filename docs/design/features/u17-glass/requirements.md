# U17 · The glass-slide interface · requirements

From Felipe's amendment of 2026-09-30: the realistic glass slide is the base container of the whole interface, the app
is navigated as sets of glass slides, in 3D, realistic, in the arrangement the visitor chooses, never a flat grid; a
slide shows the photograph of its own glass where one exists, and a drawn glass slide with its icon otherwise (the
management repository's `wip/laminario/00`, readings A1 to A10; research in dossier 18). The shared interface
requirements (R-080, R-084, R-085, R-089) and R-1007 keep binding; R-1701 to R-1708 are this unit's own.

```
R-1701  THE interface SHALL show every set of the collection (a realm's collections, a collection's drawers, a drawer's groups and slides, a search's results, the Identify queue) as glass slides in a 3D scene, each reached by pointer on the stage.
        Gate: frontend/gates/glass.mjs

R-1702  EVERY box of a place (a panel, a card, a dialog, a menu, a form, an empty state) SHALL be drawn as a glass plate with its frosted end, and no cabinet front, drawer front or plain box SHALL remain.
        Gate: frontend/gates/glass.mjs

R-1703  A glass slide SHALL be drawn as the object is made: 76 x 26 x 1 mm soda-lime glass (refractive index 1.5) at its own format, frosted ends of 20 mm with the name on the left end and the facts on the right, a 0.17 mm coverslip over the node's icon or the specimen's image; a slide whose glass was photographed SHALL be shown as that photograph.
        Gate: frontend/src/glass/items.test.ts

R-1704  WHEN the visitor chooses an arrangement (a carousel, a cabinet drawer, a slide box, a folder), EVERY set of the page SHALL show it and the choice SHALL be kept on this device.
        Gate: frontend/gates/glass.mjs

R-1705  THE sets SHALL follow the W3C carousel pattern: a labelled group of slides, previous and next buttons that do not move the focus, the arrow keys, Home and End to move, Enter to open, a ring around the focused slide on the stage; nothing SHALL turn by itself.
        Gate: frontend/gates/glass.mjs

R-1706  WHILE prefers-reduced-motion is set, THE scene SHALL cut to each new placement instead of moving.
        Gate: frontend/gates/glass.mjs

R-1707  WHEN a whole-slide scan is processed, THE scanner's macro photograph of the whole slide SHALL be stored as the slide's overview, credited as the scan, without processing the scan again.
        Gate: tests/worker/test_processing.py

R-1708  WHERE the device draws no WebGL (or is set to draw flat), THE slides SHALL be drawn flat as glass slides, at one scale for the set, never as boxes.
        Gate: frontend/gates/glass.mjs
```
