# Catalog records (what the web reads)

<!-- Generated from contracts/catalog.schema.json by scripts/render_contract_docs.py; do not edit by hand. -->

The records the API returns: slides, pages of slides, summaries, validation results and processing jobs. Geoprivacy is already applied to every place.

Schema: [`contracts/catalog.schema.json`](../../contracts/catalog.schema.json) (JSON Schema, `https://laminario.ml.fasl-work.com/contracts/catalog.schema.json`).

### LaminarioCatalog

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `slide` | [SlideRecord](#sliderecord) | no |  |  |
| `slidePage` | [SlidePage](#slidepage) | no |  |  |
| `slideSummary` | [SlideSummary](#slidesummary) | no |  |  |
| `validation` | [ValidationResult](#validationresult) | no |  |  |
| `job` | [JobRecord](#jobrecord) | no |  |  |
| `jobEvent` | [JobEventRecord](#jobeventrecord) | no |  |  |
| `account` | [AccountRecord](#accountrecord) | no |  |  |
| `invitation` | [InvitationRecord](#invitationrecord) | no |  |  |
| `createdSlideCase` | [CreatedSlideCase](#createdslidecase) | no |  |  |
| `upload` | [UploadRecord](#uploadrecord) | no |  |  |
| `collectionTree` | [CollectionTreeRecord](#collectiontreerecord) | no |  |  |
| `collectionNode` | [CollectionNodeDetail](#collectionnodedetail) | no |  |  |
| `facet` | [FacetRecord](#facetrecord) | no |  |  |
| `anchorSuggestion` | [AnchorSuggestion](#anchorsuggestion) | no |  |  |
| `partRecord` | [PartRecord](#partrecord) | no |  |  |
| `placement` | [PlacementResult](#placementresult) | no |  |  |
| `facetCounts` | [FacetCounts](#facetcounts) | no |  |  |
| `map` | [MapRecord](#maprecord) | no |  |  |
| `annotation` | [AnnotationRecord](#annotationrecord) | no |  |  |
| `case` | [CaseRecord](#caserecord) | no |  |  |
| `caseSummary` | [CaseSummary](#casesummary) | no |  |  |
| `identifications` | [IdentificationList](#identificationlist) | no |  |  |
| `flag` | [FlagRecord](#flagrecord) | no |  |  |
| `moderationAction` | [ModerationActionRecord](#moderationactionrecord) | no |  |  |
| `profile` | [ProfileRecord](#profilerecord) | no |  |  |
| `personIdentification` | [PersonIdentificationRecord](#personidentificationrecord) | no |  |  |
| `stock` | [StockRecord](#stockrecord) | no |  |  |

### SlideRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `permalink` | string | yes |  |  |
| `qr_payload` | string | yes |  |  |
| `status` | string (enumerated) | yes | one of: `draft`, `processing`, `published`, `hidden` |  |
| `origin` | string (enumerated) | yes | one of: `base`, `contribution` |  |
| `format` | [FormatRecord](#formatrecord) | yes |  |  |
| `coverslip` | [CoverslipRecord](#coversliprecord) or null | no |  | null |
| `label` | [LabelRecord](#labelrecord) | yes |  |  |
| `anchor` | [AnchorRecord](#anchorrecord) | yes |  |  |
| `host` | [AnchorRecord](#anchorrecord) or null | no |  | null |
| `part` | string or null | no |  | null |
| `preservation` | string (enumerated) | no | one of: `recent`, `fossil`, `in_amber` | `"recent"` |
| `place` | [PlaceRecord](#placerecord) | yes |  |  |
| `placement` | [PlacementRecord](#placementrecord) | yes |  |  |
| `quality` | [QualityRecord](#qualityrecord) | yes |  |  |
| `assets` | list of [AssetRecord](#assetrecord) | yes |  |  |
| `manifest_url` | string | yes |  |  |
| `contributor` | [PersonRef](#personref) or null | no |  | null |
| `created_at` | string (date-time) | yes |  |  |
| `updated_at` | string (date-time) | yes |  |  |
| `published_at` | string (date-time) or null | no |  | null |

### SlidePage

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `items` | list of [SlideSummary](#slidesummary) | yes |  |  |
| `total` | integer | yes |  |  |
| `offset` | integer | yes |  |  |
| `limit` | integer | yes |  |  |

### SlideSummary

A slide in a list: enough to draw it in a drawer.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `permalink` | string | yes |  |  |
| `anchor` | [AnchorRecord](#anchorrecord) | yes |  |  |
| `format` | [FormatRecord](#formatrecord) | yes |  |  |
| `placement` | [PlacementRecord](#placementrecord) | yes |  |  |
| `preparation` | string | yes |  |  |
| `thumbnail_url` | string or null | no |  | null |
| `origin` | string (enumerated) | yes | one of: `base`, `contribution` |  |
| `label` | [SummaryLabel](#summarylabel) | no |  | `{"catalogue_number": null, "collected_on": null, "locality_text": null, "country": null}` |

### ValidationResult

The answer of ``POST /api/slide-cases/validate``.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `valid` | boolean | yes |  |  |
| `flags` | list of [ValidationFlag](#validationflag) | no |  | `[]` |
| `errors` | list of [ValidationError](#validationerror) | no |  | `[]` |

### JobRecord

A processing job as ``GET /api/jobs/{id}`` returns it.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `kind` | string | yes |  |  |
| `status` | string (enumerated) | yes | one of: `queued`, `running`, `succeeded`, `failed`, `cancelled` |  |
| `attempts` | integer | yes |  |  |
| `error` | string or null | no |  | null |
| `result` | object or null | no |  | null |
| `created_at` | string (date-time) | yes |  |  |
| `started_at` | string (date-time) or null | no |  | null |
| `finished_at` | string (date-time) or null | no |  | null |
| `events_url` | string | yes |  |  |

### JobEventRecord

One Server-Sent Event of a job's stream: its ``id`` field is ``seq``, its ``event`` field ``event``.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `seq` | integer | yes |  |  |
| `event` | string (enumerated) | yes | one of: `queued`, `started`, `progress`, `log`, `requeued`, `succeeded`, `failed`, `cancelled` |  |
| `data` | object | yes |  |  |
| `at` | string (date-time) | yes |  |  |

### AccountRecord

An account as ``GET /api/users/me`` returns it.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `email` | string | yes |  |  |
| `display_name` | string | yes |  |  |
| `role` | string (enumerated) | yes | one of: `contributor`, `identifier`, `curator`, `admin` |  |
| `is_active` | boolean | yes |  |  |
| `is_verified` | boolean | yes |  |  |
| `handle` | string or null | no |  | null |

### InvitationRecord

An invitation as its issuer sees it. ``link`` is present only in the answer that created it, and only when it was not mailed: the token is never stored, so it cannot be shown again.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | integer | yes |  |  |
| `email` | string or null | no |  | null |
| `role` | string (enumerated) | yes | one of: `contributor`, `identifier`, `curator`, `admin` |  |
| `note` | string or null | no |  | null |
| `status` | string (enumerated) | yes | one of: `pending`, `used`, `expired`, `revoked` |  |
| `created_at` | string (date-time) | yes |  |  |
| `expires_at` | string (date-time) | yes |  |  |
| `mailed` | boolean | yes |  |  |
| `link` | string or null | no |  | null |

### CreatedSlideCase

The answer of ``POST /api/slide-cases``: the new draft and the flags of its submission.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `status` | string | yes |  |  |
| `flags` | list of [ValidationFlag](#validationflag) | no |  | `[]` |

### UploadRecord

An upload as its contributor sees it (``GET /api/uploads``).

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | integer | yes |  |  |
| `slide_id` | string | yes |  |  |
| `asset_id` | integer | yes |  |  |
| `filename` | string or null | no |  | null |
| `size` | integer | yes |  |  |
| `wsi` | boolean | yes |  |  |
| `status` | string (enumerated) | yes | one of: `uploading`, `received`, `accepted`, `rejected`, `cancelled` |  |
| `sniffed` | string or null | no |  | null |
| `sha256` | string or null | no |  | null |
| `reason` | string or null | no |  | null |
| `job_id` | string or null | no |  | null |
| `created_at` | string (date-time) | yes |  |  |
| `finished_at` | string (date-time) or null | no |  | null |

### CollectionTreeRecord

The whole tree: the three realms and everything under them.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `realms` | list of [CollectionNodeRecord](#collectionnoderecord) | yes |  |  |
| `counts` | map of integer | yes |  |  |

### CollectionNodeDetail

One node (``GET /api/collections/{id}``): itself with its children, and the path down to it.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `node` | [CollectionNodeRecord](#collectionnoderecord) | yes |  |  |
| `path` | list of [NodeRef](#noderef) | yes |  |  |
| `iiif_collection_url` | string | yes |  |  |

### FacetRecord

A property that cuts across the tree, with the icon of each value.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string (enumerated) | yes | one of: `preparation`, `modality`, `plant-organ`, `crystal-system` |  |
| `name` | [LocalisedText](#localisedtext) | yes |  |  |
| `values` | list of [FacetValueRecord](#facetvaluerecord) | yes |  |  |

### AnchorSuggestion

A name the anchor field can offer (``GET /api/anchors/search``).

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `ref` | string | yes |  |  |
| `name` | string | yes |  |  |
| `rank` | string or null | no |  | null |
| `classification` | string or null | no |  | null |
| `context` | string or null | no |  | null |

### PartRecord

A part of an organism the part field offers (``GET /api/vocab/parts``), with its organ system.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `group` | string | yes |  |  |
| `name` | [LocalisedText](#localisedtext) | yes |  |  |

### PlacementResult

Where a slide belongs (``POST /api/placement``): the suggestion, and every node that accepts it.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `anchor` | [AnchorRecord](#anchorrecord) or null | no |  | null |
| `suggestion` | string or null | no |  | null |
| `path` | list of [NodeRef](#noderef) | no |  | `[]` |
| `accepting` | list of string | no |  | `[]` |
| `errors` | list of [ValidationError](#validationerror) | no |  | `[]` |

### FacetCounts

For each facet, its values under the current filters and how many slides each would match (the facet's own filter left out, so a second value shows what it adds).

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `collection` | map of integer | no |  | `{}` |
| `kind` | map of integer | no |  | `{}` |
| `preparation` | map of integer | no |  | `{}` |
| `modality` | map of integer | no |  | `{}` |
| `preservation` | map of integer | no |  | `{}` |
| `country` | map of integer | no |  | `{}` |
| `licence` | map of integer | no |  | `{}` |
| `wsi` | map of integer | no |  | `{}` |
| `origin` | map of integer | no |  | `{}` |

### MapRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `countries` | map of integer | yes |  |  |
| `points` | list of [MapPointRecord](#mappointrecord) | yes |  |  |
| `total` | integer | yes |  |  |

### AnnotationRecord

An annotation as the stage reads it: the W3C Web Annotation, who wrote it, and whether the reader may remove it (its author, or a curator).

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `asset_id` | integer | yes |  |  |
| `author` | string | yes |  |  |
| `removable` | boolean | no |  | `false` |
| `annotation` | object | yes |  |  |

### CaseRecord

A contributor's case to reopen (``GET /api/slide-cases/{id}``): its summary and the case as last sent.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `status` | string (enumerated) | yes | one of: `draft`, `processing`, `published`, `hidden` |  |
| `status_reason` | string or null | no |  | null |
| `name` | string | yes |  |  |
| `placement` | string | yes |  |  |
| `updated_at` | string (date-time) | yes |  |  |
| `images` | list of [CaseImageRecord](#caseimagerecord) | no |  | `[]` |
| `submission` | object | no |  | `{}` |

### CaseSummary

A contributor's slide case in their list (``GET /api/slide-cases``).

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `status` | string (enumerated) | yes | one of: `draft`, `processing`, `published`, `hidden` |  |
| `status_reason` | string or null | no |  | null |
| `name` | string | yes |  |  |
| `placement` | string | yes |  |  |
| `updated_at` | string (date-time) | yes |  |  |
| `images` | list of [CaseImageRecord](#caseimagerecord) | no |  | `[]` |

### IdentificationList

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `community` | [CommunityRecord](#communityrecord) | yes |  |  |
| `identifications` | list of [IdentificationRecord](#identificationrecord) | yes |  |  |

### FlagRecord

A flag as the curators see it (``GET /api/flags``).

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `target_kind` | string (enumerated) | yes | one of: `slide`, `identification`, `annotation` |  |
| `target_id` | string | yes |  |  |
| `slide_id` | string | yes |  |  |
| `slide_name` | string | yes |  |  |
| `category` | string (enumerated) | yes | one of: `spam`, `inappropriate`, `copyright`, `wrong`, `other` |  |
| `comment` | string or null | no |  | null |
| `by` | string or null | no |  | null |
| `created_at` | string (date-time) | yes |  |  |
| `resolved_by` | string or null | no |  | null |
| `resolved_at` | string (date-time) or null | no |  | null |
| `resolution` | string or null | no |  | null |
| `hidden` | boolean | no |  | `false` |

### ModerationActionRecord

A curator's hiding or restoring, with the reason.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `action` | string (enumerated) | yes | one of: `hide`, `unhide` |  |
| `target_kind` | string (enumerated) | yes | one of: `slide`, `identification`, `annotation` |  |
| `target_id` | string | yes |  |  |
| `slide_id` | string | yes |  |  |
| `reason` | string | yes |  |  |
| `by` | string or null | no |  | null |
| `created_at` | string (date-time) | yes |  |  |

### ProfileRecord

An account's profile (``GET /api/people/{handle}``): never its email.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `handle` | string | yes |  |  |
| `name` | string | yes |  |  |
| `role` | string (enumerated) | yes | one of: `contributor`, `identifier`, `curator`, `admin` |  |
| `joined` | string (date-time) | yes |  |  |
| `last_active` | string (date-time) or null | no |  | null |
| `slides` | integer | yes |  |  |
| `verified` | integer | yes |  |  |
| `by_collection` | map of integer | no |  |  |
| `identifications` | integer | yes |  |  |
| `categories` | map of integer | no |  |  |
| `annotations` | integer | yes |  |  |

### PersonIdentificationRecord

One of an account's identifications, in its cabinet.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `slide` | [SlideSummary](#slidesummary) | yes |  |  |
| `anchor` | [AnchorRecord](#anchorrecord) | yes |  |  |
| `category` | string (enumerated) or null | no | one of: `leading`, `improving`, `supporting`, `maverick` | null |
| `community` | boolean | yes |  |  |
| `created_at` | string (date-time) | yes |  |  |

### StockRecord

A label stock a sheet is printed on (``GET /api/labels/stocks``).

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `name` | [LocalisedText](#localisedtext) | yes |  |  |
| `kind` | string (enumerated) | yes | one of: `plain`, `stock` |  |
| `page` | string (enumerated) | yes | one of: `A4`, `Letter` |  |
| `width_mm` | number | yes |  |  |
| `height_mm` | number | yes |  |  |
| `columns` | integer | yes |  |  |
| `rows` | integer | yes |  |  |
| `per_sheet` | integer | yes |  |  |
| `source` | string | yes |  |  |
| `warnings` | list of string | no |  |  |

### FormatRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `code` | string | yes |  |  |
| `width_mm` | number | yes |  |  |
| `height_mm` | number | yes |  |  |
| `assumed` | boolean | no |  | `false` |

### CoverslipRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `code` | string | yes |  |  |
| `long_mm` | number | yes |  |  |
| `short_mm` | number | yes |  |  |

### LabelRecord

What the printed label shows.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `name` | string | yes |  |  |
| `catalogue_number` | string or null | no |  | null |
| `preparation` | string | yes |  |  |
| `stain` | string or null | no |  | null |
| `mountant` | string or null | no |  | null |
| `label_note` | string or null | no |  | null |
| `prepared_on` | string or null | no |  | null |
| `preparer` | string or null | no |  | null |
| `collected_on` | string or null | no |  | null |
| `collector` | string or null | no |  | null |
| `locality_text` | string or null | no |  | null |
| `type_status` | string or null | no |  | null |

### AnchorRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `kind` | string (enumerated) | yes | one of: `taxon`, `rock`, `mineral`, `crystal`, `material` |  |
| `ref` | string | yes |  |  |
| `name` | string | yes |  |  |
| `rank` | string or null | no |  | null |
| `classification` | string or null | no |  | null |

### PlaceRecord

Where the specimen was collected, after geoprivacy.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `geoprivacy` | string (enumerated) | yes | one of: `open`, `obscured`, `private` |  |
| `point` | [PointRecord](#pointrecord) or null | no |  | null |
| `cell` | [CellRecord](#cellrecord) or null | no |  | null |
| `uncertainty_m` | number or null | no |  | null |
| `locality_text` | string or null | no |  | null |
| `country` | string or null | no |  | null |

### PlacementRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `node` | string | yes |  |  |
| `overridden` | boolean | no |  | `false` |

### QualityRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `badge` | string (enumerated) | yes | one of: `verified`, `needs_id`, `reference` |  |
| `checks` | list of [QualityCheckRecord](#qualitycheckrecord) | yes |  |  |
| `community_node` | string or null | no |  | null |
| `community_rank` | string or null | no |  | null |

### AssetRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | integer | yes |  |  |
| `family` | string (enumerated) | yes | one of: `macro`, `micro` |  |
| `role` | string | yes |  |  |
| `sort_order` | integer | yes |  |  |
| `status` | string (enumerated) | yes | one of: `pending`, `ready`, `failed` |  |
| `media` | [MediaRecord](#mediarecord) | yes |  |  |
| `pixel_size_um` | number or null | no |  | null |
| `modality` | string or null | no |  | null |
| `plane` | [PlaneRecord](#planerecord) or null | no |  | null |
| `polarisation` | [PolarisationRecord](#polarisationrecord) or null | no |  | null |
| `caption` | string or null | no |  | null |
| `licence` | [LicenceRecord](#licencerecord) | yes |  |  |
| `rights_holder` | string or null | no |  | null |
| `creator` | string or null | no |  | null |
| `source` | [SourceRecord](#sourcerecord) or null | no |  | null |
| `original_sha256` | string or null | no |  | null |

### PersonRef

An account as others may see it: its handle and display name, never its email (U14).

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `handle` | string | yes |  |  |
| `name` | string | yes |  |  |

### SummaryLabel

What a drawer shows on a slide's label end (no coordinates, so nothing geoprivacy withholds).

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `catalogue_number` | string or null | no |  | null |
| `collected_on` | string or null | no |  | null |
| `locality_text` | string or null | no |  | null |
| `country` | string or null | no |  | null |

### ValidationFlag

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `code` | string | yes |  |  |
| `field` | string | yes |  |  |
| `message` | string | yes |  |  |
| `params` | map of string | no |  | `{}` |

### ValidationError

A reason a slide case is refused: the field, the API's message and what would be accepted, and a stable code with the values the message names, so an interface can say it in its own words (R-1202).

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `field` | string | yes |  |  |
| `message` | string | yes |  |  |
| `expected` | string | yes |  |  |
| `code` | string or null | no |  | null |
| `params` | map of string | no |  | `{}` |

### CollectionNodeRecord

A node of the collection tree (``GET /api/collections``), with its published slides counted.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `level` | string (enumerated) | yes | one of: `realm`, `collection`, `sub-collection`, `group` |  |
| `name` | [LocalisedText](#localisedtext) | yes |  |  |
| `about` | [LocalisedText](#localisedtext) | yes |  |  |
| `icon` | string | yes |  |  |
| `view` | boolean | no |  | `false` |
| `priority` | integer | no |  | `0` |
| `defined_by` | list of [DefinitionRecord](#definitionrecord) | no |  | `[]` |
| `slide_count` | integer | no |  | `0` |
| `children` | list of [CollectionNodeRecord](#collectionnoderecord) | no |  | `[]` |

### NodeRef

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `name` | [LocalisedText](#localisedtext) | yes |  |  |
| `icon` | string | yes |  |  |

### LocalisedText

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `en` | string | yes |  |  |
| `es` | string | yes |  |  |

### FacetValueRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `name` | [LocalisedText](#localisedtext) | yes |  |  |
| `icon` | string | yes |  |  |

### MapPointRecord

A slide on the map, after geoprivacy: an obscured one at its public point, with its 0.2 degree cell.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `lat` | number | yes |  |  |
| `lon` | number | yes |  |  |
| `obscured` | boolean | no |  | `false` |
| `cell` | [CellRecord](#cellrecord) or null | no |  | null |

### CaseImageRecord

An image of a contributor's case: its state, and its file's (the last upload).

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `asset_id` | integer | yes |  |  |
| `token` | string or null | no |  | null |
| `family` | string (enumerated) | yes | one of: `macro`, `micro` |  |
| `role` | string | yes |  |  |
| `status` | string (enumerated) | yes | one of: `pending`, `ready`, `failed` |  |
| `failure` | string or null | no |  | null |
| `has_file` | boolean | no |  | `false` |
| `upload_status` | string or null | no |  | null |
| `upload_reason` | string or null | no |  | null |
| `upload_job` | string or null | no |  | null |

### CommunityRecord

How the identifications agree (R-088): the node, its anchor when Laminario can name it, and every score.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `node` | string or null | no |  | null |
| `anchor` | [AnchorRecord](#anchorrecord) or null | no |  | null |
| `identifications` | integer | yes |  |  |
| `score` | number or null | no |  | null |
| `cutoff` | number | yes |  |  |
| `scores` | list of [NodeScoreRecord](#nodescorerecord) | no |  |  |
| `as_good_as_it_can_be` | integer | no |  | `0` |
| `needs_more` | integer | no |  | `0` |
| `my_vote` | boolean or null | no |  | null |
| `badge` | string (enumerated) | yes | one of: `verified`, `needs_id`, `reference` |  |

### IdentificationRecord

An identification on a slide, as a viewer may see it (``GET /api/slides/{id}/identifications``).

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `id` | string | yes |  |  |
| `anchor` | [AnchorRecord](#anchorrecord) | yes |  |  |
| `node` | string | yes |  |  |
| `by` | string or null | no |  | null |
| `by_handle` | string or null | no |  | null |
| `source` | boolean | no |  | `false` |
| `mine` | boolean | no |  | `false` |
| `body` | string or null | no |  | null |
| `disagreement` | boolean or null | no |  | null |
| `current` | boolean | yes |  |  |
| `hidden` | boolean | no |  | `false` |
| `category` | string (enumerated) or null | no | one of: `leading`, `improving`, `supporting`, `maverick` | null |
| `created_at` | string (date-time) | yes |  |  |

### PointRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `lat` | number | yes |  |  |
| `lon` | number | yes |  |  |

### CellRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `south` | number | yes |  |  |
| `west` | number | yes |  |  |
| `north` | number | yes |  |  |
| `east` | number | yes |  |  |

### QualityCheckRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `code` | string (enumerated) | yes | one of: `licence_and_provenance`, `scale`, `modality`, `macro_and_micro` |  |
| `passed` | boolean | yes |  |  |
| `detail` | string | yes |  |  |

### MediaRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `kind` | string (enumerated) | yes | one of: `pyramid`, `image`, `remote_iiif` |  |
| `iiif_info_url` | string or null | no |  | null |
| `image_url` | string or null | no |  | null |
| `iiif_version` | enumerated or null | no | one of: `2`, `3` | null |
| `width_px` | integer or null | no |  | null |
| `height_px` | integer or null | no |  | null |

### PlaneRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `stack` | string | yes |  |  |
| `index` | integer | yes |  |  |
| `depth_um` | number | yes |  |  |

### PolarisationRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `state` | string (enumerated) | yes | one of: `ppl`, `xpl` |  |
| `angle_deg` | number | yes |  |  |

### LicenceRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `uri` | string | yes |  |  |
| `short_name` | string | yes |  |  |

### SourceRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `url` | string | yes |  |  |
| `record_id` | string | yes |  |  |
| `retrieved_on` | string (date) | yes |  |  |
| `sha256` | string | yes |  |  |

### DefinitionRecord

One condition of a node's rule, for people: a taxon with its GBIF page, a rock family, a part.

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `kind` | string (enumerated) | yes | one of: `taxon`, `excluded-taxon`, `kind`, `rock`, `mineral`, `crystal`, `material`, `part`, `preservation`, `relation` |  |
| `value` | string | yes |  |  |
| `label` | string | yes |  |  |
| `url` | string or null | no |  | null |

### NodeScoreRecord

| Field | Type | Required | Accepted | Default |
|---|---|---|---|---|
| `node` | string | yes |  |  |
| `depth` | integer | yes |  |  |
| `cumulative` | integer | yes |  |  |
| `disagreements` | integer | yes |  |  |
| `ancestor_disagreements` | integer | yes |  |  |
| `score` | number | yes |  |  |
