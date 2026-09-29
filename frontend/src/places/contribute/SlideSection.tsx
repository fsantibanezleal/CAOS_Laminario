// The second section: the slide as an object. Its format (each drawn to scale), a custom size, the coverslip, how it
// was prepared (the preparations named and drawn as the collection's facet), the stain and the mountant, the
// catalogue number and the label's own note, when and by whom it was prepared.
import { COVERSLIPS, FORMATS, SLIDE_MM, type CaseDraft } from "../../contribute/draft";
import { useI18n } from "../../i18n";
import { localised, useTree } from "../../tree/TreeProvider";
import { Select, TextField } from "../../ui/Field";
import { Icon } from "../../ui/Icon";
import styles from "./Contribute.module.css";
import type { SectionProps } from "./sections";

type SlideFields = CaseDraft["slide"];

function FormatDrawing({ format }: { format: SlideFields["format"] }) {
  const [w, h] = format === "custom" ? [60, 30] : SLIDE_MM[format];
  const scale = 1.2;
  return (
    <svg viewBox="0 0 96 64" width={96} height={64} aria-hidden="true" className={styles.formatDrawing}>
      <rect x={(96 - w * scale) / 2} y={(64 - h * scale) / 2} width={w * scale} height={h * scale} rx={1.5}
        className={format === "custom" ? styles.formatCustom : styles.formatGlass} />
      <rect x={(96 - w * scale) / 2} y={(64 - h * scale) / 2} width={Math.min(24, w * 0.3) * scale} height={h * scale}
        rx={1.5} className={styles.formatFrost} />
    </svg>
  );
}

export function SlideSection({ draft, update, errorFor }: SectionProps) {
  const { t, lang } = useI18n();
  const tree = useTree();
  const s = draft.slide;
  const set = (change: Partial<SlideFields>) => update((d) => ({ ...d, slide: { ...d.slide, ...change } }));
  const preparations = tree.state === "ready" ? tree.tree.facets.get("preparation")?.values ?? [] : [];

  return (
    <div className={styles.sectionBody}>
      <fieldset className={styles.choiceCards} data-kind="format">
        <legend className={styles.fieldLabel}>{t("slide.format")}</legend>
        {FORMATS.map((f) => (
          <label key={f} className={styles.choiceCard} data-checked={s.format === f || undefined}>
            <input type="radio" name="format" value={f} checked={s.format === f} onChange={() => set({ format: f })} />
            <FormatDrawing format={f} />
            <span>{t(`format.${f}`)}</span>
            <span className={styles.choiceNote}>{t(`format.${f}.note`)}</span>
          </label>
        ))}
      </fieldset>
      {s.format === "custom" ? (
        <div className={styles.grid2}>
          <TextField label={t("slide.width")} value={s.customW} inputMode="decimal" hint={t("slide.size.hint")}
            error={errorFor("slide.custom_mm", { prefix: true })} onChange={(e) => set({ customW: e.target.value })} />
          <TextField label={t("slide.height")} value={s.customH} inputMode="decimal"
            onChange={(e) => set({ customH: e.target.value })} />
        </div>
      ) : null}

      <div className={styles.grid2}>
        <Select label={t("slide.coverslip")} value={s.coverslip} error={errorFor("slide.coverslip")}
          onChange={(e) => set({ coverslip: e.target.value as SlideFields["coverslip"] })}
          options={COVERSLIPS.map((c) => ({ value: c, label: t(`coverslip.${c}`) }))} />
        {s.coverslip === "custom" ? (
          <div className={styles.pair}>
            <TextField label={t("slide.coverWidth")} value={s.coverW} inputMode="decimal"
              error={errorFor("slide.coverslip_custom_mm", { prefix: true })}
              onChange={(e) => set({ coverW: e.target.value })} />
            <TextField label={t("slide.coverHeight")} value={s.coverH} inputMode="decimal"
              onChange={(e) => set({ coverH: e.target.value })} />
          </div>
        ) : null}
      </div>

      <fieldset className={styles.choiceCards} data-kind="preparation">
        <legend className={styles.fieldLabel}>{t("slide.preparation")}</legend>
        {preparations.map((p) => (
          <label key={p.id} className={styles.choiceCard} data-checked={s.preparation === p.id || undefined}>
            <input type="radio" name="preparation" value={p.id} checked={s.preparation === p.id}
              onChange={() => set({ preparation: p.id as SlideFields["preparation"] })} />
            <Icon name={p.icon} size={32} />
            <span>{localised(p.name, lang)}</span>
          </label>
        ))}
        {errorFor("slide.preparation") ? <p className={styles.fieldError}>{errorFor("slide.preparation")}</p> : null}
      </fieldset>

      <div className={styles.grid2}>
        <TextField label={t("slide.stain")} optional value={s.stain} maxLength={80} placeholder={t("slide.stain.example")}
          error={errorFor("slide.stain")} onChange={(e) => set({ stain: e.target.value })} />
        <TextField label={t("slide.mountant")} optional value={s.mountant} maxLength={80}
          placeholder={t("slide.mountant.example")} error={errorFor("slide.mountant")}
          onChange={(e) => set({ mountant: e.target.value })} />
        <TextField label={t("slide.catalogueNumber")} optional value={s.catalogueNumber} maxLength={64}
          hint={t("slide.catalogueNumber.hint")} error={errorFor("slide.catalogue_number")}
          onChange={(e) => set({ catalogueNumber: e.target.value })} />
        <TextField label={t("slide.labelNote")} optional value={s.labelNote} maxLength={160}
          hint={t("slide.labelNote.hint")} error={errorFor("slide.label_note")}
          onChange={(e) => set({ labelNote: e.target.value })} />
        <TextField label={t("slide.preparedOn")} optional value={s.preparedOn} inputMode="numeric" placeholder="1962-08"
          hint={t("date.partial.hint")} error={errorFor("slide.prepared_on")}
          onChange={(e) => set({ preparedOn: e.target.value })} />
        <TextField label={t("slide.preparer")} optional value={s.preparer} maxLength={120}
          error={errorFor("slide.preparer")} onChange={(e) => set({ preparer: e.target.value })} />
      </div>
    </div>
  );
}
