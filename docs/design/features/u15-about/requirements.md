# U15 · About the collection · requirements

R-080, R-084, R-085 and R-089 are shared by the interface units, and U15 adds the About place to their gates. R-1501
to R-1507 are this unit's own. The research is dossier 17 of the planning record.

```
R-080  THE interface SHALL show no horizontal page scroll at 360, 768, 1280 and 1920 px wide on every place, in both themes and both languages.
       Gate: frontend/gates/fit.mjs

R-084  WHEN a visitor clicks from the landing place, THE visitor SHALL reach every place (realm, cabinet, drawer, slide, stage, contribute, identify, profile, about) with the pointer only.
       Gate: frontend/gates/walk.mjs

R-085  WHILE prefers-reduced-motion is set, THE interface SHALL run no transition longer than 0 ms except opacity.
       Gate: frontend/gates/motion.mjs

R-089  EVERY interface string SHALL exist in EN and ES.
       Gate: frontend/scripts/check-i18n.mjs

R-1501  THE About place SHALL show the collection's numbers (published slides in total, by realm and by origin, whole-slide scans, images, countries, contributors) as the database counts them when the page is read.
        Gate: tests/about/test_about.py

R-1502  EVERY source and EVERY licence of the published slides' images SHALL appear in the About answer with its count of images, and EVERY source and EVERY licence the policy accepts SHALL be described in EN and ES.
        Gate: tests/about/test_about.py

R-1503  WHEN a visitor reads a slide, THE slide place SHALL give the slide's citation and, for each image, its title, author, source, licence with a link to it, and that the image served is adapted from the original.
        Gate: frontend/gates/about.mjs

R-1504  THE About place SHALL explain how an image becomes a stage (the pyramid, the tiles, the pixel size and the objectives, focal stacks and their fusion, polarised pairs), with figures in the room's colours and the equations typeset, in EN and ES.
        Gate: frontend/gates/about.mjs

R-1505  EVERY external link the About place shows SHALL answer, or be listed as not checkable by a machine, when the links are checked.
        Gate: frontend/gates/links.mjs

R-1506  THE map SHALL credit OpenStreetMap with a link to its copyright page.
        Gate: frontend/gates/about.mjs

R-1507  THE About place SHALL name the vocabularies the tree is built on, the software and the fonts, each with its licence and, where one exists, its citation.
        Gate: frontend/src/about/content.test.ts
```
