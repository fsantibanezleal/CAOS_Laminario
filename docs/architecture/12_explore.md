# 12 · Explore

![Explore: an address names a place; the places draw from the tree fetched once and from the Explore endpoints; the endpoints narrow published slides by filters and FTS5 search, count facets without their own filter, and aggregate the map after geoprivacy; the data behind them are the composed search text, the stated country, the CLDR names, the Natural Earth shapes and the Protomaps extract; the gates walk the real build](svg/explore.svg)

Explore is the first of the two flows Laminario takes from iNaturalist (dossier 05, section 4): a visitor walks the
collection the way a curator walks a cabinet room, from the realms to a cabinet, from a cabinet to a drawer, and
reads the slides label end up; or searches, or looks at where the specimens came from. The research behind every
choice, with its measurements, is dossier 12 of the planning record; the requirements are R-1001 to R-1009 and the
shared R-080, R-084, R-085 and R-089 ([U10 requirements](../design/features/u10-explore/requirements.md)).

## 1. Addresses and navigation

| Address | Place | Drawn from |
|---|---|---|
| `/` | the realms, with their collections as cabinets | the tree |
| `/c/<collection>` | a cabinet: its drawers | the tree |
| `/c/<collection>/<drawer>[/<group>]` | a drawer: its slides as glass slides, its dividers, its filters | the tree, `/api/slides`, `/api/explore/facets` |
| `/search?q=&node=&...` | search over the whole collection or one cabinet or drawer | `/api/slides`, `/api/explore/facets` |
| `/map?...&at=<country>` | where the specimens came from | `/api/explore/map`, `/api/explore/countries`, the basemap |
| `/s/<short id>` | the slide (U11) | |

Collection segments are unique in the tree (`plants`, `insects`, `rocks`), so an address names a collection
without its realm, and `/c/insects/lice` is the node `life.insects.lice`. Filters live in the query string with
repeated keys (`?preparation=smear&preparation=section`); changing one replaces the address rather than adding a
history entry, so the back button returns to the previous place, not to the previous chip.

Routing is wouter 3.11 (dossier 12, section 5: none of the places needs a data router). Laminario adds two rules in
`frontend/src/router/`. After a link is followed, the page starts at its top and the new place's heading takes the
focus, so a screen reader announces where the visitor arrived (R-1006). After back or forward, the place returns to
the scroll position it had, once its content has arrived, which is why each place reports when it is ready.

The tree (`GET /api/collections`: 191 nodes with their names in both languages, their rules and their slide counts),
the facet vocabularies (`GET /api/facets`) and the country names (`GET /api/explore/country-names`) are fetched once
per page by `TreeProvider`; the realms, a cabinet and a drawer's heading are drawn from them without another request.
Every other answer is kept by its address for the life of the page, so going back draws at once.

## 2. The places

Since U17 every set these places show is a set of glass slides in 3D, in the arrangement the visitor chooses, and
every panel is a glass plate ([19 The glass-slide interface](19_glass.md)); the cabinet fronts and oak drawer fronts
of U10 are gone.

**The realms** show Life, Earth and Matter, each a glass panel with its icon and description, with their collections
as glass slides: the collection's icon under the coverslip, its name on the left end, its slide and drawer counts on
the right. A search field and the way to the map lead elsewhere.

