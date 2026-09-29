// What the stage opens: a slide's ready micro assets grouped as the microscope sees them. A focal stack's planes
// (ordered by index, named by depth) with its composites (the all-in-focus images and the height map); a polarised
// pair (plane-polarised and crossed polars of one field); or a single image. Each item is addressed by its first
// asset, so /s/<slide>/stage/<asset> opens the item holding that asset.
import type { AssetRecord } from "../contract/catalog";

export const COMPOSITES = ["edf_wavelet", "edf_variance", "height_map"] as const;

export interface StageItem {
  key: number;
  kind: "single" | "stack" | "pair";
  /** The asset the item opens on, and the one its address names. */
  first: AssetRecord;
  planes: AssetRecord[];
  composites: AssetRecord[];
  ppl?: AssetRecord;
  xpl?: AssetRecord;
  pixelUm: number | null;
}

const ready = (a: AssetRecord) => a.family === "micro" && a.status === "ready";

export function stageItems(assets: AssetRecord[]): StageItem[] {
  const micro = assets.filter(ready).sort((a, b) => a.sort_order - b.sort_order || a.id - b.id);
  const items: StageItem[] = [];
  const stacks = new Map<string, StageItem>();
  const composites = micro.filter((a) => (COMPOSITES as readonly string[]).includes(a.role));
  let pendingPpl: AssetRecord | null = null;
  for (const asset of micro) {
    if (asset.role === "z_plane" && asset.plane) {
      let stack = stacks.get(asset.plane.stack);
      if (!stack) {
        stack = { key: asset.id, kind: "stack", first: asset, planes: [], composites: [], pixelUm: asset.pixel_size_um ?? null };
        stacks.set(asset.plane.stack, stack);
        items.push(stack);
      }
      stack.planes.push(asset);
    } else if (asset.role === "polarised" && asset.polarisation) {
      if (asset.polarisation.state === "ppl") {
        pendingPpl = asset;
      } else if (pendingPpl) {
        items.push({ key: pendingPpl.id, kind: "pair", first: pendingPpl, planes: [], composites: [], ppl: pendingPpl,
          xpl: asset, pixelUm: pendingPpl.pixel_size_um ?? asset.pixel_size_um ?? null });
        pendingPpl = null;
      } else {
        items.push(single(asset));
      }
    } else if (!(COMPOSITES as readonly string[]).includes(asset.role)) {
      items.push(single(asset));
    }
  }
  if (pendingPpl) items.push(single(pendingPpl));
  for (const stack of stacks.values()) {
    stack.planes.sort((a, b) => (a.plane?.index ?? 0) - (b.plane?.index ?? 0));
    stack.first = stack.planes[0];
    stack.key = stack.first.id;
  }
  // The composites of a slide's one stack belong to it; with several stacks (or none) they stand alone.
  if (stacks.size === 1) {
    [...stacks.values()][0].composites = composites;
  } else {
    for (const c of composites) items.push(single(c));
  }
  return items;
}

function single(asset: AssetRecord): StageItem {
  return { key: asset.id, kind: "single", first: asset, planes: [], composites: [], pixelUm: asset.pixel_size_um ?? null };
}

/** The item holding an asset, for /s/<slide>/stage/<asset>. */
export function itemFor(items: StageItem[], assetId: number): StageItem | undefined {
  return items.find((i) => i.first.id === assetId || i.planes.some((p) => p.id === assetId) ||
    i.composites.some((c) => c.id === assetId) || i.xpl?.id === assetId);
}

/** A thumbnail of an asset, from its IIIF image or its plain image. */
export function thumbnail(asset: AssetRecord, box = 400): string | null {
  const media = asset.media;
  if (media.iiif_info_url) return `${media.iiif_info_url.replace(/\/info\.json$/, "")}/full/!${box},${box}/0/default.jpg`;
  return media.image_url ?? null;
}
