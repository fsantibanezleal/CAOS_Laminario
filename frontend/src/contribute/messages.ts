// A validation error or flag in the page's language (R-1202): its code names the message ("validation.<code>"), its
// parameters fill it; a code the interface has no words for falls back to the server's own English message.
import type { ValidationError, ValidationFlag } from "../contract/catalog";
import { en, type MessageKey } from "../i18n/en";

export type Said = Pick<ValidationError, "message" | "code" | "params"> | Pick<ValidationFlag, "message" | "code" |
  "params">;

export function messageKey(code: string | null | undefined): MessageKey | null {
  if (!code) return null;
  const key = `validation.${code}`;
  return key in en ? (key as MessageKey) : null;
}

export function worded(t: (key: MessageKey, vars?: Record<string, string | number>) => string, item: Said): string {
  const key = messageKey(item.code);
  return key ? t(key, item.params ?? undefined) : item.message;
}

/** Whether the catalogue has words for a key built at run time. */
export function known(key: string): key is MessageKey {
  return key in en;
}

/** A rank in words ("species", "grupo"), or as the server wrote it when the catalogue does not name it. */
export function rankName(t: (key: MessageKey) => string, rank: string): string {
  const key = `rank.${rank.toLowerCase()}`;
  return known(key) ? t(key) : rank.toLowerCase();
}