**A collection** shows what goes in it (the node's description and its rule, each taxon linked to its GBIF page) on a
glass panel, and its drawers as glass slides; an empty drawer is drawn fainter and says it is empty: it is open for
contributions. The whole of a collection is a search scoped to it (`/search?node=life.insects`), not a reserved
drawer name.

**A drawer** shows its dividers (its groups, or its siblings when it is a group) as glass slides, the current one
chosen, its filters on a glass panel, and its slides. A view (Parasites and hosts) lists the slides whose host lies in
its collection and offers only the anchor-kind filter.

**The slides of a drawer** are glass slides of their own formats, in millimetres, so each is drawn at its format's
proportion and at one scale for the whole set (R-1007). Drawn flat (a device without WebGL), a set lays every slide
long side across, label end first, each as long as its format against the set's longest:

$$L_{\mathrm{ref}} = \max\left(76.2,\ \max_i L_i\right) \ \mathrm{mm}, \qquad s = \dfrac{W_{\mathrm{col}}}{L_{\mathrm{ref}}}, \qquad w_i = s \cdot L_i, \qquad h_i = s \cdot S_i,$$

where $L_i$ and $S_i$ are slide $i$'s long and short sides and 76.2 mm is the longest standard format (2 x 3 in).
The label end is 20 mm (ISO 8037-1's marking end), or 0.3 of the long side on a shorter slide, so a 46 mm thin
section keeps a 13.8 mm label. On it: the collection's hue band, the catalogue number in the label face (broken
between its letters and its digits, never inside the digits), the name with its epithets in italic and its authorship
roman. The specimen's thumbnail sits under the coverslip. On the right end: the preparation, the locality with the
country, and the collection date. Pages of 48 grow only when the visitor asks ("show 48 more"); the number shown is
kept in the address (`n=`), so going back returns to the same slides.

**Search** reads the words as the visitor types (after 250 ms without a keystroke), sorts by relevance while there
are words and by newest otherwise, and adds a collection facet: the cabinets its words reach, with their counts.

**The map** is described in section 6.

## 3. Search

Each slide carries `search_text`, composed by `app/services/search.py` when the slide is created, from the anchor's
name as written, the short id, the host, the catalogue number, the locality, the stain, the country's code and its
English and Spanish names, the names of every node on the slide's placement path in both languages, and the
preparation's names. Migration 0008 creates the FTS5 table `slide_search` over that column (external content,
tokenizer `unicode61 remove_diacritics 2`, so "liquenes" finds "líquenes") and three triggers that keep it in step
with every insert, delete and change of the text, whatever writes the row.

A visitor's words become an FTS5 expression of quoted prefix terms joined by AND (`"piojo"* AND "chile"*`), so no
input is ever read as query syntax (R-1002). Results are ranked by FTS5's BM25 with its defaults
($k_1 = 1.2$, $b = 0.75$): for a query $Q$ of terms $q$ and a slide's text $D$,

$$\mathrm{score}(D, Q) = \sum_{q \in Q} \mathrm{IDF}(q) \cdot \dfrac{f(q, D)\,(k_1 + 1)}{f(q, D) + k_1 \left(1 - b + b\,\dfrac{|D|}{\mathrm{avgdl}}\right)},$$

where $f(q, D)$ is the term's frequency in the text, $|D|$ its length in tokens and avgdl the mean length.

