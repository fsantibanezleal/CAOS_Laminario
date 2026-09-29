// Chips (a facet that toggles, a filter that can be removed) and the collection tag: a collection's hue band, icon and
// name together, since the hue alone never identifies a collection.
import type { CSSProperties } from "react";
import { useI18n } from "../i18n";
import styles from "./Chip.module.css";
import { Glyph, Icon } from "./Icon";

export interface FacetChipProps {
  label: string;
  pressed: boolean;
  onChange: (pressed: boolean) => void;
  icon?: string;
  count?: number;
}

export function FacetChip({ label, pressed, onChange, icon, count }: FacetChipProps) {
  const { number } = useI18n();
  return (
    <button type="button" className={styles.chip} aria-pressed={pressed} onClick={() => onChange(!pressed)}>
      {pressed ? <Glyph name="check" size={16} /> : icon ? <Icon name={icon} size={16} /> : null}
      <span>{label}</span>
      {count !== undefined ? <span className={styles.count}>{number(count)}</span> : null}
    </button>
  );
}

export function RemovableChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  const { t } = useI18n();
  return (
    <span className={[styles.chip, styles.static].join(" ")}>
      <span>{label}</span>
      <button type="button" className={styles.remove} aria-label={t("action.remove", { name: label })} onClick={onRemove}>
        <Glyph name="close" size={16} />
      </button>
    </span>
  );
}

export interface CollectionTagProps {
  /** A collection id of the tree, such as "life.plants". */
  collection: string;
  name: string;
  size?: "small" | "large";
}

export function CollectionTag({ collection, name, size = "small" }: CollectionTagProps) {
  const hue = `var(--h-${collection.split(".")[1]})`;
  return (
    <span className={[styles.tag, styles[size]].join(" ")} style={{ "--tag-hue": hue } as CSSProperties}>
      <Icon name={collection} size={size === "large" ? 32 : 20} />
      <span>{name}</span>
    </span>
  );
}
