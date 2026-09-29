# tusd

## What and why

tusd is the reference server of tus 1.0, the open protocol for resumable uploads: `POST` creates an upload with its
length, `PATCH` appends at `Upload-Offset`, `HEAD` returns how much arrived, so a client resumes after a dropped
connection instead of starting over. Scanner files of several gigabytes make that a requirement, not a comfort
(dossier 08). Hooks let the application decide who may upload what, and learn when a file is complete.

## Install (exact, verified)

- Production: the official image, `tusproject/tusd@sha256:7b1c552a8b42f4b36cb01f2a3bd49f82ab078b2eefd191459e716141dd50376c`
  (v2.10.1, 36 MB, user `tusd`, uid 1000), through `deploy/tusd/compose.yaml`.
- Tests: the release binaries of v2.10.1, checked against their published SHA-256 (`tusd_windows_amd64.zip`,
  `tusd_linux_amd64.tar.gz`), named by `LAMINARIO_TUSD_BIN`.

## Usage

```bash
tusd -host=127.0.0.1 -port=8148 -base-path=/files/ -upload-dir=/srv/laminario/quarantine \
     -hooks-http=http://127.0.0.1:8147/api/_internal/tus-hook -hooks-http-forward-headers=Cookie \
     -hooks-enabled-events=pre-create,post-finish,post-terminate -disable-download -disable-cors -behind-proxy
```

## Applying it here

The API answers the hooks (`app/routers/uploads.py`): pre-create applies the upload policy and chooses the upload's
id; post-finish queues the verification job; post-terminate marks the upload cancelled. nginx exposes it at
`/files/`, unbuffered.

## Caveats and licence

- A non-2xx hook answer reaches the client as a 500; refusals must be `RejectUpload` with an `HTTPResponse`.
- post-finish is delivered after the client's final response; anything that stops tusd right after an upload
  (a test) must wait for it.
- Hooks time out after 15 s by default, with three retries; heavy work belongs in the worker.
- It reports its own file paths; mounted at the same path in and out of the container, they are valid on the host.
- MIT.
