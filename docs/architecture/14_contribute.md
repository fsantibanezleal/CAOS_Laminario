# 14 · Contribute

![The contribute flow: in the browser the case is filled section by section while the server validates it and answers with coded messages; photographs are read by exifr and, in a private case, rewritten without their position; a pixel size can be calibrated on a stage micrometer; the files go to tusd through Uppy's tus plugin, are verified (a private case's photograph with a position is refused) and processed into pyramids that keep the original's SHA-256; the case goes from draft to processing to published, or back to draft when an image fails, and job events stream back to the page](svg/contribute.svg)

A contributor turns a physical slide into a record of the collection: what it shows, the slide as an object, its
images, where the specimen was found, and the drawer it goes to. The research, with the libraries measured and the
formats read, is dossier 14 of the planning record (and dossier 05, section 4, for the flow); the requirements are
R-087 and R-1201 to R-1208 ([U12 requirements](../design/features/u12-contribute/requirements.md)); the decisions are in
the [U12 design](../design/features/u12-contribute/design.md).

## 1. Accounts in the interface

Accounts are invitation-only (U6). The account places are one short form each (R-1201):

| Address | Does | API |
|---|---|---|
| `/join?token=` | opens the account the invitation names, then signs in | `POST /api/auth/register`, then `/api/auth/login` |
| `/signin?next=` | signs in and returns to where the visitor was going (a path of this site only) | `POST /api/auth/login` (a form: `username`, `password`) |
| `/forgot-password` | asks for a reset link; the answer never says whether the address has an account | `POST /api/auth/forgot-password` (always 202) |
| `/reset-password?token=` | sets the new password (the link lives one hour) | `POST /api/auth/reset-password` |

The masthead names the signed-in account; its disclosure lists the account's contributions and signs out
(`POST /api/auth/logout`), and the way in named Contribute appears for the roles that may submit. The session is read
once from `GET /api/session` and again after signing in or out; the page mirrors the roles' capabilities
(`app/accounts/roles.py`) only to offer what the server allows, and the server checks every request.

