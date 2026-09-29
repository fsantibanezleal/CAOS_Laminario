// How a slide's name is set. Taxon names at the rank of genus and below are italic (the codes of nomenclature's
// convention); the authorship that follows them ("Clay, 1967"), and a rank marker inside them ("var.", "subsp."), are
// roman. Everything else (a family, a rock, a mineral, a material) is roman.
import type { AnchorRecord } from "../contract/catalog";

const ITALIC_WORDS: Record<string, number> = { genus: 1, subgenus: 1, section: 1, species: 2, subspecies: 3,
  variety: 3, form: 3 };
const MARKERS = new Set(["subsp.", "ssp.", "var.", "f.", "forma", "subvar."]);

export function isItalicName(anchor: Pick<AnchorRecord, "kind" | "rank">): boolean {
  return anchor.kind === "taxon" && (anchor.rank ?? "").toLowerCase() in ITALIC_WORDS;
}

export interface NamePart {
  text: string;
  italic: boolean;
}

/** The name in parts: the italic epithets (with any rank marker roman between them) and the roman authorship. */
export function nameParts(anchor: Pick<AnchorRecord, "kind" | "rank" | "name">): NamePart[] {
  const words = anchor.name.trim().split(/\s+/);
  const wanted = anchor.kind === "taxon" ? ITALIC_WORDS[(anchor.rank ?? "").toLowerCase()] ?? 0 : 0;
  if (!wanted) return [{ text: anchor.name, italic: false }];
  const parts: NamePart[] = [];
  let epithets = 0;
  let i = 0;
  for (; i < words.length && epithets < wanted; i += 1) {
    const w = words[i];
    const marker = MARKERS.has(w.toLowerCase());
    // An epithet is lower case after the genus; a capital or a parenthesis starts the authorship.
    if (!marker && epithets > 0 && !/^[a-z×-]/.test(w)) break;
    parts.push({ text: w, italic: !marker });
    if (!marker) epithets += 1;
  }
  const rest = words.slice(i).join(" ");
  if (rest) parts.push({ text: rest, italic: false });
  return parts;
}

/** The longest standard format (2 x 3 in, 76.2 mm): a tray is scaled so its longest slide fills a column. */
export const REFERENCE_MM = 76.2;

/** The scale reference of a tray: its longest slide, never less than the longest standard format. */
export function trayReference(formats: { width_mm: number; height_mm: number }[]): number {
  return Math.max(REFERENCE_MM, ...formats.map((f) => Math.max(f.width_mm, f.height_mm)));
}

/** A catalogue number with break opportunities where a label would break it: between letters and digits and after
 * punctuation, never inside a run of digits. */
export function breakPoints(text: string): string[] {
  return text.split(/(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])|(?<=[-./:_ ])/).filter(Boolean);
}

/** The long and short side of a format in millimetres, and its label end: a slide lies long side across the tray. */
export function geometry(format: { width_mm: number; height_mm: number }) {
  const long = Math.max(format.width_mm, format.height_mm);
  const short = Math.min(format.width_mm, format.height_mm);
  // ISO 8037-1 slides have a 20 mm marking end; a shorter slide (a 27 x 46 mm thin section) keeps the same share.
  const label = Math.min(20, Math.round(long * 0.3 * 10) / 10);
  return { long, short, label };
}
