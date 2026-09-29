# U11 · The slide place and the stage · requirements

R-082, R-083 and R-086 are from the design document and are this unit's; R-080, R-084, R-085 and R-089 are shared by
the interface units, and U11 adds the slide and the stage places to their gates. R-1101 to R-1108 are this unit's own.

```
R-080  THE interface SHALL show no horizontal page scroll at 360, 768, 1280 and 1920 px wide on every place, in both themes and both languages.
       Gate: frontend/gates/fit.mjs

R-082  WHEN the rendered slide label is screenshotted, decoding its QR SHALL return exactly the slide permalink.
       Gate: frontend/gates/qr.mjs

R-083  WHEN a label is printed, THE printed slide SHALL measure the format size within 0.1 mm.
       Gate: tests/labels/test_print.py::test_print_dimensions

R-084  WHEN a visitor clicks from the landing place, THE visitor SHALL reach every place (realm, cabinet, drawer, slide, stage, contribute, identify, profile, about) with the pointer only.
       Gate: frontend/gates/walk.mjs

R-085  WHILE prefers-reduced-motion is set, THE interface SHALL run no transition longer than 0 ms except opacity.
       Gate: frontend/gates/motion.mjs

R-086  WHEN a micro asset has a pixel size, THE stage viewer SHALL show a scale bar whose length matches the physical distance within 1 percent at every objective step.
       Gate: frontend/gates/scalebar.mjs

R-089  EVERY interface string SHALL exist in EN and ES.
       Gate: frontend/scripts/check-i18n.mjs

R-1101  THE slide object SHALL be drawn from one layout in millimetres for the screen and for print: the slide at its format, the coverslip at its recorded size centred on the glass, the label end at its format's width, and WHEN the format is assumed THE drawing SHALL say so in words.
        Gate: tests/labels/test_layout.py

R-1102  THE label SHALL carry the catalogue number (or the short id), the name with its epithets in italic and its authorship roman, the collection's hue band and the QR, and no text SHALL enter the QR's quiet zone of four modules.
        Gate: tests/labels/test_layout.py::test_quiet_zone_and_contents

R-1103  THE QR SHALL encode the permalink in upper case in alphanumeric mode, and a slide's QR SHALL be the same in the SVG and in the PDF.
        Gate: tests/labels/test_qr.py

R-1104  THE stage SHALL offer as objectives only the steps whose screen pixel is no finer than the image's own pixel, SHALL label finer steps as digital zoom, and WHEN an asset has no pixel size THE stage SHALL offer no objective and no scale bar and SHALL say the image is not to scale.
        Gate: frontend/src/stage/optics.test.ts

R-1105  WHEN a focal stack is on the stage, THE planes SHALL stay aligned when the visitor changes plane, and THE plane control SHALL name each plane by its depth in micrometres.
        Gate: frontend/gates/stage.mjs

R-1106  WHEN a polarised pair is on the stage, THE toggle SHALL switch between plane-polarised and crossed polars on the same field, and THE rotation SHALL be shown in degrees.
        Gate: frontend/gates/stage.mjs

R-1107  THE slide place SHALL show for every asset its source, record, creator or rights holder, licence and retrieval date, and for a base slide its SHA-256.
        Gate: frontend/gates/walk.mjs

R-1108  AN annotation SHALL be stored as a W3C Web Annotation on one asset, SHALL be created only by a signed-in account and removed only by its author or a curator, and SHALL be shown to every visitor.
        Gate: tests/annotations/test_annotations.py
```
