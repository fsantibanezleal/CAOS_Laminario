// The About place's content as typed blocks (U15): the same sections, equations, figures and links in both languages,
// which content.test.ts holds. Counts are never written here: "live" blocks draw them from GET /api/about.

/** A run of text: plain, emphasised, strong, a link, inline math (KaTeX) or code. */
export type Inline = string | { em: string } | { strong: string } | { a: string; href: string } | { m: string }
  | { code: string };

export type FigureId = "pyramid" | "objectives" | "stack" | "polarised" | "geoprivacy";
export type LiveId = "numbers" | "sources" | "licences" | "vocabularies" | "software" | "fonts" | "map";
export type SectionId = "what" | "numbers" | "sources" | "licences" | "cite" | "imaging" | "community" | "privacy"
  | "names" | "software" | "references";
export type SourceId = "commons" | "nhm" | "smithsonian" | "zenodo" | "openslide" | "contribution" | "other";
export type LicenceFamily = "cc0" | "pdm" | "nkc" | "by" | "by-sa" | "by-nc" | "by-nc-sa";

export type Block =
  | { kind: "p"; text: Inline[] }
  | { kind: "h3"; text: string }
  | { kind: "list"; items: Inline[][] }
  | { kind: "math"; tex: string }
  | { kind: "code"; text: string }
  | { kind: "figure"; figure: FigureId; caption: Inline[] }
  | { kind: "live"; what: LiveId };

export interface Section {
  id: SectionId;
  title: string;
  blocks: Block[];
}

export interface AboutContent {
  title: string;
  lead: string;
  contents: string;
  sections: Section[];
  /** Words for each source of the About answer (the ids of app/about/credits.json, contributions, other). */
  sources: Record<SourceId, Inline[]>;
  /** Each licence family the policy accepts: its name and what it allows. */
  licences: Record<LicenceFamily, { name: string; text: Inline[] }>;
  /** The labels drawn inside each figure. */
  figures: Record<FigureId, Record<string, string>>;
  /** The words of the live tables. */
  live: Record<string, string>;
}

export const SECTION_ORDER: SectionId[] = ["what", "numbers", "sources", "licences", "cite", "imaging", "community",
  "privacy", "names", "software", "references"];
