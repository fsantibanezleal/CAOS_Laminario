# U12 · Contribute · design

The research is dossier 14 of the planning record (and dossier 05, section 4, for the flow). How the parts fit is the
wiki page [14 Contribute](../../../architecture/14_contribute.md). This page records the unit's decisions.

## What the unit delivers

| Part | Where |
|---|---|
| Codes and parameters on every validation error and flag | `app/contracts/ingest.py`, `app/contracts/errors.py`, `app/collections/service.py` |
| The case's lifecycle: submit, publication when processed, back to draft on failure, the contributor's drafts | `app/services/cases.py`, `app/routers/cases.py`, `app/jobs/kinds.py`, migration 0010 |
| A private case's files refused while they carry a GPS position | `app/uploads/verify.py` |
| The account places: sign in, join from an invitation, reset a password, sign out | `frontend/src/places/account/` |
| The contribute place and its parts: the case form, images with their EXIF, the location routine, calibration, anchor and placement, uploads over tus, processing progress | `frontend/src/places/contribute/`, `frontend/src/contribute/` |
| The end-to-end gate | `frontend/gates/contribute.mjs` |

## Decisions

- **Validation speaks the page's language through codes.** The API's messages stay English for any client; every
  error and flag also carries a stable code (a rule's name, or `type.<pydantic type>` for a field's form) and its
  parameters, and the interface writes the message for the code in English or Spanish, falling back to the server's
  text for a code it does not know. The field a message names is where it is shown.
- **The case is created whole, then filled with files.** The server validates the entire case before it stores the
  draft (as U1 designed); the contribute place validates as the contributor goes (`/api/slide-cases/validate`) and
  keeps an unsent case on the device until it is valid. Once created, the draft is the server's, listed at
  `/contribute` and reopened at `/contribute/<id>`; a change replaces the draft's record (its images and files kept
  where they did not change); deleting a draft deletes its uploads.
- **Uploads use Uppy's core with its tus plugin, headless.** Laminario draws the files, their progress and their
  pause and resume itself; Uppy keeps the queue, retries with back-off and resumes an interrupted file from the
  offset tusd kept. The tus metadata are the draft's short id, the image's id and the file name, as the pre-create
  hook requires. A scanner file goes in chunks of 50 MB.
- **A photograph's location is shown, then removed when private (R-087).** exifr reads the date, the orientation and
  the GPS position in the browser; the position is shown on a small map beside the photograph. For a private case the
  file is rewritten before upload: the GPS IFD of its TIFF-structured EXIF block emptied (entry count 0, entries and
  values zeroed) and every XMP packet removed, in JPEG, PNG, WebP and TIFF, the image data, date and orientation kept
  (R-1204). The server does not trust it: verification refuses a private case's file that still has a position
  (R-1203). An obscured case keeps the position in the file (the original is never served; derivatives carry no
  EXIF) and publishes only its cell.
- **The pixel size is typed, read, or calibrated.** A scanner file's comes from the reader; for a photograph through a
  microscope the contributor types it, or clicks both ends of a known length on a stage micrometer photograph (not
  uploaded): $p = d/n$, with its one-pixel uncertainty $\pm 2p/n$ shown (R-1207).
- **Publication is automatic, and a failure is said.** Submitting moves a complete draft to processing; when the last
  image is processed the case is published; an image that fails verification or processing returns the case to draft
  with the reason on that image, where a new file can replace it (R-1205). Accounts are invitation-only; the curators'
  hiding and restoring come with U13.
- **The account places are small and plain.** Sign in, join from an invitation link (the invitation names the role;
  an invitation for an address requires it), forgot and reset, sign out; the masthead names the signed-in account and
  offers Contribute to those who may.
