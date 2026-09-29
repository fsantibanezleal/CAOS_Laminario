// The files of a stored case, from the device to a published slide: queued in Uppy once the case has its image ids,
// a private case's photographs rewritten without their position first (R-1204), sent over tus with their progress,
// then followed on the server: the verification job (checksum, the file's kind, its header) and, once accepted, the
// processing job (the pyramid), by their Server-Sent Events. The case itself is read again while anything is in
// flight, so a refusal, an acceptance, a failure and the publication all show without a reload.
import { useCallback, useEffect, useRef, useState } from "react";
import { followJob } from "../../contribute/api";
import { pending } from "../../contribute/pending";
import { looksLikeScannerFile, withoutLocation } from "../../contribute/photo";
import { CaseUploads, type FileProgress } from "../../contribute/uploads";
import type { CaseRecord, JobEventRecord } from "../../contract/catalog";

export interface JobStep {
  job: string;
  kind: "verify" | "process";
  event: JobEventRecord["event"];
  step: string | null;
  detail: Record<string, unknown>;
}

const IN_FLIGHT = new Set(["uploading", "received"]);

export function inFlight(record: CaseRecord | null, sending: boolean): boolean {
  if (!record) return false;
  if (sending || record.status === "processing") return true;
  return (record.images ?? []).some((i) => IN_FLIGHT.has(i.upload_status ?? ""));
}

export function useCaseFiles(record: CaseRecord | null, geoprivacy: string, refresh: () => Promise<void>) {
  const [progress, setProgress] = useState<Record<string, FileProgress>>({});
  const [steps, setSteps] = useState<Record<string, JobStep>>({});
  const [sending, setSending] = useState(false);
  const [stripped, setStripped] = useState<Record<string, number>>({});
  const uploads = useRef<CaseUploads | null>(null);
  const followed = useRef(new Map<string, () => void>());
  const caseId = record?.id ?? null;

  // One queue per stored case, gone with the place.
  useEffect(() => {
    if (!caseId) return undefined;
    const queue = new CaseUploads(caseId, (p) => setProgress((all) => ({ ...all, [p.token]: p })));
    uploads.current = queue;
    return () => {
      queue.destroy();
      uploads.current = null;
    };
  }, [caseId]);

  // Stop following every job when the place goes.
  useEffect(() => {
    const map = followed.current;
    return () => {
      for (const stop of map.values()) stop();
      map.clear();
    };
  }, []);

  /** The images that have a chosen file and still need it on the server. */
  const waiting = (record?.images ?? []).filter((i) => i.token && pending.has(i.token) && !i.has_file
    && !IN_FLIGHT.has(i.upload_status ?? "") && progress[i.token]?.state !== "sent");

  const send = useCallback(async () => {
    const queue = uploads.current;
    if (!queue || !record) return;
    setSending(true);
    try {
      for (const image of record.images ?? []) {
        const token = image.token;
        if (!token || image.has_file || IN_FLIGHT.has(image.upload_status ?? "")) continue;
        let file = pending.get(token);
        if (!file) continue;
        if (geoprivacy === "private" && !looksLikeScannerFile(file.name, file.size)) {
          const clean = await withoutLocation(file);
          if (clean.gps || clean.xmp) {
            file = clean.file;
            pending.set(token, file);
            setStripped((s) => ({ ...s, [token]: clean.gps }));
          }
        }
        if (progress[token]?.state !== "sent") queue.add(token, image.asset_id, file);
      }
      await queue.start();
    } finally {
      setSending(false);
      await refresh();
    }
  }, [record, geoprivacy, progress, refresh]);

  // Follow the jobs the case names: an upload's verification, and the processing it starts.
  useEffect(() => {
    for (const image of record?.images ?? []) {
      const job = image.upload_job;
      const token = image.token ?? String(image.asset_id);
      if (!job || followed.current.has(job)) continue;
      const stop = followJob(job, (event) => {
        const data = (event.data ?? {}) as Record<string, unknown>;
        setSteps((all) => ({ ...all, [token]: { job, kind: "verify", event: event.event,
          step: typeof data.step === "string" ? data.step : null, detail: data } }));
        const processing = typeof data.processing === "string" ? data.processing : null;
        if (processing && !followed.current.has(processing)) {
          followed.current.set(processing, followJob(processing, (next) => {
            const d = (next.data ?? {}) as Record<string, unknown>;
            setSteps((all) => ({ ...all, [token]: { job: processing, kind: "process", event: next.event,
              step: typeof d.step === "string" ? d.step : null, detail: d } }));
          }));
        }
        if (event.event === "succeeded" || event.event === "failed") void refresh();
      });
      followed.current.set(job, stop);
    }
  }, [record, refresh]);

  // Read the case again while anything is in flight (every 2 s, and never after the place is left).
  const flying = inFlight(record, sending);
  useEffect(() => {
    if (!flying) return undefined;
    const timer = window.setInterval(() => void refresh(), 2000);
    return () => window.clearInterval(timer);
  }, [flying, refresh]);

  return {
    progress, steps, sending, stripped, waiting,
    send,
    pauseResume: (token: string) => uploads.current?.pauseResume(token),
    retry: async (token: string) => {
      await uploads.current?.retry(token);
      await refresh();
    },
  };
}

/** Whether every image of a case has its file on the server (the condition to submit, R-1205). */
export function allFiles(record: CaseRecord | null): boolean {
  return Boolean(record && (record.images ?? []).length && (record.images ?? []).every((i) => i.has_file));
}

