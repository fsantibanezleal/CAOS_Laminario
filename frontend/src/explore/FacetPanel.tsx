// The facets of a place: each a group of chips with the number of slides the value would give under the other
// filters. The values come from the place without any facet filter (so a value that the other filters rule out
// stays in its place, disabled, and the list does not jump); a chosen value is always shown.
import { useState } from "react";
import type { FacetCounts } from "../contract/catalog";
import { useI18n, type I18n } from "../i18n";
import type { MessageKey } from "../i18n/en";
import { localised, type TreeIndex } from "../tree/TreeProvider";
import { FacetChip } from "../ui/Chip";
import { FACETS, type Facet, type Filters } from "./filters";
import styles from "./FacetPanel.module.css";

const LONG_LIST = 8;

export interface FacetValue {
  id: string;
  label: string;
  icon?: string;
}

/** The name of a facet value in the page's language. */
export function valueLabel(facet: Facet, id: string, tree: TreeIndex, i18n: I18n): FacetValue {
  const { t, lang } = i18n;
  if (facet === "preparation" || facet === "modality") {
    const value = tree.facets.get(facet)?.values.find((v) => v.id === id);
    return { id, label: value ? localised(value.name, lang) : id, icon: value?.icon };
  }
  if (facet === "country") return { id, label: tree.countries[id]?.[lang] ?? id };
  const key = `${facet === "wsi" ? "wsi" : facet}.${id}` as MessageKey;
  return { id, label: t(key) };
}

export interface FacetPanelProps {
  filters: Filters;
  counts: FacetCounts | undefined;
  universe: FacetCounts | undefined;
  tree: TreeIndex;
  onToggle: (facet: Facet, value: string, on: boolean) => void;
  /** Facets the place does not offer (a view filters by kind only). */
  only?: readonly Facet[];
}

export function FacetPanel({ filters, counts, universe, tree, onToggle, only }: FacetPanelProps) {
  const i18n = useI18n();
  const { t } = i18n;
  const [open, setOpen] = useState<Set<Facet>>(new Set());
  const facets = FACETS.filter((f) => !only || only.includes(f));

  return (
    <div className={styles.panel}>
      {facets.map((facet) => {
        const known = { ...(universe?.[facet] ?? {}), ...(counts?.[facet] ?? {}) };
        for (const chosen of filters.values[facet]) if (!(chosen in known)) known[chosen] = 0;
        let ids = Object.keys(known);
        if (ids.length === 0) return null;
        const count = (id: string) => counts?.[facet]?.[id] ?? 0;
        ids = ids.sort((a, b) => count(b) - count(a) || valueLabel(facet, a, tree, i18n).label.localeCompare(
          valueLabel(facet, b, tree, i18n).label, i18n.lang));
        const long = ids.length > LONG_LIST + 2 && !open.has(facet);
        const visible = long
          ? [...ids.slice(0, LONG_LIST), ...ids.slice(LONG_LIST).filter((id) => filters.values[facet].includes(id))]
          : ids;
        return (
          <fieldset key={facet} className={styles.group}>
            <legend className={styles.legend}>{t(`facet.${facet}` as MessageKey)}</legend>
            <div className={styles.values}>
              {visible.map((id) => {
                const value = valueLabel(facet, id, tree, i18n);
                const pressed = filters.values[facet].includes(id);
                const n = count(id);
                return (
                  <FacetChip key={id} label={value.label} icon={value.icon} count={counts ? n : undefined}
                    pressed={pressed} disabled={Boolean(counts) && n === 0 && !pressed} value={`${facet}:${id}`}
                    onChange={(on) => onToggle(facet, id, on)} />
                );
              })}
            </div>
            {ids.length > LONG_LIST + 2 ? (
              <button type="button" className={styles.more} aria-expanded={!long}
                onClick={() => setOpen((s) => {
                  const next = new Set(s);
                  if (next.has(facet)) next.delete(facet); else next.add(facet);
                  return next;
                })}>
                {long ? t("explore.values.all", { count: ids.length }) : t("explore.values.fewer")}
              </button>
            ) : null}
          </fieldset>
        );
      })}
    </div>
  );
}