A refusal has a code the page words in its language: fastapi-users answers `LOGIN_BAD_CREDENTIALS` or
`{code: RESET_PASSWORD_BAD_TOKEN}`, and the registration route answers the same shape (`REGISTER_INVITATION_INVALID`,
`REGISTER_INVITATION_OTHER_EMAIL`, `REGISTER_USER_ALREADY_EXISTS`, `REGISTER_INVALID_PASSWORD` with the reason). The
password rules (at least 12 characters, not the email's local part) are checked in the page first, so their words are
the page's own; the server's reason is the fallback.

## 2. The case, section by section

`/contribute` lists the contributor's cases (R-1206): drafts to finish, cases being processed, the slides they
became, each with its state, its files and the reason a failed image gave. `/contribute/new` and `/contribute/<id>`
edit one case in six sections, with the slide drawn to scale beside the form as it is described:

1. **What it shows**: the kind (an organism, a rock, a mineral, a crystal, a material), then the name from the
   server's suggestions (`GET /api/anchors/search`: GBIF backbone taxa, or the vocabularies). An organism also takes
   the part on the slide (the 53 parts of `GET /api/vocab/parts`, grouped by organ system), its preservation, a host
   and a type status; then when and by whom it was collected.
2. **The slide**: the format (each drawn to scale), a custom size, the coverslip, the preparation (named and drawn as
   the collection's facet), the stain and the mountant, the catalogue number, the label's note, when and by whom it
   was prepared.
3. **Images**: macro photographs and micro images, chosen or dropped; a scanner file is recognised by its extension
   and taken as a whole-slide image; an image already served by a IIIF service is named by its address. Each image
   has its role, licence (CC BY, BY-SA, BY-NC, BY-NC-SA 4.0 and CC0; BY and BY-SA 3.0 for an image already published
   under one), author, and for a micro image its illumination, pixel size (section 4), and its place in a focal stack
   or a polarised pair.
4. **The place**: the locality in words; the point by a click on the map (the explore map's style), a photograph's
   position, or typed; its uncertainty (drawn as a circle); the country; and who may see the place (section 3).
5. **The drawer**: the tree's suggestion for the anchor, its part and its preservation (`POST /api/placement`), with
   every other drawer that accepts the slide; a curator may place it elsewhere with a reason.
6. **Review and send**: the case read back, what still stops it (each message with the way to its field), what the
   server only notes, then the draft stored, the files sent, the case submitted (section 5).

**Validation speaks the page's language (R-1202).** The form sends the case as it stands to
`POST /api/slide-cases/validate` 600 ms after the last change. Every error and flag carries its field path, the
server's English message, a stable code and its parameters: a rule's name (`coverslip_too_large` with the slide's
`width` and `height`), or `type.<pydantic type>` for a field's form (`type.string_too_long` with `max_length`). The
page writes `validation.<code>` in English or Spanish with the parameters filled, falling back to the server's words
for a code it does not know, and shows it by the field the path names; a section's messages appear once the
contributor has been through it, and all of them on storing. A number typed wrong travels as typed, so the server
names the field rather than receiving an empty value. Until it is stored, the case is kept on the device; the files
cannot be (a browser does not keep a chosen file across a reload), so after a reload each image asks for its file.

## 3. The location of a photograph (R-087, R-1203, R-1204)

exifr 7.1.3 reads a photograph's date, orientation and GPS position in the browser before anything is sent; the
position is shown on the image and on the place's map, where a click adopts it. For WebP, which exifr does not parse,
the page hands it the EXIF chunk's TIFF block. Only the head of a large file is read, so a scanner file is never
loaded whole. Where the position lives in each format the server accepts:

| Format | GPS | XMP |
|---|---|---|
| JPEG | the APP1 `Exif` segment: a TIFF block whose first directory points (tag 0x8825) to the GPS directory | another APP1 segment (and extended XMP) |
| PNG | the `eXIf` chunk (a TIFF block) | an `iTXt` chunk keyed `XML:com.adobe.xmp` |
| WebP | the `EXIF` chunk (a TIFF block) | the `XMP ` chunk, flagged in `VP8X` |
| TIFF | the file's own first directory | tag 700 |

**Geoprivacy.** *Everyone* sees the point; *only its area* shows the 0.2 degree cell it lies in (about 22 km); *no
one* shows no place. In a private case the location routine (`frontend/src/contribute/location.ts`) rewrites each
photograph before upload, on its bytes and without decoding the image: every GPS directory's entry count is set to 0
and its entries and their out-of-line values zeroed (so no coordinate stays in the file), every XMP packet is removed
(zeroed inside a TIFF), the PNG chunk's CRC-32 is computed again, and the WebP RIFF size and `VP8X` flag follow. The
image data, the date and the orientation are kept. The server does not trust it: the verify job refuses a private
case's JPEG, PNG, WebP or TIFF that still carries a position (it reads the EXIF `GPSInfo` fields, or the TIFF
`GPSTag`), and says why. An obscured case keeps the position in its stored original, which is never served;
derivatives carry no EXIF.

## 4. The pixel size (R-1207)

A scanner file states its pixel size and the reader finds it. A photograph through a microscope does not: the
contributor types it (micrometres per pixel, from the camera and the objective) or calibrates it on a photograph of a
stage micrometer taken with the same camera and objective. Two points marked at the ends of a known length $d$, $n$
pixels apart, give

$$p = \frac{d}{n}\ \mathrm{\mu m\ per\ pixel}.$$

Each end is uncertain by one pixel, so $n$ is uncertain by two, and

$$\delta p = \left|\frac{\partial p}{\partial n}\right| \cdot 2 = \frac{2d}{n^2} = \frac{2p}{n}, \qquad
\frac{\delta p}{p} = \frac{2}{n}.$$

A calibration over too short a length is visibly poor: 100 um across 400 pixels gives $0.2500 \pm 0.0013$ um per
pixel (0.5 %), the same length across 30 pixels $3.33 \pm 0.22$ (6.7 %), and the dialog warns above 1 %. The value is
written with its uncertainty to two significant figures and the value to the same decimal place (the GUM's usual
rule, JCGM 100:2008, section 7.2.6), and must fall in the contract's 0.05 to 50 um per pixel. The micrometer
photograph is drawn at its own pixels in a zoomable frame (a click on a shrunken picture cannot be finer than the
pixels it hides); the ends are placed by a click, moved one pixel at a time with the arrow keys, or typed. It never
leaves the device.

## 5. From draft to published (R-1205, R-1206, R-1208)

| Route | Who | Does |
|---|---|---|
| `POST /api/slide-cases` | a contributor | validates the whole case and stores it as a draft, with an image row per asset |
| `GET /api/slide-cases`, `GET /api/slide-cases/{id}` | its contributor | the list, and one case with the submission as last sent and each image's file state |
| `PUT /api/slide-cases/{id}` | its contributor, a draft | replaces the record; an image still named by its token keeps its file, one no longer named leaves with its uploads |
| `DELETE /api/slide-cases/{id}` | its contributor, a draft | deletes the draft, its uploads and its files |
| `POST /api/slide-cases/{id}/submit` | its contributor, a draft whose images all have their file | draft to processing |

Anyone else's case is not found: it is not theirs to know. **The files** go through tusd (tus 1.0) at `/files/`,
sent by Uppy's core 6.1.0 with its tus plugin 6.0.0, headless: Laminario draws the files, their progress and their
pause and resume; Uppy keeps the queue, retries with back-off (0, 1, 3, 5, 10 and 20 s) and resumes an interrupted file
from the offset tusd kept, which tus-js-client finds again by the file's fingerprint after a reload. A scanner file
goes in chunks of 50 MB. The upload's metadata name the draft (`slide`) and the image (`asset`); the pre-create hook
checks the session (tusd forwards the cookie), the ownership, the quotas and the free disk. The verify job checks
the file (size, SHA-256, its kind by content, safe unpacking, header limits, a private case's position) and, once
accepted, queues the process job, which builds the pyramid and records the original's SHA-256 on the image.

The page follows each image's jobs by their Server-Sent Events (`GET /api/jobs/{id}/events`: the verification's
checksum, kind and header, then the processing's reading, pyramid and storing) and reads the case again every two
seconds while anything is in flight. After every job of a case the worker checks it: when every image is ready and
no job is left, a processing case is published; when an image failed, the case goes back to draft with the reason on
the image and on the case, where a new file can replace it. Accounts are invitation-only, so publication is
automatic; the curators' hiding and restoring come with U13. The published slide shows each image's original SHA-256
in its provenance, so anyone holding the file can check it is the one shown.

## 6. Gates and tests

| Gate | Checks |
|---|---|
| `tests/contracts/test_error_codes.py` | every rule and every field error has a stable code and its parameters (R-1202) |
| `frontend/src/contribute/messages.test.ts` | every code the server names has words in both languages; unknown codes fall back to the message (R-1202) |
| `tests/uploads/test_location.py` | a private case's photograph with a position is refused with the reason; emptied, it is accepted; an open case keeps it (R-1203) |
| `frontend/src/contribute/location.test.ts`, `photo.test.ts` | JPEG, PNG, WebP and TIFF rewritten without position and XMP, image data, date and orientation kept, read back with exifr (R-1204, R-087) |
| `tests/contribute/test_lifecycle.py` | draft, processing, published, back to draft with the reason; a contributor's own drafts only (R-1205, R-1206) |
| `frontend/src/contribute/calibration.test.ts` | $d/n$ and $2p/n$, the units, a short calibration visibly poor, the written value (R-1207) |
| `frontend/src/contribute/draft.test.ts` | the form to the contract and back, messages placed by field |
| `tests/uploads/test_tus.py` | the image keeps its original's SHA-256 (R-1208) |
| `frontend/gates/contribute.mjs` | end to end in the browser, in its own sandbox (API, worker, tusd, the preview): an invitation, joining, signing out and in, a wrong password refused; a case filled by pointer with CMU-1 (178 MB) and a real photograph carrying GPS in a private case; the position shown, then absent from the stored file with its date kept; upload, verification, processing, publication; the slide opened with CMU-1's SHA-256 (R-087, R-1201, R-1208) |
