# 02 · Build the base collection

How to extend, re-check and deploy the base collection. The design is in
[10 The base collection](../architecture/10_base-collection.md); this page is the operator's sequence. Commands are
PowerShell on the workstation (Windows) unless marked as run on the server.

## 0. Prerequisites

- A clone set up as in [01 Run it locally](01_run-locally.md), with libvips and OpenSlide found (`LAMINARIO_VIPS_BIN`
  on Windows).
- The data vault: `LAMINARIO_FIXTURES` in `.env` names a folder on a large drive (not the system drive). The lane
  writes only under `<vault>/base/`: `candidates/`, `sources/` and `tmp/`.
- Disk: the sources of the current lock take about 37 GB (the NMNH and OpenSlide scans are 35 GB of it); a full bake
  needs about as much again for its root.

## 1. Find candidates

Add the source to `data/base/harvest.yaml` under its collection, then harvest that collection:

```powershell
.\.venv\Scripts\python -m app.base harvest life.reptiles
```

| Entry | Harvests |
|---|---|
| `{commons: "Category name", depth: 1, limit: 30}` | a Commons category and its subcategories to `depth` levels |
| `commons_files: ["File:...", ...]` with an optional `min_side` | named Commons files (found by search) |
| `{nhm: "query", filters: {...}, limit: 60}` | NHM imaged records (`need_micro: true` keeps only records with a microscope image) |
| `{smithsonian: "query", title_contains: "Photomicrograph", limit: 80}` | Smithsonian Open Access records with a CC0 image (`LAMINARIO_SI_API_KEY`, else the shared `DEMO_KEY`, 30 requests an hour) |

The harvest rewrites `<vault>/base/candidates/<sheet>.jsonl`, `.png` (the numbered contact sheet) and `.tsv`
(number, source, record, title, licence, size, hints). A sheet is usually a collection, but any name works: files
found later go on a sheet of their own (`search.additions`), so the numbers of a sheet already reviewed never move.
If a category sheet must be harvested again, compare the first columns of the old and new `.tsv`.

## 2. Review and pick

Open the sheet and its `.tsv`, and read each chosen record's description (in the `.jsonl`) for the organism, the
illumination and the stain. Write one line per slide in `data/base/picks/<sheet>.txt` (the notation is in the
design page, section 3.2), with a comment block at the top saying what was reviewed and what was excluded and why.
When the source states where the specimen came from, write it as `locality=` the way the source gives it, and add
`country=` with the ISO 3166-1 code when the locality names a country or a place inside exactly one country
(`locality=Ponza, Italy; country=IT`, `locality=South Uist; country=GB`); never infer a country from anything else.
An NHM record's own country is taken by `lock` and must agree with a `country=` the pick states. Then:

```powershell
.\.venv\Scripts\python -m app.base select
.\.venv\Scripts\python -m app.base lock
```

`lock` lists every pick that does not build, with its reason. The usual ones:

| Reason | What to write |
|---|---|
| `SYNONYM; name the accepted taxon (key N)` | `taxon=#N` and `name=<the name as written>` |
| `no exact backbone match (got HIGHERRANK KINGDOM)` for a genus | the genus is a homonym: find its key with its lineage and write `taxon=#key` |
| `no exact backbone match (got NONE)` | the rank or the name differs in the backbone; anchor at the rank it has, and keep the name in `name=` |
| `the source records no author or rights holder` | drop the pick: it cannot be attributed |
| `<node> does not take it; suggested <node>` | remove the node, or name an accepting one |
| `duplicate slide id` | the same file was picked twice (from two sheets) |
| `the record's country ... is not a CLDR name` | the NHM record writes the country its own way: state `country=` on the pick |
| `the pick's country XX is not the record's ...` | the pick and the NHM record disagree: read the record again |
| `country 'XX' is not an ISO 3166-1 code of the vocabulary` | a typing error in `country=` |

## 3. Acquire and validate

```powershell
.\.venv\Scripts\python -m app.base acquire
.\.venv\Scripts\python -m app.base validate
```

`acquire` skips what is already in the vault, fetches Commons images one at a time (paced) and whole-slide files four
at a time, and resumes a stopped download. Run it in the background for large scans and follow its log; a run stopped
by a time limit is simply started again. `validate` writes `docs/collections/base-report.md` and `coverage.md` and
exits non-zero when a slide fails, when a floor is missed without a recorded reason, or when a rock family has no
polarised pair.

Commit the picks, `selection.yaml`, `lock.yaml`, `names.json`, `taxa.json`, `acquired.json` and the two reports
together, with the tests in `tests/base` passing.

## 4. Bake

```powershell
.\.venv\Scripts\python -m app.base bake --out (Join-Path (Split-Path $env:LAMINARIO_FIXTURES) "bake-2026-09-30")
```

The bake creates a complete data root in `--out` and processes every slide with the product's pipeline (whole-slide
pyramids, the z-plane policy, derivatives). It can take hours for the whole-slide scans; it keeps `bake-index.json`
so a stopped bake continues where it stopped. It ends by writing `manifest.json` and reports the number of failed
jobs, which must be zero before an import.

The index keeps two fingerprints of each baked slide: of its assets and of its whole lock entry. After the lock
changes, a slide whose assets changed is baked again, and a slide whose record alone changed (a country, a locality, a
determination) has its rows rewritten in place with its images kept, so a corrected label never fuses a focal stack
again. `--refresh <slide id>` bakes a slide again whatever changed. A bake root made before the images fingerprint
existed learns it once from the lock it was baked from:

```powershell
git show <commit of that lock>:data/base/lock.yaml > (Join-Path $env:TEMP "baked-from.yaml")
.\.venv\Scripts\python -m app.base bake --out <bake root> --digests-from (Join-Path $env:TEMP "baked-from.yaml")
```

## 5. Import on the server

Copy the bake root to the server's staging folder, then import (on the server):

```bash
cd /opt/laminario && sudo -u laminario .venv/bin/python -m app.base import --bake /srv/laminario/staging/bake-2026-09-30
```

The import verifies every stored file against the manifest before it writes anything, copies the files into the
store, inserts the slides and assets as baked, composes their search text with the server's tree, and prints what it
imported, updated, skipped and copied. A base slide already on the server is brought to the bake's rows when its
record or its assets changed since, and skipped otherwise, so running the import again changes nothing. Remove the
staging copy afterwards.
