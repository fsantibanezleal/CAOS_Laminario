# 08 · Uploads

![Uploads: the browser sends a tus upload through nginx to tusd; the pre-create hook decides before any byte is stored; after the last byte a worker job verifies the file and hands it to processing](svg/uploads.svg)

A scanner file can weigh several gigabytes and a contributor's connection can drop. Laminario receives files with
tus 1.0, the open protocol for resumable uploads, through tusd, its reference server; the API decides through tusd's
hooks who may upload what, and the worker checks every finished file before anything else touches it.

## 1. The protocol

A tus upload is created with its length, then filled in chunks at explicit offsets:

| Request | Meaning |
|---|---|
| `POST /files/` with `Upload-Length` and `Upload-Metadata` | create an upload; the answer's `Location` names it |
| `PATCH <location>` with `Upload-Offset: n` | append bytes from offset `n` |
| `HEAD <location>` | how many bytes arrived (`Upload-Offset`) |

When a connection drops, the client asks `HEAD` and continues with `PATCH` from that offset, so only the bytes in
flight are sent again. The gate measures exactly that: it announces a whole file, sends half, drops the connection,
reads the offset tusd kept, sends the rest, and the stored file has the original's SHA-256 (R-040).

Laminario's metadata is `slide` (the draft's short id), `asset` (the image in it) and `filename`.

## 2. Before any byte is stored: the pre-create hook

tusd forwards the client's `Cookie` to the API's hook, so the uploader is authenticated by its normal session. The
upload is refused, with a status and a reason the client receives as they are, when:

| Condition | Status |
|---|---|
| no session | 401 |
| the role cannot submit, or the slide case is someone else's | 403 |
| the image is not in the case, or is a remote IIIF service | 404 |
| the case is not a draft, the image already has its file, or another upload for it is in progress | 409 |
| no declared length, or an empty file | 400 |
| more than 30 GB, or over the account's quota (40 GB and 20 whole-slide images) | 413 |
| a whole-slide image while the data volume is more than 90 percent full | 507 |

A whole-slide image is a file with a scanner extension (SVS, NDPI, VMS, SCN, MRXS, VSI, BIF, DICOM, ZIP, ...) or of
1 GB or more. The quotas count uploads in progress and accepted; refused and cancelled ones free their share. The
disk rule is the design document's tier-A rule: photographs still go when whole-slide images cannot (R-043).

tusd turns any non-2xx hook answer into a bare 500, so refusals are 200 answers carrying `RejectUpload` and the
response to send.

## 3. After the last byte: verification

The post-finish hook only marks the upload received and queues a `verify_upload` job: hashing a multi-gigabyte file
does not fit a hook that tusd abandons after 15 seconds. The job:

1. checks that the size is the declared one and computes the SHA-256;
2. sniffs the type from the bytes, never from the name: JPEG, PNG, WebP, TIFF (plain TIFF, SVS, NDPI, SCN, Philips
   TIFF), BigTIFF and DICOM by their magic numbers, and ZIP archives by the names inside (MRXS, VSI or DICOM slides);
3. unpacks archives safely: no absolute or parent paths, at most four times the upload limit in total;
4. asks the imaging engine's reader for the header, with its dimension limits;
5. moves the file to `sources/{slide}/{asset}-{digest}` (scanner extensions kept, because OpenSlide recognises some
   formats by them), records the source on the asset and queues its processing.

A file that fails any step is deleted from quarantine and the upload records why, naming what was found and what is
accepted: "the file is a Windows executable; accepted are JPEG, PNG, WebP, TIFF or BigTIFF (SVS, NDPI, SCN,
Philips), DICOM, and MRXS, VSI or DICOM slides in a ZIP archive" (R-041).

The contributor follows it in `GET /api/uploads` (status, sniffed type, SHA-256, reason, the processing job whose
events stream at `/api/jobs/{id}/events`).

## 4. In production

tusd runs from its official image pinned by digest (`deploy/tusd/compose.yaml`): host networking on loopback port
8148, a read-only root, the quarantine mounted at the same path it has on the host (the paths tusd reports are then
valid for the worker), downloads and CORS disabled (it is same-origin behind nginx). nginx exposes it at `/files/`
with request buffering off, so each chunk reaches tusd as it arrives. The gate starts that compose file and checks
the image, the network, the read-only root and that its hooks reach the API with the session (R-501).

## 5. How it is verified

| Gate | Checks |
|---|---|
| `tests/uploads/test_tus.py` | an interrupted upload resumed to the original SHA-256 and processed to a ready image; an executable renamed `.jpg` deleted and named; quotas; the disk rule; visitors, other contributors' cases, unknown images, concurrent uploads; archives recognised; the production compose file |

The tests run the real tusd (the verified v2.10.1 binary, or the image on the production host) against a real API
server, and the real worker for verification and processing.

## References

- tus resumable upload protocol 1.0. [tus.io/protocols/resumable-upload](https://tus.io/protocols/resumable-upload).
- tusd v2.10.1 and its hooks. [github.com/tus/tusd](https://github.com/tus/tusd).
- File signatures used for sniffing: the formats' own specifications (JPEG JFIF, PNG, RIFF WebP, TIFF 6.0 and
  BigTIFF, DICOM PS3.10 section 7.1, ZIP APPNOTE).
