# U5 · Resumable uploads · design

The flow, with its diagram, is in the wiki page [08 Uploads](../../../architecture/08_uploads.md); the research is
dossier 08 of the planning record. This page records the unit's decisions.

## What the unit delivers

| Part | Where |
|---|---|
| The `upload` table | migration 0005, `app/db/models.py` |
| Content sniffing | `app/uploads/sniff.py` |
| The pre-create policy: ownership, sizes, quotas, the whole-slide disk budget | `app/uploads/policy.py` |
| The hook endpoint and the contributor's upload records | `app/routers/uploads.py` |
| The verification job | `verify_upload` in `app/jobs/kinds.py` |
| tusd, pinned, for production | `deploy/tusd/compose.yaml` |
| nginx's `/files/` location | `deploy/nginx/laminario.conf` |
| The upload record of the catalog contract | `UploadRecord` and its TypeScript type |

## Decisions

- **tusd v2.10.1** (MIT), the tus 1.0 reference server: resumable by protocol (`HEAD` returns the offset, `PATCH`
  continues from it), so a dropped connection costs only the bytes in flight. Production runs the official image
  pinned by digest with host networking on loopback, a read-only root and the quarantine mounted at the same path
  it has on the host (the paths tusd reports are then valid for the worker). Tests start the verified release binary
  (Windows and Linux) with the same flags.
- **Hooks over HTTP with the session forwarded** (`-hooks-http-forward-headers Cookie`): the API authenticates the
  uploader with its normal session; no upload tokens.
- **Refusals are hook answers, not HTTP errors.** tusd turns a non-2xx hook answer into a bare 500 for the client, so
  pre-create answers 200 with `RejectUpload` and an `HTTPResponse` carrying the status and the reason (401, 403,
  404, 409, 413, 507).
- **pre-create decides before any byte is stored**: the uploader may submit and owns the draft, the asset is
  pending and not remote, no other upload for it is in progress, the length is declared, within 30 GB per file,
  within the account's 40 GB and 20 whole-slide images, and, for whole-slide images, the data volume is below
  90 percent (R-042, R-043, R-502). A whole-slide image is a scanner extension or a file of 1 GB or more.
- **Verification is a worker job, not a hook.** post-finish only marks the upload received and queues
  `verify_upload`; hashing a multi-gigabyte file does not fit a hook with a 15-second timeout. The job checks the size,
  computes the SHA-256, sniffs the bytes, unpacks ZIP archives safely (no absolute or parent paths, at most four
  times the upload limit), asks the U2 reader for the header (its dimension limits apply), moves the file to the
  source store (`sources/{slide}/{asset}-{digest}`, scanner extensions kept because OpenSlide needs them), sets the
  asset's `source_path` and queues `process_asset` (R-040). A refused file is deleted from quarantine and the reason
  names what was found and what is accepted (R-041).
- **Types from bytes, never from names**: magic numbers for JPEG, PNG, WebP, TIFF, BigTIFF and DICOM; for ZIP, the
  names inside (MRXS, VSI, DICOM); common wrong files (executables, PDF, GIF, other archives, video) are named in the
  refusal. Readability is the reader's decision after sniffing.
- **The worker's deadline.** `Worker.run` accepts a deadline; the service runs without one. Tests use it, after a
  box run showed that tusd delivers post-finish after it has answered the client, so a test must wait for the
  hook before stopping tusd.

## Interfaces used by later units

- U12 (contribute): Uppy over tus with `slide`, `asset` and `filename` metadata; the upload record and the job's
  event stream for progress; the refusal reasons shown as they are.
- U16 (deploy): the tusd compose file, the quarantine and sources folders on the volume owned by the service account,
  nginx's `/files/`, port 8148 checked free.
