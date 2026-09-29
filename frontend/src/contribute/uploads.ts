// The files of a case, sent to tusd (tus 1.0) by Uppy's core and its tus plugin, headless: Laminario draws the files,
// their progress, pause and resume; Uppy keeps the queue, retries with back-off, and resumes an interrupted file from
// the offset tusd kept (tus-js-client's fingerprint, kept on this device, finds the upload again after a reload when
// the same file is chosen). Each upload names the draft and the image it is for, as the pre-create hook requires; a
// refusal of the hook (not the owner, over the quota, a full disk) comes back as its reason.
import Uppy, { type UppyFile } from "@uppy/core";
import Tus from "@uppy/tus";

/** Where nginx (and the dev server's proxy) expose tusd. */
export const TUS_ENDPOINT = "/files/";
/** A scanner file goes in chunks of 50 MB (a photograph fits in one). */
export const CHUNK_BYTES = 50 * 1024 * 1024;
/** Waits before each retry of a failed request, in ms. */
export const RETRY_DELAYS = [0, 1000, 3000, 5000, 10000, 20000];

export interface FileProgress {
  token: string;
  state: "waiting" | "uploading" | "paused" | "sent" | "failed";
  sent: number;
  total: number;
  error: string | null;
}

type Meta = { slide: string; asset: string; filename: string; filetype: string; token: string };
type Listener = (progress: FileProgress) => void;

/** The server's reason in a tus error ("response text: {"detail": "..."}"), or the error's own message. */
export function reasonOf(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  const body = /response text: (\{.*\})/s.exec(message)?.[1];
  if (body) {
    try {
      const detail = (JSON.parse(body) as { detail?: unknown }).detail;
      if (typeof detail === "string") return detail;
    } catch {
      // not JSON: the message as it is
    }
  }
  const status = /response code: (\d{3})/.exec(message)?.[1];
  return status ? `the upload server answered ${status}` : message;
}

export class CaseUploads {
  private uppy: Uppy<Meta, Record<string, never>>;
  private byToken = new Map<string, string>();
  private progress = new Map<string, FileProgress>();

  constructor(private slide: string, private onProgress: Listener) {
    this.uppy = new Uppy<Meta, Record<string, never>>({ autoProceed: false, allowMultipleUploadBatches: true,
      restrictions: { maxNumberOfFiles: 500 } });
    this.uppy.use(Tus, { endpoint: TUS_ENDPOINT, chunkSize: CHUNK_BYTES, retryDelays: RETRY_DELAYS,
      allowedMetaFields: ["slide", "asset", "filename", "filetype"], removeFingerprintOnSuccess: true,
      limit: 2 });
    this.uppy.on("upload-progress", (file, p) => {
      if (!file) return;
      this.set(file, { state: "uploading", sent: p.bytesUploaded, total: p.bytesTotal ?? file.size ?? 0 });
    });
    this.uppy.on("upload-success", (file) => {
      if (!file) return;
      const total = file.size ?? 0;
      this.set(file, { state: "sent", sent: total, total, error: null });
    });
    this.uppy.on("upload-error", (file, error) => {
      if (!file) return;
      this.set(file, { state: "failed", error: reasonOf(error) });
    });
    this.uppy.on("upload-pause", (file, paused) => {
      if (!file) return;
      this.set(file, { state: paused ? "paused" : "uploading" });
    });
  }

  private set(file: UppyFile<Meta, Record<string, never>>, change: Partial<FileProgress>): void {
    const token = file.meta.token;
    const before = this.progress.get(token) ?? { token, state: "waiting", sent: 0, total: file.size ?? 0,
      error: null };
    const next = { ...before, ...change };
    this.progress.set(token, next);
    this.onProgress(next);
  }

  /** Queue an image's file; a file queued before for the same image is replaced. */
  add(token: string, assetId: number, file: File): void {
    const previous = this.byToken.get(token);
    if (previous) this.uppy.removeFile(previous);
    const id = this.uppy.addFile({ name: file.name, type: file.type || "application/octet-stream", data: file,
      meta: { slide: this.slide, asset: String(assetId), filename: file.name,
        filetype: file.type || "application/octet-stream", token } });
    this.byToken.set(token, id);
    const entry: FileProgress = { token, state: "waiting", sent: 0, total: file.size, error: null };
    this.progress.set(token, entry);
    this.onProgress(entry);
  }

  has(token: string): boolean {
    return this.byToken.has(token);
  }

  /** Send every queued file; resolves when each has been sent or has failed. */
  async start(): Promise<void> {
    await this.uppy.upload();
  }

  pauseResume(token: string): void {
    const id = this.byToken.get(token);
    if (id) this.uppy.pauseResume(id);
  }

  async retry(token: string): Promise<void> {
    const id = this.byToken.get(token);
    if (!id) return;
    this.set(this.uppy.getFile(id), { state: "waiting", error: null });
    await this.uppy.retryUpload(id);
  }

  remove(token: string): void {
    const id = this.byToken.get(token);
    if (id) this.uppy.removeFile(id);
    this.byToken.delete(token);
    this.progress.delete(token);
  }

  destroy(): void {
    this.uppy.destroy();
  }
}
