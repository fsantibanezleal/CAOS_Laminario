// The room and the language, each a small segmented radio group: one tab stop, arrow keys move the choice (the
// platform's radio behaviour), every option named in words and not only by its glyph.
import { useId } from "react";
import { useRoom, type RoomChoice } from "../design/theme";
import { LANGS, useI18n, type Lang } from "../i18n";
import { Glyph } from "./Icon";
import styles from "./Switches.module.css";

interface Option<V extends string> { value: V; label: string; glyph?: string; short?: string }

function Segmented<V extends string>({ legend, value, options, onChange }: {
  legend: string; value: V; options: Option<V>[]; onChange: (v: V) => void;
}) {
  const name = useId();
  return (
    <fieldset className={styles.segmented}>
      <legend className="visually-hidden">{legend}</legend>
      {options.map((o) => (
        <label key={o.value} className={styles.option} title={o.label}>
          <input type="radio" name={name} value={o.value} checked={value === o.value} onChange={() => onChange(o.value)} />
          {o.glyph ? <Glyph name={o.glyph} size={20} /> : null}
          {o.short ? <span className={styles.short} aria-hidden="true">{o.short}</span> : null}
          <span className="visually-hidden">{o.label}</span>
        </label>
      ))}
    </fieldset>
  );
}

export function RoomSwitch() {
  const { choice, setChoice } = useRoom();
  const { t } = useI18n();
  const options: Option<RoomChoice>[] = [
    { value: "system", label: t("room.system"), glyph: "system" },
    { value: "daylight", label: t("room.daylight"), glyph: "daylight" },
    { value: "lamplit", label: t("room.lamplit"), glyph: "lamplit" },
  ];
  return <Segmented legend={t("room.label")} value={choice} options={options} onChange={setChoice} />;
}

export function LanguageSwitch() {
  const { lang, setLang, t } = useI18n();
  const options: Option<Lang>[] = LANGS.map((l) => ({ value: l, label: t(`lang.${l}`), short: l.toUpperCase() }));
  return <Segmented legend={t("lang.label")} value={lang} options={options} onChange={setLang} />;
}
