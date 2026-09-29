// What every section of the case editor receives: the case, the way to change it, and the messages for its fields.
import type { CaseDraft } from "../../contribute/draft";

export interface ErrorOptions {
  /** Also the messages of the fields below this path ("specimen.anchor" takes "specimen.anchor.ref"). */
  prefix?: boolean;
}

export interface SectionProps {
  draft: CaseDraft;
  update: (change: (draft: CaseDraft) => CaseDraft) => void;
  /** The worded errors of a field, joined; undefined when it has none or the section's errors are not shown yet. */
  errorFor: (path: string, options?: ErrorOptions) => string | undefined;
  /** The worded flags (accepted, but said) of a field. */
  flagFor: (path: string, options?: ErrorOptions) => string | undefined;
}

export const STEPS = ["specimen", "slide", "images", "place", "placement", "send"] as const;
export type Step = (typeof STEPS)[number];
