import { describe, expect, it } from "vitest";
import type { AssetRecord } from "../contract/catalog";
import { itemFor, stageItems } from "./assets";

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
