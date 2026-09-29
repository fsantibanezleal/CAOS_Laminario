# U15 · About the collection · design

The research is dossier 17 of the planning record (the Creative Commons recommended practices and the deeds, the NHM
Data Portal's citation formats read from its source, the base collection's sources and licences counted from the
lock, the vocabularies' citations, the OpenStreetMap attribution guidelines, the software and fonts with their
licences, the links a machine cannot check). How the parts fit is the wiki page
[17 About the collection](../../../architecture/17_about.md).

## What the unit delivers

| Part | Where |
|---|---|
| The facts: the sources (name, homepage, the hosts their files come from, their terms), the vocabularies, the software and the fonts | `app/about/credits.json` |
| The numbers and the counts by source and licence, read from the database | `app/services/about.py`, `GET /api/about` |
| The About place, its sections in EN and ES, the figures, the equations | `frontend/src/about/`, `frontend/src/places/about/` |
| The citation of a slide and the attribution of each image | `frontend/src/about/cite.ts`, the slide place |
| The footer every place shares (About, licences, how to cite) | `frontend/src/ui/Footer.tsx` |
| The map's credit linked to OpenStreetMap's copyright page | `frontend/src/map/style.ts` |
| The gates | `frontend/gates/about.mjs`, `frontend/gates/links.mjs`, `tests/about/` |

## Decisions

- **Numbers from the data (R-1501, R-1502).** The page never types a count. `GET /api/about` counts published
  slides (in total, by realm, by origin), whole-slide scans (slides with a pyramid of a whole-slide file), images (the
  source images of published slides: a focal plane is an image, a fused composite is not), countries, contributors
  (accounts with a published slide), and the images by source and by licence. A source is known by the host its
  files come from (`upload.wikimedia.org` is Wikimedia Commons, `ids.si.edu` the Smithsonian); a contribution's
  images are the contributors'. A host no source claims is counted as "other", which the test forbids for the base
  collection, so a new source cannot arrive without its description.
- **Facts in one file.** `app/about/credits.json` holds what is not in the database: each source's name, homepage,
  hosts and terms page; each vocabulary's name, citation, DOI or address and licence; each piece of software and
  font with its licence and address. The API returns it with the numbers; the page's prose is keyed by the same ids,
  and a unit test fails when an id has no words in either language (R-1502, R-1507).
- **Prose as content, not interface strings.** The About text is long and structured (paragraphs, lists, tables,
  equations), so it lives in `frontend/src/about/content.en.ts` and `content.es.ts` as typed blocks under the same
  section ids, not in the interface catalogue; the test checks that both languages have every section, the same
  equations and the same links.
- **Attribution as Creative Commons recommends it (R-1503).** Each image: its title (the caption, or the role and
  the slide), its author (creator, else rights holder), its source (the record's address), its licence named and
  linked, and "adapted: re-encoded as a tiled pyramid" (or "fused from a focal stack" for a composite), since every
  served image is an adaptation in the licence's sense. The slide's citation follows the NHM Data Portal's form:
  `Laminario (year). Name (catalogue number), preparation [Microscope slide]. Permalink. Read on date.` Both are
  copied with one button.
- **The imaging explained from the wiki (R-1504).** The section on how an image becomes a stage is transcribed from
  wiki pages 04, 05 and 13 (the pyramid's level count, the fidelity floor and the JPEG quality rule, the IIIF tile,
  the pixel size and the objective, the kept focal planes, the variance selection, the complex wavelet fusion, the
  polarised pair), with KaTeX for the equations and figures drawn as inline SVG in the room's tokens (an SVG loaded
  as an image cannot read the page's colours).
- **The map's credit (R-1506).** "OpenStreetMap" links to openstreetmap.org/copyright in the map's corner, as the
  OSM Foundation's guidelines ask; the About page repeats it with Protomaps.
- **The link check (R-1505)** runs before a release, not in continuous integration (it needs the network, ADR-0074):
  every external address of the content and of `credits.json`, with three outcomes, reachable, broken, and not
  checkable by a machine (a Cloudflare challenge, which iNaturalist, the NHM Data Portal and GBIF's pages answered
  to every client but a browser on 2026-09-29).
- **One footer.** Every place ends with the same footer: About the collection, licences and credits, how to cite,
  and the version, so the About place is one click from anywhere (R-084).
