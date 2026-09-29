// The first section: what the slide shows. The kind of thing (an organism, a rock, a mineral, a crystal, a material),
// then its name from the backbone or the vocabularies; for an organism, the part of it on the slide, whether it is
// recent, fossil or in amber, a host it lived on, and a type status; then when and by whom it was collected.
import { useMemo } from "react";
import { api } from "../../api/client";
import { useResource } from "../../api/useResource";
import { ANCHOR_KINDS, PRESERVATION, TYPE_STATUS, type AnchorValue, type CaseDraft } from "../../contribute/draft";
import { known } from "../../contribute/messages";
import { useI18n } from "../../i18n";
import type { MessageKey } from "../../i18n/en";
import { Select, TextField } from "../../ui/Field";
import { Icon } from "../../ui/Icon";
import { AnchorField } from "./AnchorField";
import styles from "./Contribute.module.css";
import type { SectionProps } from "./sections";

const KIND_ICONS: Record<AnchorValue["kind"], string> = {
  taxon: "life", rock: "earth.rocks", mineral: "earth.minerals", crystal: "matter.crystals",
  material: "matter.materials",
};

export function SpecimenSection({ draft, update, errorFor }: SectionProps) {
  const { t, lang } = useI18n();
  const s = draft.specimen;
  const kind = s.anchor?.kind ?? s.kindChoice ?? "taxon";
  const parts = useResource("vocab-parts", (signal) => api.parts(signal));
  const set = (change: Partial<CaseDraft["specimen"]>) => update((d) => ({ ...d, specimen: { ...d.specimen, ...change } }));

  const partOptions = useMemo(() => {
    const groups = new Map<string, { value: string; label: string }[]>();
    for (const p of parts.value ?? []) {
      const list = groups.get(p.group) ?? [];
      list.push({ value: p.id, label: p.name[lang] });
      groups.set(p.group, list);
    }
    return groups;
  }, [parts.value, lang]);

  return (
    <div className={styles.sectionBody}>
      <fieldset className={styles.choiceCards}>
        <legend className={styles.fieldLabel}>{t("specimen.kind")}</legend>
        {ANCHOR_KINDS.map((k) => (
          <label key={k} className={styles.choiceCard} data-checked={kind === k || undefined}>
            <input type="radio" name="anchor-kind" value={k} checked={kind === k}
              onChange={() => set({ kindChoice: k, anchor: s.anchor?.kind === k ? s.anchor : null,
                host: k === "taxon" ? s.host : null, part: k === "taxon" ? s.part : "",
                preservation: k === "taxon" ? s.preservation : "recent" })} />
            <Icon name={KIND_ICONS[k]} size={32} />
            <span>{t(`anchor.kind.${k}`)}</span>
          </label>
        ))}
      </fieldset>

      <AnchorField kind={kind} value={s.anchor} onChange={(anchor) => set({ anchor })} label={t(`anchor.label.${kind}`)}
        hint={t(`anchor.hint.${kind}`)}
        error={errorFor("specimen.anchor", { prefix: true })} />

      {kind === "taxon" ? (
        <div className={styles.grid2}>
          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="part">{t("specimen.part")}
              <span className={styles.optional}> ({t("field.optional")})</span></label>
            <select id="part" className={styles.select} value={s.part} aria-describedby="part-hint"
              aria-invalid={errorFor("specimen.part") ? true : undefined}
              onChange={(e) => set({ part: e.target.value })}>
              <option value="">{t("specimen.part.whole")}</option>
              {[...partOptions].map(([group, options]) => (
                <optgroup key={group} label={known(`specimen.partGroup.${group}`) ? t(`specimen.partGroup.${group}` as
                  MessageKey) : group}>
                  {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </optgroup>
              ))}
            </select>
            <p id="part-hint" className={styles.fieldHint}>{t("specimen.part.hint")}</p>
            {errorFor("specimen.part") ? <p className={styles.fieldError}>{errorFor("specimen.part")}</p> : null}
          </div>
          <Select label={t("specimen.typeStatus")} optional value={s.typeStatus}
            error={errorFor("specimen.type_status")}
            onChange={(e) => set({ typeStatus: e.target.value as CaseDraft["specimen"]["typeStatus"] })}
            options={[{ value: "", label: t("specimen.typeStatus.none") },
              ...TYPE_STATUS.map((v) => ({ value: v, label: t(`typeStatus.${v}`) }))]} />
          <fieldset className={styles.inlineChoice}>
            <legend className={styles.fieldLabel}>{t("specimen.preservation")}</legend>
            {PRESERVATION.map((v) => (
              <label key={v}>
                <input type="radio" name="preservation" value={v} checked={s.preservation === v}
                  onChange={() => set({ preservation: v })} />
                <span>{t(`preservation.${v}`)}</span>
              </label>
            ))}
            {errorFor("specimen.preservation") ? <p className={styles.fieldError}>{errorFor("specimen.preservation")}</p>
              : null}
          </fieldset>
          <AnchorField kind="taxon" value={s.host} optional onChange={(host) => set({ host })}
            label={t("specimen.host")} hint={t("specimen.host.hint")} error={errorFor("specimen.host", { prefix: true })} />
        </div>
      ) : null}

      <div className={styles.grid2}>
        <TextField label={t("specimen.collectedOn")} optional value={s.collectedOn} inputMode="numeric"
          placeholder="2019-04-20" hint={t("date.partial.hint")} error={errorFor("specimen.collected_on")}
          onChange={(e) => set({ collectedOn: e.target.value })} />
        <TextField label={t("specimen.collector")} optional value={s.collector} maxLength={120} autoComplete="name"
          error={errorFor("specimen.collector")} onChange={(e) => set({ collector: e.target.value })} />
      </div>
    </div>
  );
}
