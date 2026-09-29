# The slide case (ingestion contract)

<!-- Generated from contracts/ingest.schema.json by scripts/render_contract_docs.py; do not edit by hand. -->

What a submission must satisfy before anything is stored. `POST /api/slide-cases/validate` runs it without storing. Rules that span several fields, and the conditions that are accepted but flagged, are listed in [the data-contract overview](../data-contract.md).

Schema: [`contracts/ingest.schema.json`](../../contracts/ingest.schema.json) (JSON Schema, `https://laminario.ml.fasl-work.com/contracts/ingest.schema.json`).

### SlideCaseSubmission

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `origin` | string (enumerated) | no | one of: contribution, base | `"contribution"` |
| `slide` | [SlideSpec](#slidespec) | yes |  |  |
| `specimen` | [SpecimenSpec](#specimenspec) | yes |  |  |
| `placement` | [PlacementSpec](#placementspec) | yes |  |  |
| `assets` | list of [AssetSpec](#assetspec) | yes | 1 to 500 assets |  |

### SlideSpec

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `format` | string (enumerated) | yes | one of: iso_76x26, us_75x25, petro_27x46, us_2x3in, custom |  |
| `format_assumed` | boolean | no | true or false | `false` |
| `custom_mm` | [SizeMm](#sizemm) or null | no | a size, only for the custom format | null |
| `coverslip` | string (enumerated) | no | one of: none, 18x18, 22x22, 22x40, 22x50, 24x50, 24x60, custom | `"none"` |
| `coverslip_custom_mm` | [CoverslipSizeMm](#coverslipsizemm) or null | no | a size, only for a custom coverslip | null |
| `preparation` | string (enumerated) | yes | one of: whole_mount, section, smear, squash, strew, thin_section, polished_section, peel, cast, fluid_mount |  |
| `stain` | string or null | no | at most 80 characters | null |
| `mountant` | string or null | no | at most 80 characters | null |
| `catalogue_number` | string or null | no | at most 64 characters | null |
| `label_note` | string or null | no | at most 160 characters | null |
| `prepared_on` | string or null | no | a date YYYY, YYYY-MM or YYYY-MM-DD, from 1600 to today | null |
| `preparer` | string or null | no | at most 120 characters | null |

### SpecimenSpec

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `anchor` | [Anchor](#anchor) | yes |  |  |
| `collected_on` | string or null | no | a date YYYY, YYYY-MM or YYYY-MM-DD, from 1600 to today | null |
| `collector` | string or null | no | at most 120 characters | null |
| `locality_text` | string or null | no | at most 300 characters | null |
| `coordinates` | [Coordinates](#coordinates) or null | no |  | null |
| `geoprivacy` | string (enumerated) | no | one of: open, obscured, private | `"open"` |
| `host` | [Anchor](#anchor) or null | no | a taxon anchor | null |
| `part` | string or null | no | a part of the parts vocabulary, such as blood or feather | null |
| `preservation` | string (enumerated) | no | one of: recent, fossil, in_amber | `"recent"` |
| `type_status` | string (enumerated) or null | no | one of: holotype, paratype, allotype, syntype, lectotype, paralectotype, neotype, topotype, other | null |

### PlacementSpec

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `node` | string | yes | a node id: lowercase words joined by hyphens, levels by dots |  |
| `override_reason` | string or null | no | at most 300 characters | null |

### AssetSpec

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `family` | string (enumerated) | yes | one of: macro, micro |  |
| `role` | string (enumerated) | yes | one of: slide_overview, specimen, place, label, single, pyramid, z_plane, polarised |  |
| `upload_id` | string or null | no | an upload id, 8 to 128 characters | null |
| `remote_iiif` | string (uri) or null | no | the URL of a IIIF Image API service | null |
| `source` | [SourceSpec](#sourcespec) or null | no |  | null |
| `licence` | string | yes | a licence URI |  |
| `rights_holder` | string or null | no | at most 200 characters | null |
| `creator` | string or null | no | at most 200 characters | null |
| `pixel_size_um` | number or null | no | 0.05 to 50 um per pixel | null |
| `modality` | string (enumerated) or null | no | one of: brightfield, darkfield, phase_contrast, dic, polarised_ppl, polarised_xpl, reflected, fluorescence, sem_external | null |
| `plane` | [PlaneSpec](#planespec) or null | no |  | null |
| `polarisation` | [PolarisationSpec](#polarisationspec) or null | no |  | null |
| `exif` | [ExifSpec](#exifspec) or null | no |  | null |
| `caption` | string or null | no | at most 300 characters | null |

### SizeMm

A custom slide size.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `w_mm` | number | yes | 20 to 100 mm |  |
| `h_mm` | number | yes | 20 to 100 mm |  |

### CoverslipSizeMm

A custom coverslip size.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `w_mm` | number | yes | more than 0 and at most 100 mm |  |
| `h_mm` | number | yes | more than 0 and at most 100 mm |  |

### Anchor

What the slide shows: a taxon, a rock, a mineral, a crystal or a material.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `kind` | string (enumerated) | yes | one of: taxon, rock, mineral, crystal, material |  |
| `ref` | string | yes | 1 to 200 characters; for a taxon, its GBIF usage key |  |
| `name` | string | yes | 1 to 200 characters |  |
| `rank` | string or null | no | at most 32 characters | null |
| `classification` | string or null | no | a Nickel-Strunz code for a mineral (9, 9.A or 9.AF.15) or a snow-crystal category for ice (C, P, CP, A, R, I, G, H) | null |

### Coordinates

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `lat` | number | yes | -90 to 90 degrees |  |
| `lon` | number | yes | -180 to 180 degrees |  |
| `uncertainty_m` | number or null | no | at least 0 m | null |

### SourceSpec

Where an imported asset came from (the base collection).

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `url` | string (uri) | yes | an http or https URL |  |
| `record_id` | string | yes | 1 to 200 characters |  |
| `retrieved_on` | string (date) | yes | a date YYYY-MM-DD, not in the future |  |
| `sha256` | string | yes | 64 lowercase hexadecimal characters |  |

### PlaneSpec

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `index` | integer | yes | 0 to 10000 |  |
| `depth_um` | number | yes | -100000 to 100000 um |  |
| `stack` | string | yes | 1 to 64 letters, digits, hyphens or underscores |  |

### PolarisationSpec

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `state` | string (enumerated) | yes | one of: ppl, xpl |  |
| `angle_deg` | number | no | 0 to 360 degrees | `0.0` |

### ExifSpec

What the browser read from a photo's EXIF block, sent so the server can flag and strip.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `datetime_original` | string (date-time) or null | no | an ISO date-time | null |
| `gps_present` | boolean | no |  | `false` |
