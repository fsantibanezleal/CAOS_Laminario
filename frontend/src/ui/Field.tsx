// Text field, search field and select: always with a visible label, an optional hint, and an error that is named to
// assistive technology (aria-invalid, aria-describedby) and shown in words, not only in colour.
import { useId, useState, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import { useI18n } from "../i18n";
import styles from "./Field.module.css";
import { Glyph } from "./Icon";

interface FieldFrame {
  label: string;
  hint?: string;
  error?: string;
  optional?: boolean;
}

function Frame({ id, label, hint, error, optional, children }: FieldFrame & { id: string; children: ReactNode }) {
  const { t } = useI18n();
  return (
    <div className={styles.field} data-invalid={error ? "true" : undefined}>
      <label className={styles.label} htmlFor={id}>
        {label}
        {optional ? <span className={styles.optional}> ({t("field.optional")})</span> : null}
      </label>
      {children}
      {hint ? <p id={`${id}-hint`} className={styles.hint}>{hint}</p> : null}
      {error ? (
        <p id={`${id}-error`} className={styles.error}>
          <Glyph name="warning" size={16} />
          <span>{error}</span>
        </p>
      ) : null}
    </div>
  );
}

const describedBy = (id: string, hint?: string, error?: string) =>
  [hint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(Boolean).join(" ") || undefined;

export type TextFieldProps = FieldFrame & Omit<InputHTMLAttributes<HTMLInputElement>, "id">;

export function TextField({ label, hint, error, optional, className, ...input }: TextFieldProps) {
  const id = useId();
  return (
    <Frame id={id} label={label} hint={hint} error={error} optional={optional}>
      <input id={id} className={[styles.input, className].filter(Boolean).join(" ")} aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, hint, error)} {...input} />
    </Frame>
  );
}

export type SearchFieldProps = FieldFrame & Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "type"> & {
  onClear?: () => void;
};

export function SearchField({ label, hint, error, optional, value, defaultValue, onChange, onClear, ...input }:
  SearchFieldProps) {
  const id = useId();
  const { t } = useI18n();
  const [local, setLocal] = useState(String(defaultValue ?? ""));
  const current = value !== undefined ? String(value) : local;
  return (
    <Frame id={id} label={label} hint={hint} error={error} optional={optional}>
      <div className={styles.search}>
        <Glyph name="search" size={20} className={styles.searchGlyph} />
        <input id={id} type="search" className={styles.input} value={current} aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(id, hint, error)}
          onChange={(e) => { setLocal(e.target.value); onChange?.(e); }} {...input} />
        {current ? (
          <button type="button" className={styles.clear} aria-label={t("action.clear")}
            onClick={() => { setLocal(""); onClear?.(); }}>
            <Glyph name="close" size={16} />
          </button>
        ) : null}
      </div>
    </Frame>
  );
}

export type SelectProps = FieldFrame & Omit<SelectHTMLAttributes<HTMLSelectElement>, "id"> & {
  options: { value: string; label: string }[];
  /** Options in named groups, after ``options`` (a vocabulary by its families). */
  groups?: { label: string; options: { value: string; label: string }[] }[];
};

export function Select({ label, hint, error, optional, options, groups, className, ...select }: SelectProps) {
  const id = useId();
  return (
    <Frame id={id} label={label} hint={hint} error={error} optional={optional}>
      <div className={styles.selectWrap}>
        <select id={id} className={[styles.input, styles.select, className].filter(Boolean).join(" ")}
          aria-invalid={error ? true : undefined} aria-describedby={describedBy(id, hint, error)} {...select}>
          {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          {groups?.map((g) => (
            <optgroup key={g.label} label={g.label}>
              {g.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </optgroup>
          ))}
        </select>
        <Glyph name="chevron-down" size={20} className={styles.chevron} />
      </div>
    </Frame>
  );
}
