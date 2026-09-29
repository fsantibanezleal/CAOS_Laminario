// The community API (U13): a slide's identifications and how they agree, adding, withdrawing and restoring one, the
// vote on whether the community anchor can still be improved, the Identify queue, flags, and the curators' hiding
// and restoring.
import { send } from "../api/client";
import type { FlagRecord, IdentificationList, IdentificationRecord, ModerationActionRecord,
  SlidePage } from "../contract/catalog";
import type { Anchor } from "../contract/ingest";

const slidePath = (id: string) => `/api/slides/${encodeURIComponent(id)}`;

export type TargetKind = "slide" | "identification" | "annotation";
export type FlagCategory = FlagRecord["category"];
export const FLAG_CATEGORIES: FlagCategory[] = ["wrong", "copyright", "inappropriate", "spam", "other"];

export interface QueueFilters {
  node?: string;
  kind?: Anchor["kind"] | "";
  badge?: "needs_id" | "reference" | "any";
  unidentifiedByMe?: boolean;
  offset?: number;
  limit?: number;
}

export function queueQuery(f: QueueFilters): URLSearchParams {
  const q = new URLSearchParams();
  if (f.node) q.set("node", f.node);
  if (f.kind) q.set("kind", f.kind);
  if (f.badge && f.badge !== "needs_id") q.set("badge", f.badge);
  if (f.unidentifiedByMe) q.set("unidentified_by_me", "true");
  if (f.offset) q.set("offset", String(f.offset));
  q.set("limit", String(f.limit ?? 24));
  return q;
}

export const communityApi = {
  identifications: (slide: string, signal?: AbortSignal) =>
    send<IdentificationList>("GET", `${slidePath(slide)}/identifications`, undefined, signal) as
      Promise<IdentificationList>,
  identify: (slide: string, anchor: Anchor, body: string | null, disagreement: boolean | null) =>
    send<IdentificationRecord>("POST", `${slidePath(slide)}/identifications`, { anchor, body, disagreement }),
  withdraw: (id: string) => send<null>("POST", `/api/identifications/${encodeURIComponent(id)}/withdraw`),
  restore: (id: string) => send<null>("POST", `/api/identifications/${encodeURIComponent(id)}/restore`),
  vote: (slide: string, asGoodAsItCanBe: boolean | null) =>
    send<null>("PUT", `${slidePath(slide)}/vote`, { as_good_as_it_can_be: asGoodAsItCanBe }),
  queue: (filters: QueueFilters, signal?: AbortSignal) =>
    send<SlidePage>("GET", `/api/identify?${queueQuery(filters)}`, undefined, signal) as Promise<SlidePage>,
  flag: (kind: TargetKind, id: string, category: FlagCategory, comment: string | null) =>
    send<FlagRecord>("POST", "/api/flags", { target_kind: kind, target_id: id, category, comment }),
  flags: (status: "open" | "resolved" | "all", signal?: AbortSignal) =>
    send<FlagRecord[]>("GET", `/api/flags?status=${status}`, undefined, signal) as Promise<FlagRecord[]>,
  resolve: (id: string, resolution: string) =>
    send<FlagRecord>("POST", `/api/flags/${encodeURIComponent(id)}/resolve`, { resolution }),
  hide: (kind: TargetKind, id: string, reason: string) =>
    send<null>("POST", `/api/moderation/${kind}/${encodeURIComponent(id)}/hide`, { reason }),
  unhide: (kind: TargetKind, id: string, reason: string) =>
    send<null>("POST", `/api/moderation/${kind}/${encodeURIComponent(id)}/unhide`, { reason }),
  hidden: (signal?: AbortSignal) =>
    send<ModerationActionRecord[]>("GET", "/api/moderation/hidden", undefined, signal) as
      Promise<ModerationActionRecord[]>,
  actions: (slide?: string, signal?: AbortSignal) =>
    send<ModerationActionRecord[]>("GET", `/api/moderation/actions${slide ? `?slide=${encodeURIComponent(slide)}` : ""}`,
      undefined, signal) as Promise<ModerationActionRecord[]>,
};

/** The minimum a curator's reason needs (app/contracts/community.py, ReasonIn). */
export const MIN_REASON = 10;
