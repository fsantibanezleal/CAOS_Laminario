# U10 · Explore · design

The research, with every measurement, is dossier 12 of the planning record (and dossier 05, section 4, for the
flow). How the places are put together is the wiki page [12 Explore](../../../architecture/12_explore.md); what
they look like follows [the visual system](../../visual-system.md). This page records the unit's decisions.

## What the unit delivers

| Part | Where |
|---|---|
| A specimen's country: the contract field, migration 0008, the vocabulary (CLDR 48.2.2) and shapes (Natural Earth 1:50m) with label points | `app/contracts/ingest.py`, `app/db/migrations/versions/0008_country.py`, `app/collections/places.py`, `scripts/build_countries.py` |
| Text search over slides (SQLite FTS5, BM25, accents folded, kept in step by triggers, backfilled and recomposed at import) | `app/services/search.py` |
| Filters, facet counts, the map's aggregates after geoprivacy | `app/services/explore.py`, `app/routers/slides.py` |
| The basemap: a verified zoom-7 extract, served with byte ranges | `scripts/fetch_basemap.py`, `GET /api/explore/basemap.pmtiles` |
| Base slides placed in their countries, and record changes that reach the bake and the import without re-processing | `data/base/picks/`, `app/base/lock.py`, `app/base/bake.py`, `app/base/importer.py` |
| Addresses, focus and scroll on navigation | `frontend/src/router/` |
| The places: realms, cabinet, drawer, search, map | `frontend/src/places/` |
| The gates: the pointer walk, and fit and motion over the new places | `frontend/gates/walk.mjs`, `fit.mjs`, `motion.mjs` |

## Addresses

| Address | Place |
|---|---|
| `/` | the realms: Life, Earth and Matter with their collections as cabinets |
| `/c/<collection>` | a cabinet: its drawers (sub-collections) |
| `/c/<collection>/<drawer>[/<group>]` | a drawer: its slides, label end up, with dividers for its groups |
| `/search?q=&node=&...` | search over the whole collection, or one cabinet or drawer (`node`) |
| `/map?...` | where the specimens came from |
| `/s/<short id>` | the slide (U11) |
| `/design` | the visual system's specimen place (U9) |

Collection segments are unique in the tree (plants, insects, rocks), so an address names a collection without its
realm. Filters live in the query string with repeated keys (`?preparation=smear&preparation=section`), so every
state of a place can be shared and reopened (R-1006). The whole of a cabinet is a search scoped to it
(`/search?node=life.insects`), not a reserved drawer name.

## Decisions

- **One router, no data router.** wouter 3.11 (Unlicense, 77 KB unpacked) gives the location, path parameters, the
  query string and links; the places fetch what they show. After every navigation the new place's heading takes the
  focus (it is the first thing a screen reader announces) and the page returns to the top; going back restores the
  scroll position the place had.
- **The tree is fetched once.** `GET /api/collections` returns all 191 nodes with their names in both languages, their
  rules and their slide counts; the realms, a cabinet and a drawer are drawn from it without another request.
- **A drawer is a tray.** Slides lie on a sunken tray at one scale for every format (a thin section is visibly
  shorter than a 76 x 26 mm slide), label end on the left: the collection's hue band, the catalogue number in the
  label face, the name (italic when a binomial), the preparation, the locality and the date; the specimen's
  thumbnail sits in the coverslip area. Pages of 48 and a "show more" control, never infinite scroll, so the page
  has an end and a keyboard user is never trapped. The scale is 3.4 px per mm below 768 px of width (a 76 mm slide
  is 258 px, inside a 360 px screen) and 4 px per mm above.
- **Facets are counted the faceted-search way.** A facet's counts leave out its own filter, so choosing a second
  preparation shows what it adds; a value with no slide under the other filters is shown disabled, not hidden, so
  the list does not jump. On narrow screens the facets open in a dialog; from 1280 px they are a rail beside the tray.
- **Search is quiet.** The field searches as the visitor types, after 250 ms without a keystroke, and replaces the
  address rather than adding a history entry per keystroke; the sort is relevance while there are words, newest
  otherwise.
- **The map labels only what the collection places.** The basemap (Protomaps, zoom 0 to 7, OpenStreetMap data) is
  drawn without its own labels, in colours taken from the room's tokens, and redrawn when the room changes. The
  countries are shaded by how many slides they hold and labelled with their CLDR name in the visitor's language, in
  Laminario Sans itself through MapLibre's `font-faces` (the style declares the page's own font file; no glyph
  server). A country with slides is labelled at every zoom, the others from Natural Earth's label zoom. Points are
  contributions with coordinates; an obscured one is drawn as its cell with the public point. Selecting a country
  (on the map or in the list beside it) shows its slides and a link to search them. The list is the map's keyboard
  and screen-reader equivalent.
- **The map works without its basemap.** When the extract is not installed (a 404), the map draws the countries and
  points on the room's ground; nothing else changes (R-1008).
- **A base slide's country is stated, never guessed.** NHM records give a country name, mapped to its code through
  the CLDR names (unknown names fail the lock); NMNH sheets and Commons descriptions that state a country give it as
  a pick's `country=`. Nothing is geocoded from free text. The bake records two digests per slide, of its images and
  of its record: a changed record updates the baked rows in place, and the import updates a base slide already in
  the target, so correcting a country never fuses a focal stack again (R-1009).