Two moments compose the text for rows that did not get it at creation. Migration 0008 composes it for every slide
that existed before the column, and it does so before the index and its triggers exist: the update trigger removes
the old text from the index, and removing a row an external-content index never held corrupts it ("database disk
image is malformed", found by the migration test). The base import composes it again for every slide it writes,
with the server's tree, since a bake's rows carry the names of the tree of their day.

## 4. Filters and facet counts

`app/services/explore.py` narrows published slides by node (the node and everything under it), anchor kind,
preparation, preservation, country and origin (columns of the slide), and by modality, licence family and
whole-slide (a matching asset exists). Values of one facet are alternatives, facets combine: with $F$ the set of
filters and $A_g$ the slides allowed by facet $g$,

$$\mathrm{shown}(F) = \bigcap_{g \in F} A_g, \qquad \mathrm{count}_f(v) = \left|\,\{ s \in \bigcap_{g \in F,\, g \ne f} A_g \ :\ v(s) = v \}\,\right|.$$

The count beside a value leaves out its own facet's filter (R-1001), so choosing a second preparation shows how many
it would add. The place also reads the counts with no facet filter at all, the universe of values: a value the other
filters rule out stays in its place, disabled, and the list does not jump. The licence family is read from the
canonical licence URI (public domain, CC BY, BY-SA, BY-NC, BY-NC-SA); whole-slide is a yes-or-no filter whose two
values cancel out; the collection facet counts slides per collection with the node filter left out.

## 5. Countries

A slide's country is an ISO 3166-1 alpha-2 code. The vocabulary (257 codes with their English and Spanish names) is
built from Unicode CLDR 48.2.2, and the shapes (247 features) from Natural Earth's 1:50m admin-0 map units, rounded to
0.01 degree, with each country's hand-placed label point and the zoom it is labelled from; `scripts/build_countries.py`
builds both from files whose SHA-256 it records, and `--check` proves the committed files are the rebuild (R-1005).

A contribution states its country, or its coordinates imply it: the country whose shape contains the point, else the
nearest shape within 0.25 degree of its edge (a collecting point on a beach, which the rounded coast leaves in the
sea). Distances are measured with the longitude scaled by the latitude's cosine,

$$d = \min_{\mathrm{segments}} \left\lVert (\Delta\lambda \cos\varphi,\ \Delta\varphi) \right\rVert \le 0.25^{\circ}.$$

A submission that states a country and gives coordinates outside it is refused, with the country the point lies in
(R-1004). A base slide carries a country only where its source states one (R-1009, page 10).

## 6. The map

The map is MapLibre GL JS 6.11 over a world basemap cut from one Protomaps daily build (OpenStreetMap data, ODbL).
The extract stops at zoom 7: slides are placed at country level, and an obscured contribution's 0.2 degree cell is
18 px wide at zoom 7 (a 256 px tile spans $360 / 2^7 = 2.81$ degrees). Measured with go-pmtiles 1.31.2 on the
2026-09-28 build:

| Max zoom | Tiles | Archive |
|---|---|---|
| 5 | 1,045 | 15 MB |
| 6 | 3,396 | 45 MB |
| 7 | 10,666 | 188 MB |
| 8 | 33,312 | 556 MB |

`scripts/fetch_basemap.py` cuts the zoom-7 extract (188,341,959 bytes) and checks it against its recorded SHA-256:
two extracts of the same build were byte-identical. The file lives on the data volume, never in the repository;
production nginx serves it, and in development the API does (`GET /api/explore/basemap.pmtiles`, byte ranges and
HEAD). The map reads it through the `pmtiles` protocol, with its web worker emitted by Vite as an ES module, since
MapLibre 6 looks for its worker beside its own module, which a bundle does not have.

Of the basemap only the ground, the water and the rivers are drawn, in colours taken from the room's tokens
(`--c-map-land`, `--c-map-water`, `--c-map-border`, contrast-checked against the text drawn on them) and applied
again when the room changes. Borders, shading and labels are Laminario's own layers over the Natural Earth shapes:

| Layer | Draws |
|---|---|
| `countries-shade` | the accent at an opacity by slide count: 0.2 from 1, 0.34 from 5, 0.5 from 20, 0.66 from 100 (the legend's steps) |
| `countries-line` | borders; the selected country in the accent, the hovered one thicker |
| `labels-placed` | a country with slides, at every zoom: its name in the visitor's language and its count |
| `labels-other`, `labels-late` | the other countries from zoom 3 or 5, by Natural Earth's label zoom |
| `cells`, `points` | contributions with coordinates: an open slide at its point, an obscured one as its cell (R-1003) |

Labels are set in Laminario Sans itself: the style declares the page's font file in MapLibre's `font-faces`, which
rasterises it in the browser, so no glyph server is needed. The shading and the selection are feature state, the
labels a GeoJSON source rebuilt when the counts or the language change. Choosing a country, on the map or in the list
beside it, marks it, flies to it and shows its first six slides with a link to search them; the list is the map's
keyboard and screen-reader equivalent and works where WebGL does not. Without the basemap (a 404 to the HEAD
request) the shapes become the ground, and the page says so (R-1008).

## 7. Gates and tests

| Gate | Checks |
|---|---|
| `tests/explore/test_explore.py` | filters and faceted counts (R-1001); search in both languages, with and without accents, by prefix, catalogue number and short id, never as syntax (R-1002); the map after geoprivacy (R-1003) |
| `tests/collections/test_places.py` | countries of points, stated countries against coordinates (R-1004) |
| `scripts/build_countries.py --check` | the vocabulary and the shapes are the rebuild of their pinned sources (R-1005) |
| `tests/explore/test_basemap.py` | byte ranges, HEAD, a 404 without the extract (R-1008) |
| `tests/base/test_countries.py` | stated countries on base slides; a record change reaches the bake and the import without processing (R-1009) |
| `tests/db/test_migrations.py` | slides older than the index are indexed by migration 0008 |
| `frontend/src/explore/filters.test.ts`, `frontend/src/slide/names.test.ts` | the filters in the address; names, catalogue breaks, the tray's scale |
| `frontend/gates/walk.mjs` | by pointer from the landing to a cabinet, a drawer, a facet, search and the map (R-084); the heading focused after every navigation and a filtered drawer reopened from its address (R-1006); every slide's proportion within 1 percent at one scale, label end first (R-1007); the map without its basemap (R-1008) |
| `frontend/gates/fit.mjs`, `motion.mjs` | every place at four widths, two rooms and two languages (R-080); nothing moves with reduced motion (R-085) |

The browser gates refuse to run unless the API on port 8147 answers as Laminario with at least 300 slides: a gate
against another product on the port, or an empty collection, would pass without having looked.
