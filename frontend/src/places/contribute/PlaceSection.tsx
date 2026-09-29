// The fourth section: where the specimen was found. The locality in words, the point (a click on the map, a
// photograph's position, or typed), its uncertainty, the country, and who may see the place: everyone, only a cell
// of about 20 km, or no one (the photographs' positions then leave the files before they are sent, R-087).
import { lazy, Suspense, useMemo } from "react";
import { GEOPRIVACY, number, type CaseDraft } from "../../contribute/draft";
import { useI18n } from "../../i18n";
import { useTree } from "../../tree/TreeProvider";
import { Select, TextField } from "../../ui/Field";
import { Skeleton } from "../../ui/Feedback";
import { Glyph } from "../../ui/Icon";
import styles from "./Contribute.module.css";
import type { SectionProps } from "./sections";

const PointMap = lazy(() => import("./PointMap").then((m) => ({ default: m.PointMap })));
const GLYPHS = { open: "pin", obscured: "cell", private: "lock" } as const;

export function PlaceSection({ draft, update, errorFor, flagFor }: SectionProps) {
  const { t, lang } = useI18n();
  const tree = useTree();
  const p = draft.specimen;
  const set = (change: Partial<CaseDraft["specimen"]>) => update((d) => ({ ...d, specimen: { ...d.specimen, ...change } }));
  const lat = number(p.lat);
  const lon = number(p.lon);
  const point = typeof lat === "number" && typeof lon === "number" && Math.abs(lat) <= 90 && Math.abs(lon) <= 180
    ? { lat, lon } : null;
  const uncertainty = number(p.uncertainty);
  const photos = useMemo(() => draft.images.flatMap((i) => (i.photo?.gps ? [i.photo.gps] : [])), [draft.images]);

  const countries = useMemo(() => {
    if (tree.state !== "ready") return [];
    const collator = new Intl.Collator(lang);
    return Object.entries(tree.tree.countries).map(([code, names]) => ({ value: code, label: names[lang] }))
      .sort((a, b) => collator.compare(a.label, b.label));
  }, [tree, lang]);

  return (
    <div className={styles.sectionBody}>
      <TextField label={t("place.locality")} optional value={p.locality} maxLength={300}
        hint={t("place.locality.example")} error={errorFor("specimen.locality_text")}
        onChange={(e) => set({ locality: e.target.value })} />

      <Suspense fallback={<Skeleton lines={4} />}>
        <PointMap point={point} uncertainty={typeof uncertainty === "number" ? uncertainty : null} photos={photos}
          onPick={(pt) => set({ lat: String(pt.lat), lon: String(pt.lon), uncertainty: p.uncertainty || "30" })} />
      </Suspense>

      <div className={styles.grid3}>
        <TextField label={t("place.lat")} optional value={p.lat} inputMode="decimal" hint={t("place.coordinates.hint")}
          error={errorFor("specimen.coordinates.lat") ?? errorFor("specimen.coordinates")}
          onChange={(e) => set({ lat: e.target.value })} />
        <TextField label={t("place.lon")} optional value={p.lon} inputMode="decimal"
          error={errorFor("specimen.coordinates.lon")} onChange={(e) => set({ lon: e.target.value })} />
        <TextField label={t("place.uncertainty")} optional value={p.uncertainty} inputMode="numeric"
          hint={t("place.uncertainty.hint")} error={errorFor("specimen.coordinates.uncertainty_m")}
          onChange={(e) => set({ uncertainty: e.target.value })} />
      </div>
      {point ? (
        <p><button type="button" className={styles.linkButton}
          onClick={() => set({ lat: "", lon: "", uncertainty: "" })}>{t("place.clearPoint")}</button></p>
      ) : null}

      <Select label={t("place.country")} optional value={p.country.toUpperCase()} hint={t("place.country.hint")}
        error={errorFor("specimen.country")} onChange={(e) => set({ country: e.target.value })}
        options={[{ value: "", label: t("place.country.fromPoint") }, ...countries]} />
      {flagFor("specimen.country") ? <p className={styles.flagText}>{flagFor("specimen.country")}</p> : null}

      <fieldset className={styles.privacyCards}>
        <legend className={styles.fieldLabel}>{t("place.geoprivacy")}</legend>
        {GEOPRIVACY.map((g) => (
          <label key={g} className={styles.privacyCard} data-checked={p.geoprivacy === g || undefined}>
            <input type="radio" name="geoprivacy" value={g} checked={p.geoprivacy === g}
              onChange={() => set({ geoprivacy: g })} />
            <Glyph name={GLYPHS[g]} size={24} />
            <span className={styles.privacyTitle}>{t(`geoprivacy.${g}`)}</span>
            <span className={styles.choiceNote}>{t(`geoprivacy.${g}.about`)}</span>
          </label>
        ))}
      </fieldset>
      {p.geoprivacy === "private" && photos.length ? (
        <p className={styles.notice}><Glyph name="lock" size={20} />
          <span>{t("place.privatePhotos", { count: photos.length })}</span></p>
      ) : null}
    </div>
  );
}
