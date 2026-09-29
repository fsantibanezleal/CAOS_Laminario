// A slide's citation and each image's attribution (U15, R-1503; dossier 17 section 2). The attribution is Creative
// Commons' TASL (title, author, source, licence with its link) and says the image is adapted, since every image
// Laminario serves is re-encoded or fused; the citation follows the NHM Data Portal's form for a record. The words
// come from the page's language, so the functions stay pure.
import type { AssetRecord, SlideRecord } from "../contract/catalog";

export interface CiteWords {
  /** "Microscope slide". */
  kind: string;
  /** "Read on". */
  readOn: string;
  by: string;
  from: string;
  unknownAuthor: string;
  /** "adapted: re-encoded as a tiled pyramid", for a scan. */
  pyramid: string;
  /** "adapted: fused from a focal stack", for a composite or a height map. */
  fused: string;
  /** "adapted: re-encoded", for a photograph. */
  reencoded: string;
}

const FUSED = new Set(["edf_wavelet", "edf_variance", "height_map"]);
const TILED = new Set(["pyramid", "z_plane", "single", "polarised"]);

/** "Laminario (2026). Polyplax borealis (NHMUK010173454), whole mount [Microscope slide]. <permalink>. Read on <date>." */
export function slideCitation(record: Pick<SlideRecord, "id" | "permalink" | "published_at" | "label">,
  preparation: string, readOn: string, words: CiteWords): string {
  const year = (record.published_at ?? "").slice(0, 4) || String(new Date().getFullYear());
  const catalogue = record.label.catalogue_number || record.id;
  return `Laminario (${year}). ${record.label.name} (${catalogue}), ${preparation} [${words.kind}]. `
    + `${record.permalink}. ${words.readOn} ${readOn}.`;
}

/** The TASL line of one image: its title, author, source and licence, and how the served image is adapted. */
export function attribution(asset: Pick<AssetRecord, "role" | "family" | "caption" | "creator" | "rights_holder"
  | "licence" | "source">, record: Pick<SlideRecord, "id" | "permalink" | "label">, roleName: string,
words: CiteWords): string {
  const catalogue = record.label.catalogue_number || record.id;
  const title = asset.caption?.trim() || `${roleName}, ${record.label.name} (${catalogue})`;
  const author = asset.creator?.trim() || asset.rights_holder?.trim() || words.unknownAuthor;
  const source = asset.source?.url || record.permalink;
  const adapted = FUSED.has(asset.role) ? words.fused
    : asset.family === "micro" && TILED.has(asset.role) ? words.pyramid : words.reencoded;
  return `"${title}" ${words.by} ${author}, ${words.from} ${source}, ${asset.licence.short_name} `
    + `(${asset.licence.uri}); ${adapted}.`;
}
