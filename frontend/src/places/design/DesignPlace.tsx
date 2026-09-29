// The specimen place (/design): every token and primitive of the visual system in the current room and language. It
// is what the screenshots and the gates look at (R-080, R-081, R-085, R-089) until the places of U10 and U11 exist.
import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import tokens from "../../design/tokens.json";
import { useRoom } from "../../design/theme";
import { useSpriteNames } from "../../design/sprite";
import { useI18n } from "../../i18n";
import { Button, IconButton } from "../../ui/Button";
import { Checkbox, RadioGroup, Switch } from "../../ui/Choice";
import { CollectionTag, FacetChip, RemovableChip } from "../../ui/Chip";
import { EmptyState, Progress, Skeleton } from "../../ui/Feedback";
import { SearchField, Select, TextField } from "../../ui/Field";
import { Glyph } from "../../ui/Icon";
import { Masthead } from "../../ui/Masthead";
import { Dialog, Tooltip, useToast } from "../../ui/Overlay";
import { PlaceTrail } from "../../ui/PlaceTrail";
import { Tabs } from "../../ui/Tabs";
import styles from "./DesignPlace.module.css";

const COLOUR_TOKENS = Object.keys(tokens.rooms.daylight.colours);
const COLLECTIONS = Object.keys(tokens.collections);

