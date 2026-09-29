// Tabs after the WAI-ARIA Authoring Practices pattern: one tab stop, arrow keys move between tabs (Home and End to the
// ends) and select them, each panel is labelled by its tab.
import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import styles from "./Tabs.module.css";

export interface TabItem<K extends string> {
  key: K;
  label: string;
  panel: ReactNode;
}

export interface TabsProps<K extends string> {
  label: string;
  items: TabItem<K>[];
  selected: K;
  onSelect: (key: K) => void;
}

export function Tabs<K extends string>({ label, items, selected, onSelect }: TabsProps<K>) {
  const base = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const index = Math.max(0, items.findIndex((i) => i.key === selected));

  const move = (e: KeyboardEvent<HTMLDivElement>) => {
    const last = items.length - 1;
    const next = { ArrowRight: index === last ? 0 : index + 1, ArrowLeft: index === 0 ? last : index - 1, Home: 0,
      End: last }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    onSelect(items[next].key);
    refs.current[next]?.focus();
  };

  return (
    <div className={styles.tabs}>
      <div role="tablist" aria-label={label} className={styles.list} onKeyDown={move}>
        {items.map((item, i) => (
          <button key={item.key} ref={(el) => { refs.current[i] = el; }} type="button" role="tab"
            id={`${base}-tab-${item.key}`} aria-controls={`${base}-panel-${item.key}`}
            aria-selected={item.key === selected} tabIndex={item.key === selected ? 0 : -1} className={styles.tab}
            onClick={() => onSelect(item.key)}>
            {item.label}
          </button>
        ))}
      </div>
      {items.map((item) => (
        <div key={item.key} role="tabpanel" id={`${base}-panel-${item.key}`} aria-labelledby={`${base}-tab-${item.key}`}
          hidden={item.key !== selected} tabIndex={0} className={styles.panel}>
          {item.panel}
        </div>
      ))}
    </div>
  );
}
