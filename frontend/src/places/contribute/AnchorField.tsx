// The anchor field: what the slide shows, chosen from the names the server offers (GET /api/anchors/search): taxa of
// the GBIF backbone, or entries of the rock, mineral, crystal and material vocabularies. An ARIA 1.2 combobox: the
// list opens as the contributor types (two letters at least), arrows move through it, Enter chooses, Escape closes.
// A chosen name is shown with its rank and its higher classification, and can be changed.
import { useEffect, useId, useRef, useState } from "react";
import { ApiError } from "../../api/client";
import { contributeApi } from "../../contribute/api";
import { rankName } from "../../contribute/messages";
import type { AnchorValue } from "../../contribute/draft";
import type { AnchorSuggestion } from "../../contract/catalog";
import { useI18n } from "../../i18n";
import { Button } from "../../ui/Button";
import { Glyph } from "../../ui/Icon";
import { AnchorName } from "./AnchorName";
import styles from "./Contribute.module.css";

interface AnchorFieldProps {
  kind: AnchorValue["kind"];
  value: AnchorValue | null;
  onChange: (value: AnchorValue | null) => void;
  label: string;
  hint?: string;
  error?: string;
  optional?: boolean;
  /** The example in the empty field; by default a name of the kind (none for a host, whose example would mislead). */
  placeholder?: string;
}

type Lookup = { state: "idle" } | { state: "busy" } | { state: "done"; items: AnchorSuggestion[] }
  | { state: "failed"; unavailable: boolean };

export function AnchorField({ kind, value, onChange, label, hint, error, optional, placeholder }: AnchorFieldProps) {
  const { t } = useI18n();
  const id = useId();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [lookup, setLookup] = useState<Lookup>({ state: "idle" });
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setLookup({ state: "idle" });
      return undefined;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setLookup({ state: "busy" });
      contributeApi.anchors(kind, q, controller.signal).then(
        (items) => {
          setLookup({ state: "done", items });
          setActive(items.length ? 0 : -1);
        },
        (e: unknown) => {
          if (!controller.signal.aborted) {
            setLookup({ state: "failed", unavailable: e instanceof ApiError && e.status === 503 });
          }
        });
    }, 250);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query, kind]);

  const items = lookup.state === "done" ? lookup.items : [];
  const choose = (item: AnchorSuggestion) => {
    onChange({ kind, ref: item.ref, name: item.name, rank: item.rank ?? null,
      classification: item.classification ?? null });
    setQuery("");
    setOpen(false);
  };

  if (value) {
    return (
      <div className={styles.field}>
        <span className={styles.fieldLabel}>{label}</span>
        <div className={styles.chosen}>
          <div>
            <p className={styles.chosenName}>
              <AnchorName kind={kind} rank={value.rank} name={value.name} />
              {value.rank ? <span className={styles.rank}>{rankName(t, value.rank)}</span> : null}
            </p>
            <p className={styles.chosenRef}>
              {kind === "taxon" ? t("anchor.gbifKey", { key: value.ref }) : value.ref}
              {value.classification ? ` · ${value.classification}` : ""}
            </p>
          </div>
          <Button variant="quiet" size="small" icon="edit" onClick={() => {
            onChange(null);
            requestAnimationFrame(() => input.current?.focus());
          }}>{t("anchor.change")}</Button>
        </div>
        {error ? <p className={styles.fieldError}><Glyph name="warning" size={16} /><span>{error}</span></p> : null}
      </div>
    );
  }

  const listId = `${id}-list`;
  const status = lookup.state === "busy" ? t("anchor.searching")
    : lookup.state === "failed" ? (lookup.unavailable ? t("anchor.unavailable") : t("anchor.failed"))
      : lookup.state === "done" && items.length === 0 ? t("anchor.none", { query: query.trim() })
        : lookup.state === "done" ? t("anchor.found", { count: items.length }) : "";

  return (
    <div className={styles.field} data-invalid={error ? "true" : undefined}>
      <label className={styles.fieldLabel} htmlFor={id}>
        {label}{optional ? <span className={styles.optional}> ({t("field.optional")})</span> : null}
      </label>
      <div className={styles.comboWrap}>
        <Glyph name="search" size={20} className={styles.comboGlyph} />
        <input ref={input} id={id} className={styles.comboInput} role="combobox" aria-autocomplete="list"
          aria-expanded={open && items.length > 0} aria-controls={listId}
          aria-activedescendant={open && active >= 0 ? `${listId}-${active}` : undefined}
          aria-invalid={error ? true : undefined} aria-describedby={[hint ? `${id}-hint` : "", error ? `${id}-error` : "",
            `${id}-status`].filter(Boolean).join(" ")}
          autoComplete="off" spellCheck={false} value={query} placeholder={placeholder ?? t(`anchor.placeholder.${kind}`)}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => window.setTimeout(() => setOpen(false), 150)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setOpen(true);
              setActive((a) => Math.min(items.length - 1, a + 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((a) => Math.max(0, a - 1));
            } else if (e.key === "Enter" && open && active >= 0 && items[active]) {
              e.preventDefault();
              choose(items[active]);
            } else if (e.key === "Escape") {
              setOpen(false);
            }
          }} />
      </div>
      <ul id={listId} role="listbox" aria-label={label} className={styles.options}
        hidden={!open || items.length === 0}>
        {items.map((item, i) => (
          <li key={`${item.ref}-${i}`} id={`${listId}-${i}`} role="option" aria-selected={i === active}
            className={styles.option} onMouseDown={(e) => e.preventDefault()} onClick={() => choose(item)}
            onMouseEnter={() => setActive(i)}>
            <span className={styles.optionName}>
              <AnchorName kind={kind} rank={item.rank} name={item.name} />
              {item.rank ? <span className={styles.rank}>{rankName(t, item.rank)}</span> : null}
              {item.classification ? <span className={styles.rank}>{item.classification}</span> : null}
            </span>
            {item.context ? <span className={styles.optionContext}>{item.context}</span> : null}
          </li>
        ))}
      </ul>
      <p id={`${id}-status`} className={styles.comboStatus} role="status" aria-live="polite">{status}</p>
      {hint ? <p id={`${id}-hint`} className={styles.fieldHint}>{hint}</p> : null}
      {error ? <p id={`${id}-error`} className={styles.fieldError}><Glyph name="warning" size={16} /><span>{error}</span></p>
        : null}
    </div>
  );
}
