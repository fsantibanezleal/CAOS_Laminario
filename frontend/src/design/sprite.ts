// The names of the tree's nodes, read from the icon sprite's EN and ES titles (the sprite is built from the tree, so
// the names are the tree's own). Places that have the API read names from it; this serves the specimen place and any
// icon that needs a name before the API has answered.
import { useEffect, useState } from "react";
import type { Lang } from "../i18n";

export type SpriteNames = Record<string, Record<Lang, string>>;

let cache: Promise<SpriteNames> | null = null;

function load(): Promise<SpriteNames> {
  cache ??= fetch("/icons.svg")
    .then((r) => (r.ok ? r.text() : ""))
    .then((text) => {
      const doc = new DOMParser().parseFromString(text, "image/svg+xml");
      const names: SpriteNames = {};
      for (const symbol of Array.from(doc.querySelectorAll("symbol"))) {
        const titles = Array.from(symbol.querySelectorAll("title"));
        const en = titles.find((t) => t.getAttribute("lang") === "en")?.textContent ?? symbol.id;
        const es = titles.find((t) => t.getAttribute("lang") === "es")?.textContent ?? en;
        names[symbol.id] = { en, es };
      }
      return names;
    })
    .catch(() => ({}));
  return cache;
}

export function useSpriteNames(): SpriteNames {
  const [names, setNames] = useState<SpriteNames>({});
  useEffect(() => {
    let live = true;
    void load().then((n) => { if (live) setNames(n); });
    return () => { live = false; };
  }, []);
  return names;
}
