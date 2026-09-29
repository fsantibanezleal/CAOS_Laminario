# 17 · About the collection

![About the collection: GET /api/about joins what the database counts when it is read with the facts of credits.json; the About place draws the same blocks in English and Spanish, with live blocks from the answer, figures drawn inline in the room's tokens and equations typeset by KaTeX; the slide place gives a citation and each image's attribution; the map credits OpenStreetMap with its link; the link check sorts every external link as reachable, broken or not checkable by a machine](svg/about.svg)

A collection built from other people's images owes its visitors an account of where they came from, what may be done
with them and how to credit them, and owes its sources that credit. The About place gives that account, with the
numbers counted from the database, and explains how an image becomes the stage a visitor zooms into. The research is
dossier 17 of the planning record; the requirements are R-1501 to R-1507
([U15 requirements](../design/features/u15-about/requirements.md)); the decisions are in the
[U15 design](../design/features/u15-about/design.md).

## 1. Numbers from the data (R-1501, R-1502)

`GET /api/about` counts when it is read (and may be cached for a minute):

| Number | What is counted |
|---|---|
| slides, by realm and collection, by origin | slides with the status `published` (a hidden slide is `hidden`) |
| whole-slide scans | published slides with a micro image of role `pyramid` or `z_plane` |
| images | ready source images of published slides: a focal plane counts, a composite fused from a stack (`edf_wavelet`, `edf_variance`, `height_map`) does not |
| countries | distinct countries of published slides |
| contributors | accounts with a published contribution |
| identifications | current, visible identifications by accounts, of slides they did not contribute |
| images by source | a source is known by the host its files come from (`upload.wikimedia.org` is Wikimedia Commons, `ids.si.edu` the Smithsonian); a contribution's images are its contributor's |
| images by licence | the canonical licence URI, its short name and family (cc0, pdm, nkc, by, by-sa, by-nc, by-nc-sa) |

A host no source claims is counted as `other`; the test holds every host of the base lock to a known source, so a
new source cannot arrive without its description. What the database does not hold is in `app/about/credits.json`:
each source's name, homepage, hosts and terms page; each vocabulary's citation, DOI and licence; the map's data; the
software and fonts with their licences. It was read from primary sources on 2026-09-29 (PyPI, npm, GitHub, the GBIF
API, Crossref).

## 2. The prose, in two languages

The text is not interface strings: it is long and structured, so it lives as typed blocks in
`frontend/src/about/content.en.ts` and `content.es.ts` (paragraphs, headings, lists, equations, code, figures, and
live blocks that the place fills from the answer). `content.test.ts` holds the two languages together: the same
sections in the same order, the same block shapes, the same equations and links; words for every source of
`credits.json` and for every licence family the policy accepts; every equation typesets; no em dash and no arrow.

The imaging section is transcribed from pages [04](04_imaging.md), [05](05_delivery.md) and [13](13_slide.md): the
pyramid's level count $L = \lceil \log_2 (n/512) \rceil + 1$, the fidelity floor (PSNR of 38 dB over 32 regions, JPEG
quality 85 raised to 90 when colour subsampling fails a thin section), the IIIF tile, the objective's zoom
$z = pM/10$, the planes kept from a large stack, the variance selection and the complex wavelet fusion of the EPFL
plugin with the defect Laminario corrects, and the polarised pair. The identification section restates the agreement
rule of page [15](15_identify.md).

## 3. Figures and equations

The five figures (the pyramid's levels, one image at three objectives, a focal stack fused, a polarised pair,
geoprivacy) are React components drawing inline SVG with the room's tokens, since an SVG loaded as an image cannot
read the page's colours; each takes its labels in the page's language. The equations are typeset by KaTeX 0.18.9
(MIT), loaded only with the About place's own chunk, with its fonts served from the site.

## 4. Crediting and citing (R-1503)

Creative Commons' recommended practice is TASL: the title, the author, the source and the licence, with a link to the
licence, and a note when the work is adapted. Every image Laminario serves is an adaptation in that sense, so the
line says how: `re-encoded as a tiled pyramid` for a scan, `fused from a focal stack` for a composite or a height
map, `re-encoded` for a photograph. The slide's citation follows the NHM Data Portal's form for a record:

```
Laminario (2026). Polyplax borealis (NHMUK010173454), whole mount [Microscope slide].
https://laminario.ml.fasl-work.com/s/7K2QD4MN. Read on 29 September 2026.
```

`frontend/src/about/cite.ts` builds both from the slide record, with the words of the page's language; the slide place
shows them under **Cite this slide**, each with a button that copies it.

## 5. The map's credit (R-1506)

The OpenStreetMap Foundation's attribution guidelines ask for "OpenStreetMap" in a corner of a browsable map, linked to
its copyright page. The map place's credit line now links it; the About place names OpenStreetMap (ODbL), Protomaps,
Natural Earth (public domain) and Unicode CLDR (Unicode License v3), the four sources of what the map draws.

## 6. Links (R-1505)

`frontend/gates/links.mjs` reads every external address of the content and of `credits.json` and sorts it: reachable
(2xx after redirects, or, for a DOI, registered at doi.org's handle API, since publishers' landing pages sit behind
challenges), not checkable by a machine (a bot challenge answered, listed for a person to open), or broken (anything
else, which fails the check). On 2026-09-29: 46 links, 43 reachable, 3 not checkable by a machine (the NHM Data
Portal's pages and si.edu's Open Access page answer Cloudflare challenges to every client but a person's browser,
headless Chromium included), 0 broken. It needs the network, so it runs before a release, not in continuous
integration (ADR-0074).

## 7. The footer

Every place ends with the same footer: About the collection, Licences and credits (`/about#licences`) and How to
cite (`/about#cite`). The About place goes to a section named in its address once the numbers that move it have
arrived.

## 8. Gates and tests

| Gate | Checks |
|---|---|
| `tests/about/test_about.py` | the numbers over a published, a hidden and a base slide (a composite not counted, the contributor's own identification not counted); sources and licences with their counts; the credits; every host of the base lock known; every licence family in the policy (R-1501, R-1502, R-1507) |
| `frontend/src/about/content.test.ts` | both languages alike; every source and licence family described; every equation typesets (R-1502, R-1504, R-1507) |
| `frontend/src/about/cite.test.ts` | the citation and the attribution, a composite and a contribution (R-1503) |
| `frontend/gates/about.mjs` | from the landing place by the footer; the numbers equal the API's; a card for every source and licence; five figures in the room's colours and every equation typeset, in both rooms and languages; a section opened from its address; the map's linked credit; a slide's citation and attributions, and Copy (R-084, R-1501 to R-1504, R-1506) |
| `frontend/gates/links.mjs` | every external link (R-1505) |
| `frontend/gates/fit.mjs`, `motion.mjs`, `walk.mjs` | the About place at every width, room and language, without motion, reached by pointer (R-080, R-084, R-085) |

## References

- Creative Commons, [Recommended practices for attribution](https://wiki.creativecommons.org/wiki/Recommended_practices_for_attribution).
- Natural History Museum, [Data Portal citation](https://data.nhm.ac.uk/about/citation) (read from its source,
  `NaturalHistoryMuseum/ckanext-nhm`, `templates/about/citation.html`); Scott B et al. (2019). The Natural History
  Museum Data Portal. *Database* 2019: baz038. doi:[10.1093/database/baz038](https://doi.org/10.1093/database/baz038).
- OpenStreetMap Foundation, [Attribution Guidelines](https://osmfoundation.org/wiki/Licence/Attribution_Guidelines).
