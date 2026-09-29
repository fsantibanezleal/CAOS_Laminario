# Data contract

Laminario's data moves through contracts that are typed models with committed JSON Schemas; the database tables
are only the storage behind them. This section is the reference for anyone who prepares data for Laminario (a
contributor's slide case, an import of openly licensed slides) or reads what it serves.

| Page | What it holds |
|---|---|
| [01 The slide case](data-contract/01_slide-case.md) | Every field of a submission: type, whether it is required, what is accepted, the default. Generated from `contracts/ingest.schema.json`. |
| [02 Catalog records](data-contract/02_catalog-records.md) | Every field the API returns for slides, pages, summaries, validation results and processing jobs. Generated from `contracts/catalog.schema.json`. |
| [Architecture: the two contracts](architecture/02_data-contracts.md) | How the contracts are built, geoprivacy, the quality checks, the TypeScript mirror. |
| [Architecture: IIIF delivery](architecture/05_delivery.md) | The artifacts the web reads besides the catalog: `info.json`, manifests, the remote-asset contract. |

The two generated pages cannot drift from the models: `scripts/render_contract_docs.py --check` fails when a
committed page differs from the schemas, as `scripts/export_contracts.py --check` fails when a schema differs from
the models.

## What is refused, what is accepted and flagged

A submission is checked in three phases: structure (types, vocabularies, ranges, lengths, patterns and partial
dates), rules across fields, and flags. Every refusal names its field and what was expected. From the design
document, section 2.1:

| Field or condition | Accepted | When violated |
|---|---|---|
| `slide.format` | `iso_76x26`, `us_75x25`, `petro_27x46`, `us_2x3in`, or `custom` with 20 to 100 mm per side | refused |
| `slide.coverslip` | `none`, `18x18`, `22x22`, `22x40`, `22x50`, `24x50`, `24x60`, or `custom` that fits on the slide | refused |
| `slide.preparation` | one of ten: whole mount, section, smear, squash, strew, thin section, polished section, peel, cast, fluid mount | refused |
| `slide.prepared_on`, `specimen.collected_on` | a date as year, year-month or full date; not in the future; not before 1600 | refused |
| `specimen.anchor` | a taxon (GBIF usage key), rock (BGS RCS term), mineral (IMA name), crystal (system and origin) or material | refused when it does not resolve (the collection tree, U7) |
| `specimen.coordinates` | latitude in [-90, 90], longitude in [-180, 180], uncertainty at least 0 m | refused |
| `specimen.geoprivacy` | `open`, `obscured`, `private` | refused |
| `placement.node` | a collection node whose rule accepts the anchor, or a curator's override with a reason | refused for a contributor; accepted with an audit record for a curator |
| `assets` | at least one, at most 500; each with its family, role, licence, and a creator or rights holder | refused |
| `asset.licence` | CC0, Public Domain Mark, No Known Copyright, CC BY or CC BY-SA 2.0 to 4.0; for contributions also CC BY-NC and CC BY-NC-SA 4.0 | refused |
| the file's type | JPEG, PNG, WebP, TIFF or BigTIFF, SVS, NDPI, MRXS, SCN, VSI, DICOM WSI, Philips TIFF, with a header libvips or OpenSlide can read (the upload verifier, U5) | refused |
| image dimensions | 64 to 200,000 px per side, at most 20 gigapixels per plane | refused before any pixel is decoded |
| `asset.pixel_size_um` | 0.05 to 50 um per pixel | refused outside the range |
| focal planes | a stack's planes share their dimensions; index and depth each; at most 200 planes | refused |
| imported source | the source URL, record id, retrieval date and SHA-256 of the retrieved bytes | refused if any is missing |

## Missing and doubtful data

Missing data is accepted where the product can still be honest about it, and flagged so the contributor and the
visitor see it:

| Condition | Handling |
|---|---|
| a micro image without a pixel size | accepted and flagged `not_to_scale`; the viewer shows no scale bar and the quality check "scale" fails |
| a photograph carrying GPS while the place is private | accepted and flagged `gps_stripped`; the position is removed before storage, and no served file carries EXIF |
| a photograph taken more than a day from the collection date | accepted and flagged `exif_date_mismatch` for the contributor to confirm |
| a place without coordinates | accepted; the slide has no map point |
| an obscured place | stored exactly, served only as its 0.2 degree cell and a stable point inside it |
| a private place | stored, never served, nor its locality in a manifest |
| a TIFF or photograph whose resolution is a screen default (72, 96, 300 dpi) | not taken as a pixel size; the pyramid's resolution unit is "none" |

Outliers in imaging are handled by measurement, not by trust: a pyramid whose level 0 falls below 38 dB PSNR
against its source is rewritten at higher quality, and the measured value is stored with the asset.
