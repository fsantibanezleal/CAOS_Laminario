# U10 · Explore · requirements

R-080, R-084, R-085 and R-089 are from the design document, shared by the interface units U9 to U15; U10 adds its
places (the realms, a cabinet, a drawer, search and the map) to their gates, and R-084's walk reaches the places
built so far (the slide, stage, contribute, identify, profile and about places join it with U11 to U15).
R-1001 to R-1009 are this unit's own.

```
R-080  THE interface SHALL show no horizontal page scroll at 360, 768, 1280 and 1920 px wide on every place, in both themes and both languages.
       Gate: frontend/gates/fit.mjs

R-084  WHEN a visitor clicks from the landing place, THE visitor SHALL reach every place (realm, cabinet, drawer, slide, stage, contribute, identify, profile, about) with the pointer only.
       Gate: frontend/gates/walk.mjs

R-085  WHILE prefers-reduced-motion is set, THE interface SHALL run no transition longer than 0 ms except opacity.
       Gate: frontend/gates/motion.mjs

R-089  EVERY interface string SHALL exist in EN and ES.
       Gate: frontend/scripts/check-i18n.mjs

R-1001  THE slide list SHALL narrow published slides by node, anchor kind, preparation, modality, preservation, country, licence family, whole-slide and origin, and THE count beside a facet value SHALL leave that facet's own filter out.
        Gate: tests/explore/test_explore.py::test_filters_and_facet_counts

R-1002  WHEN a visitor searches, THE search SHALL match names in English or Spanish with or without accents, word prefixes, catalogue numbers and short ids, including slides older than the index and slides loaded from a bake, and SHALL never read the visitor's text as query syntax.
        Gate: tests/explore/test_explore.py::test_search

R-1003  THE map SHALL show an obscured slide only at its public point inside its 0.2 degree cell, and SHALL never show the point of a private slide.
        Gate: tests/explore/test_explore.py::test_map_after_geoprivacy

R-1004  WHEN a specimen states a country and coordinates, THE submission SHALL be refused unless the point lies in that country or within 0.25 degree of its edge, and WHEN it gives coordinates only, THE slide SHALL carry the country they lie in.
        Gate: tests/collections/test_places.py

R-1005  THE country vocabulary and shapes SHALL be the exact rebuild of their pinned sources, and THE basemap SHALL be the extract whose SHA-256 is recorded.
        Gate: scripts/build_countries.py

R-1006  WHEN a place is opened from its address, THE interface SHALL show the same place, filters and results as when it was reached by clicking, and after every navigation THE focus SHALL be on the new place's heading.
        Gate: frontend/gates/walk.mjs

R-1007  THE drawer SHALL draw every slide at its format's proportion within 1 percent, at one scale for every format, with the label end first.
        Gate: frontend/gates/walk.mjs

R-1008  THE basemap SHALL be read with byte ranges, and WHEN it is missing THE map SHALL still draw the countries and the points.
        Gate: tests/explore/test_basemap.py

R-1009  A base slide SHALL carry a country only where its source states one, as a code of the country vocabulary, and a change of a base slide's record SHALL reach the bake and the import without processing its images again.
        Gate: tests/base/test_countries.py
```
