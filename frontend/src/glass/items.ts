// Glass slides from what the page already has: a node of the collection tree (a realm, a collection, a drawer, a group)
// or a slide's summary. Colours are the room's, resolved when the items are made (the scene paints with them).
import type { CollectionNodeRecord, SlideRecord, SlideSummary } from "../contract/catalog";
import type { useI18n } from "../i18n";
import { bestFit } from "../slide/assets";
import { geometry, isItalicName } from "../slide/names";
import { collectionOf, localised, nodeHref, type TreeIndex } from "../tree/TreeProvider";
import { roomColour } from "./GlassSet";
import { STANDARD, qrOf, type GlassItem } from "./model";

type I18n = ReturnType<typeof useI18n>;

/** The hue token of a node: its collection's, or the accent for a realm. */
export function hueToken(id: string): string {
  const collection = collectionOf(id);
  return collection ? `--h-${collection.split(".")[1]}` : "--c-accent";
}

/** A node of the tree as a glass slide: its icon under the coverslip, its name on the left end, its counts on the
 * right. */
export function nodeItem(node: CollectionNodeRecord, i18n: I18n): GlassItem {
  const { plural, lang, t } = i18n;
  const count = node.slide_count ?? 0;
  const drawers = (node.children ?? []).length;
  const facts = [plural("count.slides", count)];
  if (drawers) facts.push(plural("count.drawers", drawers));
  if (!count) facts.push(t("cabinet.empty"));
  return {
    id: node.id,
    href: nodeHref(node.id),
    name: localised(node.name, lang),
    facts,
    icon: node.icon || node.id,
    hue: roomColour(hueToken(node.id)),
    format: STANDARD,
    empty: count === 0,
  };
}

/** A slide's summary as a glass slide: its photograph as the whole glass when one exists, else the specimen's image
 * under the coverslip; the name and catalogue number on the left end; the preparation, place and date on the right. */
export function slideItem(slide: SlideSummary, tree: TreeIndex, i18n: I18n): GlassItem {
  const { lang, date } = i18n;
  const collection = collectionOf(slide.placement.node) ?? "life.plants";
  const preparation = tree.facets.get("preparation")?.values.find((v) => v.id === slide.preparation);
  const names = slide.label?.country ? tree.countries[slide.label.country] : undefined;
  const locality = slide.label?.locality_text ?? "";
  const named = names && [names.en, names.es].some((n) => locality.toLowerCase().trimEnd().endsWith(n.toLowerCase()));
  const place = [locality, named ? "" : names?.[lang] ?? ""].filter(Boolean).join(", ");
  const collected = slide.label?.collected_on;
  const facts = [preparation ? localised(preparation.name, lang) : slide.preparation, place,
    collected ? date(collected, { year: "numeric", month: "short", day: "numeric" }) : ""].filter(Boolean);
  const node = tree.byId.get(slide.placement.node);
  return {
    id: slide.id,
    href: `/s/${slide.id}`,
    name: slide.anchor.name,
    italic: isItalicName(slide.anchor),
    reference: slide.label?.catalogue_number || slide.id,
    facts,
    icon: node?.icon ?? collection,
    image: slide.thumbnail_url ?? null,
    photo: slide.glass_photo_url ?? null,
    hue: roomColour(hueToken(collection)),
    format: geometry(slide.format),
  };
}

/** A slide's full record as its glass slide, for its own place: its photograph when the glass was photographed, else
 * its first micro image under the coverslip; the label's name and catalogue number on the left end; its preparation,
 * place and date on the right, with the QR the server draws for it. */
export function recordItem(record: SlideRecord, tree: TreeIndex, i18n: I18n, drawing?: string | null): GlassItem {
  const { lang, date } = i18n;
  const collection = collectionOf(record.placement.node) ?? "life.plants";
  const preparation = tree.facets.get("preparation")?.values.find((v) => v.id === record.label.preparation);
  const ready = record.assets.filter((a) => a.status === "ready");
  const overview = ready.find((a) => a.role === "slide_overview");
  const micro = ready.find((a) => a.family === "micro");
  const picture = (a?: (typeof ready)[number]) => {
    if (!a) return null;
    const info = a.media.iiif_info_url;
    return info ? `${info.replace(/\/info\.json$/, "")}/full/${bestFit(1024, a.media)}/0/default.jpg` : a.media.image_url ?? null;
  };
  const collected = record.label.collected_on;
  const facts = [preparation ? localised(preparation.name, lang) : record.label.preparation, record.label.locality_text ?? "",
    collected ? date(collected, { year: "numeric", month: "short", day: "numeric" }) : ""].filter(Boolean);
  const node = tree.byId.get(record.placement.node);
  return {
    id: record.id,
    href: `/s/${record.id}`,
    name: record.label.name,
    italic: isItalicName(record.anchor),
    reference: record.label.catalogue_number || record.id,
    facts,
    icon: node?.icon ?? collection,
    image: picture(micro),
    photo: picture(overview),
    hue: roomColour(hueToken(collection)),
    format: geometry(record.format),
    qr: drawing ? qrOf(drawing) ?? undefined : undefined,
  };
}
