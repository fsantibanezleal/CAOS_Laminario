# 10 · The base collection

![The base-collection lane: four open sources are harvested into review sheets; the curator writes picks; select, lock, acquire and validate run on a workstation and commit their records; the bake runs the product's own pipeline into a declared root; the server imports the bake after verifying every file](svg/base-lane.svg)

Laminario opens with a collection of its own: slides chosen one by one from open sources, each with its image, its
anchor in the collection tree and the provenance of every file. This page describes how that collection is made
and checked. The research behind the sources is dossier 06 (availability per collection) and dossier 10 (the
sources re-verified) of the planning record; the composition is in
[docs/collections/base-report.md](../collections/base-report.md) and
[docs/collections/coverage.md](../collections/coverage.md), both generated.

## 1. What a base slide is

A base slide is an ordinary slide case (the ingestion contract of [02](02_data-contracts.md)) with `origin: base`.
It differs from a contribution in two ways only:

- every asset carries a **source block**: the URL it was taken from, the source's record id, the retrieval date and
  the SHA-256 of the bytes retrieved (R-071);
- its licence must be in the **base policy set** (CC0, public domain mark, no known copyright restrictions, CC BY and
  CC BY-SA in their versions), and never a non-commercial licence.

Everything else is shared: the same anchor check, the same placement rule of the tree ([09](09_collections.md)),
the same processing jobs ([04](04_imaging.md), [06](06_worker.md)), the same delivery ([05](05_delivery.md)).

## 2. The sources

| Source | What it gives | Licence per item | How it is read |
|---|---|---|---|
| Wikimedia Commons | micrographs in categories, and files found by search | CC0, public domain, CC BY, CC BY-SA (read from `extmetadata`) | MediaWiki API, `generator=categorymembers` or `titles=` |
| NHM Data Portal | photographs of slides with their labels (the macro) and microscope images (the micro) of the Natural History Museum's slide collections | CC BY 4.0 per media item | CKAN datastore, IIIF level 2 image service; the taxon from the record's GBIF occurrence |
| Smithsonian Open Access | Wilson A. Bentley's snow-crystal photomicrographs in the Smithsonian Institution Archives, typed by Bentley's own categories in their titles | CC0 per media item (`usage.access`) | the Open Access API with an api.data.gov key (`LAMINARIO_SI_API_KEY`, else `DEMO_KEY`); images from the IDS delivery service |
| Zenodo (Smithsonian NMNH, parts III and IV) | whole-slide scans in NDPI with focal stacks of 3 to 81 planes, and a metadata sheet per record | CC BY 4.0 | Zenodo records API; the MD5 of each file |
| OpenSlide test data | whole-slide scans in DICOM, Philips TIFF, Ventana BIF and NDPI | CC0 1.0 | `index.json` with the SHA-256 of each file |

A slide whose source records no author and no rights holder is refused, because it could not be attributed; so is a
source record id longer than the contract's 200 characters.

The CDC Public Health Image Library, named in the plan, is read through its Commons mirror: a PHIL details page
serves only a small image and loads its description after the page, while the mirrored file carries the full
description, the photographer and the public-domain statement.

## 3. The lane, step by step

All steps are `python -m app.base <step>` and read `LAMINARIO_FIXTURES` for the data vault (a local folder, never
in git). The committed records are in `data/base/`.

| Step | Reads | Writes | Network |
|---|---|---|---|
| `harvest [sheet...]` | `data/base/harvest.yaml` | vault `candidates/<sheet>.jsonl`, a numbered review sheet `.png` and its `.tsv` | Commons, NHM, Smithsonian, GBIF |
| (the curator) | the review sheets | `data/base/picks/*.txt` | none |
| `select` | picks | `data/base/selection.yaml` | none |
| `lock` | selection, candidates | `data/base/lock.yaml`, `names.json`, `taxa.json` | GBIF, Zenodo, OpenSlide index |
| `acquire [slide or collection...]` | lock | vault `sources/<sha256>.<ext>`, `data/base/acquired.json` | every source |
| `validate` | lock, acquired, taxa | `docs/collections/base-report.md`, `coverage.md` | none |
| `bake --out ROOT [slide or collection...]` | lock, acquired, vault | only `ROOT` | none |
| `import --bake ROOT` | `ROOT` | the deployment's database and store | none |

### 3.1 Harvest and review

The harvest lists candidates only: it keeps an image when its licence is in the base policy and its long side is at
least 1000 pixels (a named file may lower that, as `min_side` says in `harvest.yaml`), and writes a contact sheet
with each image numbered. **No slide enters because a query matched it.** Full-text search is noisy (the dossier-06
amphibian pool held an astronomy picture), and a record's metadata cannot tell a microscope preparation from a
figure plate, an SEM image, a drawing or an engraving. Every slide is chosen by looking at it on the sheet, and its
description is read for the facts the image cannot show: the organism, the illumination, the stain.

### 3.2 Picks

One line per slide, written against the sheet:

```
<sheet> <n> | <anchor> | <preparation> | <part> | <modality> | <stain> | <node> | <note> | <extras>
```

| Head | Picks |
|---|---|
| `<sheet> <n>` | image `n` of a harvest sheet (a Commons file, an NHM record or a Smithsonian record) |
| `pair <sheet> <n_ppl> <n_xpl>` | a polarised pair: the same field in plane-polarised light and between crossed polars |
| `nhm <catalogue number>` | an NHM slide record, the anchor from its GBIF occurrence |
| `zenodo <record> <file name>` | a whole-slide scan from a Zenodo record |
| `openslide <path>` | a whole-slide scan from the OpenSlide index |

Anchors are `taxon=Name@rank[@Kingdom]` or `taxon=#<backbone key>`, `rock=`, `mineral=Name[:class]`,
`crystal=origin[/system][:category]`, `material=`, with `~fossil` or `~in_amber` when needed. Extras record facts
read on a label or a source sheet: `host`, `locality`, `collected`, `collector`, `preparer`, `name` (the
determination as written), `type`, `catalogue`, `stack=policy`, `pixel` (micrometres per pixel, when stated),
`country` (the ISO 3166-1 code, when the stated locality names a country or a place inside exactly one country). The
section header of the file (`[life.fishes]`) is the collection the pick is meant for; the tree decides the node.

A base slide carries a country only where its source states one (R-1009): the locality the curator transcribed, or
the NHM record's own country, whose name `lock` maps to its code through the CLDR names and checks against a code the
pick states. Nothing is geocoded from free text. 69 of the 505 slides have one (dossier 12): the NHM slides, the
NMNH, USDA and Field Museum scans, and the Commons and Smithsonian images whose sheets name their locality.

What the curator records as illumination is what the source states, or what the image shows beyond doubt
(interference colours on an extinct black ground are crossed polars). An image whose illumination can be neither
read nor seen is left out: three well-known Reischig fish-scale preparations were excluded on that ground.

### 3.3 The lock

`lock` turns every pick into a complete slide entry. Names are resolved on the GBIF backbone by **strict** match at
the given rank (`names.py`): a fuzzy match, a higher-rank fallback or a synonym is refused, and the refusal names the
accepted key when there is one, so the curator writes `taxon=#<key>` and keeps the name as written in `name=`. Each
key's record and lineage go to `taxa.json`, which later steps read instead of GBIF. Every entry is then placed by the
tree's engine ([09](09_collections.md)): a pick naming a node must name an accepting one. A pick that does not build
is reported with its reason; the lock is written only when none fails.

What the backbone taught while locking (dossier 10, findings F-032 and F-033 of the planning record):

- it has **no ray-finned fish class** (Actinopterygii, Teleostei and Osteichthyes do not match), so an unidentified
  fish scale cannot be anchored and is left out;
- `Serpentes` matches a family placed directly under Chordata, outside the four reptile classes, so snakes are
  anchored at `Squamata@class` with `name=Serpentes`;
- common genus names are homonyms across kingdoms or have synonym twins (*Hydra*, *Anomia*, *Dugesia*,
  *Haemoproteus*): a strict match with the kingdom still answers only the kingdom, so these picks use the key,
  verified by its lineage (`Animalia > Cnidaria > Hydrozoa > Anthoathecata > Hydridae` for *Hydra*).

### 3.4 Acquisition

Each image is downloaded once and stored under its SHA-256 (`sources/<sha256>.<ext>`), so a changed source becomes a
new file and never overwrites the old one. `acquired.json` maps each URL to what was retrieved (SHA-256, size, file,
date) and is committed: it is the provenance of R-071. A checksum the source publishes is verified and a mismatch
stops the step (Zenodo's MD5, the OpenSlide index's SHA-256). A DICOM archive is unpacked beside itself, since
OpenSlide opens DICOM from a folder of instances.

Commons images are fetched one at a time with a pause between them, and a 429 or 503 is answered by waiting
(Retry-After, or a doubling back-off): Wikimedia's image servers refuse clients that do not pace themselves.
Whole-slide files are fetched four at a time, because Zenodo serves about 1 MB/s per connection and the ten NMNH
scans weigh 25 GB. Every download grows its own partial file and resumes with an HTTP Range request after an
interruption.

### 3.5 Validation

Every lock entry is turned into a submission (`submission.py`: its source blocks from `acquired.json`; a focal stack
expanded from the acquired file into the planes the z-plane policy keeps) and put through the same checks as a
contribution: the ingestion contract, then the tree's submission check (anchor, host, part, placement), against a
throw-away database seeded from `taxa.json`, so no network is used. The report lists every slide with its node and
verdict, and the floors of dossier 06:

| Floor (R-070, R-072) | Meaning |
|---|---|
| at least 300 slides | the whole collection |
| at least 12 per collection | every one of the 18 collections |
| at least 14 whole-slide images | the NMNH and OpenSlide scans |
| a PPL/XPL pair per rock family | igneous, sedimentary and metamorphic |

A collection below 12 slides fails validation unless it is listed in `SHORTFALLS` with the finding that records the
searches made: the reptiles are the one such collection (finding F-031). The coverage matrix shows every node of
the tree with its slides, and marks a node without any as open for contribution.

### 3.6 The bake and the import

The bake is the product processing its own collection. `bake --out ROOT` treats `ROOT` as a complete Laminario data
root: it creates the database there, stores each lock entry through `create_slide` as a published base slide,
points each asset at its acquired file in the vault, queues the processing jobs and runs the worker until the queue
is empty. It writes nothing outside `ROOT` (R-073). `manifest.json` lists every slide and asset row and the file
behind every storage key with its SHA-256 and size.

`bake-index.json` keeps, for each baked slide, its short id and two fingerprints (SHA-256 of canonical JSON): of the
lock entry's pixels, its assets without the fields that credit an image (licence, rights holder, creator, caption,
record id and address), which is what its images are made from; and of the whole entry. When the lock changes, a slide
whose pixels changed is removed and baked again; a slide whose record alone changed is rewritten in place from its
submission with no job queued: every slide column, and the credit columns of every stored image, matched to its lock
asset by source address and plane (a fused image takes the credits of its stack's first plane, as the fusion does). An
entry made before the pixels fingerprint is judged by the bake's own rows: if the source files of its stored images,
address and SHA-256, are exactly the files its lock entry now names, it gains the fingerprint and its record is
rewritten; otherwise it is baked again. No entry is trusted without a judgement.

The server never bakes. `import --bake ROOT` verifies every stored file against the manifest, refuses a bake with a
failed job or a changed file, copies the files under their storage keys (content addresses, so an identical file is
left in place: a file already there is kept only if its SHA-256 and size are the manifest's), and inserts the rows
as baked. `verify --bake ROOT` checks the served store against the manifest afterwards, file by file. The search text of every slide it writes is composed again with the
server's tree. An import can be repeated: a base slide already imported is brought to the bake's rows when its record
or its assets changed since, and skipped otherwise; a short id held by another slide is refused.

## 4. Tests

| Gate | Checks |
|---|---|
| `tests/base/test_base_collection.py::test_floors` | the floors on the committed lock; every shortfall recorded, and no stale record |
| `tests/base/test_base_collection.py::test_asset_provenance` | licence, attribution, URL, record id, acquisition entry with SHA-256 and date for every asset |
| `tests/base/test_base_collection.py::test_polarised_pairs` | pairs are complete (PPL and XPL) and cover the three rock families |
| `tests/base/test_base_collection.py::test_every_taxon_has_its_lineage` | every taxon anchor and host has its lineage in `taxa.json` |
| `tests/base/test_base_collection.py::test_a_sample_passes_the_offline_checks` | one slide per collection through the contract and the tree, offline |
| `tests/base/test_picks.py` | every head form, anchor form and extra of the notation |
| `tests/base/test_importer.py` | a changed or missing file, or a failed job, stops the import |
| `tests/base/test_sources.py` | Commons, NHM and Smithsonian answers become candidates only under the base licence policy |
| `tests/base/test_bake_sandbox.py::test_tests_never_write_canonical_outputs` | two slides baked and imported in temporary folders, the repository's records unchanged, the imported slides found by search (local, with the vault) |
| `tests/base/test_countries.py` | every country in the lock is a vocabulary code stated by a locality or an NHM record; the two fingerprints tell a record change from an image change; a country added to two baked slides rewrites their rows with no job queued and reaches the served rows and the search on the next import (local, with the vault) |