function Swatch({ name }: { name: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [value, setValue] = useState("");
  const { room } = useRoom();
  useEffect(() => {
    if (ref.current) setValue(getComputedStyle(ref.current).getPropertyValue(`--c-${name}`).trim());
  }, [name, room]);
  return (
    <div className={styles.swatch} ref={ref}>
      <span className={styles.chipColour} style={{ background: `var(--c-${name})` }} />
      <code className={styles.token}>--c-{name}</code>
      <span className={styles.hex}>{value}</span>
    </div>
  );
}

export function DesignPlace() {
  const i18n = useI18n();
  const { t, lang, plural } = i18n;
  const names = useSpriteNames();
  const toast = useToast();
  const [preparation, setPreparation] = useState("section");
  const [modality, setModality] = useState<"brightfield" | "polarised">("brightfield");
  const [stained, setStained] = useState(true);
  const [showPlace, setShowPlace] = useState(false);
  const [facets, setFacets] = useState<Record<string, boolean>>({ smear: true });
  const [filters, setFilters] = useState(["Chile", "1990"]);
  const [tab, setTab] = useState<"macro" | "micro" | "provenance">("macro");
  const [dialog, setDialog] = useState(false);
  const [onStage, setOnStage] = useState(false);

  const moveSlide = () => {
    const doc = document as Document & { startViewTransition?: (cb: () => void) => unknown };
    if (doc.startViewTransition && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
      doc.startViewTransition(() => flushSync(() => setOnStage((v) => !v)));
    } else {
      setOnStage((v) => !v);
    }
  };

  const name = (id: string) => names[id]?.[lang] ?? id;

  return (
    <>
      <Masthead trail={<PlaceTrail places={[{ label: t("app.name"), href: "/" }, { label: t("place.design") }]} />} />
      <main id="content" className={styles.page}>
        <section className={styles.intro}>
          <h1>{t("design.title")}</h1>
          <p>{t("design.intro")}</p>
        </section>

        <section className={styles.section} aria-labelledby="rooms">
          <h2 id="rooms">{t("design.rooms")}</h2>
          <p className={styles.note}>{t("design.rooms.note")}</p>
          <div className={styles.swatches}>
            {COLOUR_TOKENS.map((c) => <Swatch key={c} name={c} />)}
          </div>
        </section>

        <section className={styles.section} aria-labelledby="type">
          <h2 id="type">{t("design.type")}</h2>
          <div className={styles.faces}>
            <figure>
              <figcaption>{t("design.type.display")}</figcaption>
              <p className={styles.display}>{name("earth.minerals")}, {name("life.fungi")}</p>
            </figure>
            <figure>
              <figcaption>{t("design.type.reading")}</figcaption>
              <p>{t("design.type.sample")}</p>
              <p className={styles.small}>{plural("count.slides", 1)} · {plural("count.slides", 505)} ·{" "}
                {i18n.list([name("life.plants"), name("life.fungi"), name("earth.rocks")])} ·{" "}
                {i18n.date("2026-09-29")}</p>
            </figure>
            <figure>
              <figcaption>{t("design.type.label")}</figcaption>
              {/* A base-collection slide, as its lock records it (data/base/lock.yaml). */}
              <div className={styles.label}>
                <span className={styles.labelNumber}>NHMUK010173454</span>
                <span><i>Pediculus humanus</i> Linnaeus, 1758</span>
                <span>Niupani, Rennell Island</span>
                <span>{i18n.date("1962-08-31")}</span>
                <span>ex <i>Homo sapiens</i></span>
              </div>
            </figure>
          </div>
        </section>

        <section className={styles.section} aria-labelledby="collections">
          <h2 id="collections">{t("design.collections")}</h2>
          <p className={styles.note}>{t("design.collections.note")}</p>
          <div className={styles.tags}>
            {COLLECTIONS.map((c) => <CollectionTag key={c} collection={c} name={name(c)} />)}
          </div>
          <div className={styles.tags}>
            <CollectionTag collection="earth.rocks" name={name("earth.rocks")} size="large" />
            <CollectionTag collection="life.plants" name={name("life.plants")} size="large" />
          </div>
        </section>

        <section className={styles.section} aria-labelledby="controls">
          <h2 id="controls">{t("design.controls")}</h2>
          <div className={styles.row}>
            <Button variant="primary" onClick={() => toast.show(t("demo.saved"), "good")}>{t("demo.save")}</Button>
            <Button variant="secondary">{t("demo.submit")}</Button>
            <Button variant="quiet">{t("demo.later")}</Button>
            <Button variant="danger" onClick={() => setDialog(true)}>{t("demo.delete")}</Button>
            <Button variant="secondary" size="small" icon="plus">{t("demo.later")}</Button>
            <Button variant="primary" busy>{t("demo.save")}</Button>
            <Button variant="secondary" disabled>{t("demo.submit")}</Button>
            <IconButton icon="search" label={t("action.search")} variant="secondary" />
            <Tooltip text={t("demo.tooltip")}>
              <IconButton icon="info" label={t("demo.modality.polarised")} />
            </Tooltip>
          </div>
          <div className={styles.grid}>
            <SearchField label={t("demo.search")} hint={t("demo.search.hint")} />
            <TextField label={t("demo.name")} defaultValue="R. W." error={t("demo.name.error")} />
            <Select label={t("demo.preparation")} value={preparation} onChange={(e) => setPreparation(e.target.value)}
              options={[{ value: "section", label: t("demo.preparation.section") },
                { value: "smear", label: t("demo.preparation.smear") },
                { value: "thin", label: t("demo.preparation.thin") }]} />
            <TextField label={t("demo.name")} optional disabled defaultValue="Diana Perez" />
          </div>
          <div className={styles.grid}>
            <RadioGroup legend={t("demo.modality")} value={modality} onChange={setModality} inline
              options={[{ value: "brightfield", label: t("demo.modality.brightfield") },
                { value: "polarised", label: t("demo.modality.polarised") }]} />
            <div className={styles.stack}>
              <Checkbox label={t("demo.stain")} checked={stained} onChange={(e) => setStained(e.target.checked)} />
              <Switch label={t("demo.public")} checked={showPlace} onChange={setShowPlace} />
            </div>
          </div>
          <div className={styles.row}>
            {(["section", "smear", "thin"] as const).map((k) => (
              // the counts are the base collection's, from its lock (505 slides)
              <FacetChip key={k} label={t(`demo.preparation.${k}`)} pressed={!!facets[k]} count={{ section: 72,
                smear: 42, thin: 78 }[k]} onChange={(p) => setFacets((f) => ({ ...f, [k]: p }))} />
            ))}
            {filters.map((f) => (
              <RemovableChip key={f} label={f} onRemove={() => setFilters((list) => list.filter((x) => x !== f))} />
            ))}
          </div>
          <Tabs label={t("place.slide")} selected={tab} onSelect={setTab} items={[
            { key: "macro", label: t("demo.tabs.macro"), panel: <p>{t("demo.tabs.macro.body")}</p> },
            { key: "micro", label: t("demo.tabs.micro"), panel: <p>{t("demo.tabs.micro.body")}</p> },
            { key: "provenance", label: t("demo.tabs.provenance"), panel: <p>{t("demo.tabs.provenance.body")}</p> },
          ]} />
          <PlaceTrail places={[
            { label: name("life"), href: "#", icon: "life" },
            { label: name("life.insects"), href: "#", icon: "life.insects" },
            { label: name("life.insects.lice"), href: "#", icon: "life.insects.lice" },
            { label: "NHMUK010173454" },
          ]} />
        </section>

        <section className={styles.section} aria-labelledby="feedback">
          <h2 id="feedback">{t("design.feedback")}</h2>
          <div className={styles.grid}>
            <Progress label={t("demo.progress")} value={0.62} />
            <Progress label={t("state.loading")} />
          </div>
          <div className={styles.grid}>
            <Skeleton lines={4} />
            <EmptyState icon="life.reptiles.scales" title={t("demo.empty.title")}
              action={<Button size="small" icon="plus">{t("demo.submit")}</Button>}>
              {t("demo.empty.body")}
            </EmptyState>
          </div>
        </section>

        <section className={styles.section} aria-labelledby="motion">
          <h2 id="motion">{t("design.motion")}</h2>
          <p className={styles.note}>{t("design.motion.note")}</p>
          <div className={styles.motion}>
            <div className={styles.drawer}>
              {!onStage ? <span className={styles.slideObject} style={{ viewTransitionName: "demo-slide" }}>
                <Glyph name="slide" size={48} /></span> : null}
            </div>
            <div className={styles.stage}>
              {onStage ? <span className={styles.slideObject} style={{ viewTransitionName: "demo-slide" }}>
                <Glyph name="slide" size={48} /></span> : null}
            </div>
          </div>
          <Button onClick={moveSlide}>{t("design.motion.try")}</Button>
        </section>
      </main>
      <Dialog open={dialog} title={t("demo.dialog.title")} onClose={() => setDialog(false)}
        actions={<>
          <Button variant="quiet" onClick={() => setDialog(false)}>{t("action.cancel")}</Button>
          <Button variant="danger" onClick={() => setDialog(false)}>{t("demo.delete")}</Button>
        </>}>
        <p>{t("demo.dialog.body")}</p>
      </Dialog>
    </>
  );
}
