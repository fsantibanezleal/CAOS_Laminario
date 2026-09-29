# U14 · The profile cabinet and printable label sheets · requirements

R-080, R-084, R-085 and R-089 are shared by the interface units, and U14 adds the cabinet to their gates. R-1401 to
R-1408 are this unit's own. The research is dossier 16 of the planning record.

```
R-080  THE interface SHALL show no horizontal page scroll at 360, 768, 1280 and 1920 px wide on every place, in both themes and both languages.
       Gate: frontend/gates/fit.mjs

R-084  WHEN a visitor clicks from the landing place, THE visitor SHALL reach every place (realm, cabinet, drawer, slide, stage, contribute, identify, profile, about) with the pointer only.
       Gate: frontend/gates/walk.mjs

R-085  WHILE prefers-reduced-motion is set, THE interface SHALL run no transition longer than 0 ms except opacity.
       Gate: frontend/gates/motion.mjs

R-089  EVERY interface string SHALL exist in EN and ES.
       Gate: frontend/scripts/check-i18n.mjs

R-1401  EVERY account SHALL have a public handle, unique and made from its display name, and THE profile SHALL be addressed by it and SHALL never show or send the account's email.
        Gate: tests/people/test_profile.py

R-1402  THE profile SHALL show the account's role, when it joined and was last active, its published slides by collection, its verified slides, and its identifications by category, counting nothing hidden.
        Gate: tests/people/test_profile.py

R-1403  THE cabinet SHALL list the account's published slides, by collection, and its current visible identifications with whether each names the community anchor now.
        Gate: tests/people/test_profile.py

R-1404  EVERY label stock SHALL be a record of its page, label size, columns, rows, margins and pitches with its source, and every label it places SHALL lie on the page and apart from the others.
        Gate: tests/labels/test_sheet.py::test_every_stock_places_its_labels

R-1405  WHEN a sheet is printed on a stock, EACH label's content SHALL lie inside its label, with the QR's quiet zone clear of text, from the chosen start position and printer offset.
        Gate: tests/labels/test_sheet.py

R-1406  WHEN a test page is printed at 100 %, EACH label outline SHALL measure its stock's label size and sit at its stock's position within 0.1 mm.
        Gate: tests/labels/test_sheet.py::test_the_test_page_measures_the_stock

R-1407  WHEN an account exports its own slides, THE file SHALL hold one row per slide with its exact place, and no one else SHALL export them with the exact place of an obscured or private slide.
        Gate: tests/people/test_export.py

R-1408  WHEN a visitor opens a contributor's cabinet from a slide and selects slides, THE page SHALL print their labels on a chosen stock and a test page for it.
        Gate: frontend/gates/cabinet.mjs
```
