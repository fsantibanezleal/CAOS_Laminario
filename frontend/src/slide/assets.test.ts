import { describe, expect, it } from "vitest";
import type { AssetRecord } from "../contract/catalog";
import { bestFit, itemFor, stageItems, thumbnail } from "./assets";

let next = 1;
function asset(role: string, extra: Partial<AssetRecord> = {}): AssetRecord {
  const id = next++;
  return {
    id, family: "micro", role, sort_order: id, status: "ready",
    media: { kind: "pyramid", iiif_info_url: `/iiif/X%2F${id}.tif/info.json` },
    licence: { uri: "https://creativecommons.org/licenses/by/4.0/", short_name: "CC BY 4.0" }, ...extra,
  };
}

describe("stage items", () => {
  it("groups a focal stack by depth with its composites, pairs polarised images, and keeps singles", () => {
    next = 1;
    const planes = [2, 0, 1].map((index) => asset("z_plane", { plane: { stack: "focus", index, depth_um: index * 2 },
      pixel_size_um: 0.229 }));
    const wavelet = asset("edf_wavelet");
    const ppl = asset("polarised", { polarisation: { state: "ppl", angle_deg: 0 } });
    const xpl = asset("polarised", { polarisation: { state: "xpl", angle_deg: 0 } });
    const lone = asset("single", { pixel_size_um: 0.5 });
    const macro = asset("slide_overview", { family: "macro" });
    const pending = asset("single", { status: "pending" });
    const items = stageItems([lone, xpl, ...planes, wavelet, ppl, macro, pending]);

    expect(items.map((i) => i.kind)).toEqual(["stack", "pair", "single"]);
    const [stack, pair, single] = items;
    expect(stack.planes.map((p) => p.plane?.index)).toEqual([0, 1, 2]);
    expect(stack.first.plane?.index).toBe(0);
    expect(stack.composites).toEqual([wavelet]);
    expect(stack.pixelUm).toBe(0.229);
    expect([pair.ppl?.id, pair.xpl?.id]).toEqual([ppl.id, xpl.id]);
    expect(single.first).toBe(lone);
    // Any asset of an item opens that item.
    expect(itemFor(items, planes[0].id)).toBe(stack);
    expect(itemFor(items, wavelet.id)).toBe(stack);
    expect(itemFor(items, xpl.id)).toBe(pair);
    expect(itemFor(items, macro.id)).toBeUndefined();
  });
});

describe("best-fit sizes", () => {
  // iipsrv 1.3 answers 400 to !w,h when w or h exceeds the image's side; 95 of 505 base slides tripped it.
  it("caps the box at the image's own sides", () => {
    expect(bestFit(1024, { width_px: 1280, height_px: 720 })).toBe("!1024,720");
    expect(bestFit(1024, { width_px: 640, height_px: 480 })).toBe("!640,480");
    expect(bestFit(320, { width_px: 1280, height_px: 720 })).toBe("!320,320");
  });
  it("sends the plain box when the size is unknown", () => {
    expect(bestFit(400, { width_px: null, height_px: null })).toBe("!400,400");
  });
  it("puts the capped size in the thumbnail URL", () => {
    const a = asset("single", { media: { kind: "pyramid", iiif_info_url: "/iiif/X%2F1.tif/info.json", width_px: 1280, height_px: 720 } });
    expect(thumbnail(a, 1024)).toBe("/iiif/X%2F1.tif/full/!1024,720/0/default.jpg");
  });
});
