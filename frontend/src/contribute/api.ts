// The contribution API: validate a case as it is filled in, store it as a draft, change it, list and reopen the
// contributor's cases, submit, delete; the anchor names and the placement the tree suggests; the job events of an
// image's verification and processing.
import { ApiError, send } from "../api/client";
import type { AnchorSuggestion, CaseRecord, CaseSummary, CreatedSlideCase, JobEventRecord, PlacementResult,
  ValidationResult } from "../contract/catalog";
import type { Anchor, SlideCaseSubmission } from "../contract/ingest";

const CASES = "/api/slide-cases";
const casePath = (id: string) => `${CASES}/${encodeURIComponent(id)}`;

/** A 422 answer carries the validation result: read it as the answer rather than as a failure. */
async function judged<T>(call: Promise<T | null>): Promise<T | ValidationResult> {
  try {
    return (await call) as T;
  } catch (error) {
    if (error instanceof ApiError && error.status === 422 && error.body && typeof error.body === "object"
      && "valid" in error.body) {
      return error.body as ValidationResult;
    }
    throw error;
  }
}

export function isValidation(value: unknown): value is ValidationResult {
  return Boolean(value && typeof value === "object" && "valid" in value && !("id" in value));
}

export const contributeApi = {
  validate: (sub: SlideCaseSubmission, signal?: AbortSignal) =>
    judged(send<ValidationResult>("POST", `${CASES}/validate`, sub, signal)) as Promise<ValidationResult>,
  create: (sub: SlideCaseSubmission) => judged(send<CreatedSlideCase>("POST", CASES, sub)),
  change: (id: string, sub: SlideCaseSubmission) => judged(send<CaseRecord>("PUT", casePath(id), sub)),
  list: (signal?: AbortSignal) => send<CaseSummary[]>("GET", CASES, undefined, signal) as Promise<CaseSummary[]>,
  get: (id: string, signal?: AbortSignal) => send<CaseRecord>("GET", casePath(id), undefined, signal) as
    Promise<CaseRecord>,
  submit: (id: string) => send<CaseRecord>("POST", `${casePath(id)}/submit`) as Promise<CaseRecord>,
  remove: (id: string) => send<null>("DELETE", casePath(id)),
  anchors: (kind: Anchor["kind"], q: string, signal?: AbortSignal) =>
    send<AnchorSuggestion[]>("GET", `/api/anchors/search?${new URLSearchParams({ kind, q, limit: "12" })}`,
      undefined, signal) as Promise<AnchorSuggestion[]>,
  placement: (anchor: Anchor, part: string | null, preservation: string, signal?: AbortSignal) =>
    send<PlacementResult>("POST", "/api/placement", { anchor, part, preservation }, signal) as
      Promise<PlacementResult>,
};

const TERMINAL = new Set(["succeeded", "failed", "cancelled"]);
const EVENTS = ["queued", "started", "progress", "log", "requeued", "succeeded", "failed", "cancelled"] as const;

/**
 * Follow a job's Server-Sent Events (GET /api/jobs/{id}/events) until its terminal event. The browser reconnects by
 * itself (the stream asks for 2 s) and the server replays from the last event seen. Returns the way to stop.
 */
export function followJob(jobId: string, onEvent: (event: JobEventRecord) => void): () => void {
  const source = new EventSource(`/api/jobs/${encodeURIComponent(jobId)}/events`);
  const handle = (message: MessageEvent<string>) => {
    try {
      const event = JSON.parse(message.data) as JobEventRecord;
      onEvent(event);
      if (TERMINAL.has(event.event)) source.close();
    } catch {
      // a line that is not an event: ignored
    }
  };
  for (const name of EVENTS) source.addEventListener(name, handle as EventListener);
  return () => source.close();
}
