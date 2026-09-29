// /s/<id>: a slide. At the top the slide as an object (its drawing, with its label and QR) and what can be done with
// it (print the label at 1:1, read the label, download the drawing, the IIIF manifest); then what can be looked at
// under the microscope, the photographs, the record, and where every image came from (R-1107).
import { useState } from "react";
import { Link, useParams } from "wouter";
import { api, labelPdf, slideDrawing } from "../../api/client";
import { useResource } from "../../api/useResource";
import type { AssetRecord, SlideRecord } from "../../contract/catalog";
import { useI18n } from "../../i18n";
import { en, type MessageKey } from "../../i18n/en";
import { Place } from "../../router/Place";
import { stageItems, thumbnail, type StageItem } from "../../slide/assets";
import { nameParts } from "../../slide/names";
import { LabelReading, SlideObject } from "../../slide/SlideObject";
import { collectionOf, localised, nodeHref, pathTo, useTree, type TreeIndex } from "../../tree/TreeProvider";
import { Button } from "../../ui/Button";
import { CollectionTag } from "../../ui/Chip";
import { EmptyState, Skeleton } from "../../ui/Feedback";
import { Glyph } from "../../ui/Icon";
import { Dialog } from "../../ui/Overlay";
import { NotFoundPlace } from "../NotFoundPlace";
import styles from "./SlidePlace.module.css";

/** The SHA-256 of the file an image was made from: its source's (the base collection) or its upload's. */
const originalSha = (a: SlideRecord["assets"][number]) => a.original_sha256 ?? a.source?.sha256 ?? null;

export function SlidePlace() {
  const { id } = useParams<{ id: string }>();
  const { t } = useI18n();
  const tree = useTree();
  const slide = useResource(`slide:${id.toUpperCase()}`, (signal) => api.slide(id, signal));
  if (slide.state === "error") {
    return (slide.error as { status?: number }).status === 404 ? <NotFoundPlace /> : (
      <Place title={t("slide.title")}><p role="alert">{t("explore.error")}</p></Place>
    );
  }
  if (!slide.value || tree.state !== "ready") {
    return <Place title={t("state.loading")} ready={false}><Skeleton lines={6} /></Place>;
  }
  return <SlideView record={slide.value} tree={tree.tree} />;
}

export function SlideName({ record }: { record: Pick<SlideRecord, "anchor"> }) {
  return (
    <>
      {nameParts(record.anchor).map((part, i) => (
        <span key={i}>{i ? " " : ""}{part.italic ? <i className="binomial">{part.text}</i> : part.text}</span>
      ))}
    </>
  );
}

function SlideView({ record, tree }: { record: SlideRecord; tree: TreeIndex }) {
  const { t, lang } = useI18n();
  const [reading, setReading] = useState(false);
  const [photo, setPhoto] = useState<AssetRecord | null>(null);
  const collection = collectionOf(record.placement.node);
  const collectionNode = collection ? tree.byId.get(collection) : undefined;
  const trail = [{ label: t("nav.collections"), href: "/" }, ...pathTo(tree, record.placement.node).map((n) => ({
    label: localised(n.name, lang), href: nodeHref(n.id), icon: n.id })), { label: record.id }];
  const items = stageItems(record.assets);
  const macro = record.assets.filter((a) => a.family === "macro" && a.status === "ready");
  const scannerLabel = macro.find((a) => a.role === "label");

  return (
    <Place title={`${record.label.name} (${record.id})`} trail={trail}
      heading={<span className={styles.heading}><SlideName record={record} /></span>}>
      <div className={styles.meta}>
        {collectionNode ? <CollectionTag collection={collectionNode.id} name={localised(collectionNode.name, lang)} /> : null}
        <span className={styles.id}>{record.id}</span>
        {record.origin === "base" ? <span className={styles.origin}>{t("origin.base")}</span> : null}
      </div>

      <section className={styles.objectArea} aria-label={t("slide.object")}>
        <SlideObject slideId={record.id} />
        <div className={styles.actions}>
          <a className={styles.action} href={labelPdf(record.id, lang)} target="_blank" rel="noreferrer">
            <Glyph name="slide" size={20} />{t("slide.print")}
          </a>
          <Button icon="search" onClick={() => setReading(true)}>{t("slide.read")}</Button>
          <a className={styles.action} href={slideDrawing(record.id, lang)} download={`laminario-${record.id}.svg`}>
            {t("slide.download")}
          </a>
          <a className={styles.action} href={record.manifest_url}>{t("slide.manifest")}</a>
        </div>
        <p className={styles.permalink}>
          <span>{t("slide.permalink")}</span> <a href={record.permalink}>{record.permalink}</a>
        </p>
      </section>

      <div className={styles.columns}>
        <div className={styles.main}>
          <section aria-labelledby="stage-items">
            <h2 id="stage-items" className={styles.sectionTitle}>{t("slide.microscope")}</h2>
            {items.length ? (
              <ul className={styles.items}>
                {items.map((item) => <li key={item.key}><StageCard slideId={record.id} item={item} tree={tree} /></li>)}
              </ul>
            ) : <EmptyState icon={record.placement.node} title={t("slide.micro.none")}>{t("slide.micro.none.body")}</EmptyState>}
          </section>

          {macro.length ? (
            <section aria-labelledby="photographs">
              <h2 id="photographs" className={styles.sectionTitle}>{t("slide.photographs")}</h2>
              <ul className={styles.gallery}>
                {macro.map((a) => {
                  const src = thumbnail(a, 600);
                  return src ? (
                    <li key={a.id}>
                      <button type="button" className={styles.photo} onClick={() => setPhoto(a)}>
                        <img src={src} alt={a.caption ?? t(`role.${a.role}` as MessageKey)} loading="lazy" />
                        <span>{t(`role.${a.role}` as MessageKey)}</span>
                      </button>
                    </li>
                  ) : null;
                })}
              </ul>
            </section>
          ) : null}

          <Provenance record={record} />
        </div>
        <Record record={record} tree={tree} />
      </div>

      <Dialog open={reading} title={t("slide.read")} onClose={() => setReading(false)}>
        <div className={styles.readingPair}>
          <figure>
            <LabelReading slideId={record.id} />
            <figcaption>{t("slide.read.drawn")}</figcaption>
          </figure>
          {scannerLabel && thumbnail(scannerLabel, 800) ? (
            <figure>
              <img src={thumbnail(scannerLabel, 800)!} alt={t("slide.read.scanned")} />
              <figcaption>{t("slide.read.scanned")}</figcaption>
            </figure>
          ) : null}
        </div>
      </Dialog>
      <Dialog open={photo !== null} title={photo ? t(`role.${photo.role}` as MessageKey) : ""} onClose={() => setPhoto(null)}>
        {photo && thumbnail(photo, 1600) ? (
          <figure className={styles.photoLarge}>
            <img src={thumbnail(photo, 1600)!} alt={photo.caption ?? t(`role.${photo.role}` as MessageKey)} />
            {photo.caption ? <figcaption>{photo.caption}</figcaption> : null}
          </figure>
        ) : null}
      </Dialog>
    </Place>
  );
}

function StageCard({ slideId, item, tree }: { slideId: string; item: StageItem; tree: TreeIndex }) {
  const { t, plural, lang, number } = useI18n();
  const src = thumbnail(item.first, 480);
  const modality = item.first.modality ? tree.facets.get("modality")?.values.find((v) => v.id === item.first.modality) : undefined;
  const what = item.kind === "stack"
    ? t("slide.item.stack", { planes: plural("count.planes", item.planes.length) })
    : item.kind === "pair" ? t("slide.item.pair") : t("slide.item.single");
  return (
    <Link href={`/s/${slideId}/stage/${item.first.id}`} className={styles.card} data-stage-item={item.kind}>
      <span className={styles.cardImage}>{src ? <img src={src} alt="" loading="lazy" /> : null}</span>
      <span className={styles.cardText}>
        <span className={styles.cardTitle}>{what}</span>
        <span className={styles.cardFacts}>
          {modality ? localised(modality.name, lang) : null}
          {item.pixelUm ? ` · ${t("slide.pixel", { um: number(item.pixelUm, { maximumSignificantDigits: 3 }) })}`
            : ` · ${t("stage.unscaled")}`}
        </span>
        <span className={styles.cardOpen}>{t("slide.open.stage")}<Glyph name="chevron-right" size={16} /></span>
      </span>
    </Link>
  );
}

function Record({ record, tree }: { record: SlideRecord; tree: TreeIndex }) {
  const { t, lang, date } = useI18n();
  const rankName = (rank: string) => {
    const key = `rank.${rank.toLowerCase()}`;
    return key in en ? t(key as MessageKey) : rank.toLowerCase();
  };
  const label = record.label;
  const prep = tree.facets.get("preparation")?.values.find((v) => v.id === label.preparation);
  const country = record.place.country ? tree.countries[record.place.country]?.[lang] : undefined;
  const day = (value?: string | null) => (value ? date(value, value.length > 7
    ? { year: "numeric", month: "long", day: "numeric" } : value.length > 4 ? { year: "numeric", month: "long" }
    : { year: "numeric" }) : null);
  const anchorLink = record.anchor.kind === "taxon" && /^\d+$/.test(record.anchor.ref)
    ? `https://www.gbif.org/species/${record.anchor.ref}` : null;
  const rows: [string, React.ReactNode][] = [
    [t("slide.field.name"), <>{anchorLink ? <a href={anchorLink}><SlideName record={record} /></a> : <SlideName record={record} />}
      {record.anchor.rank ? <span className={styles.muted}> ({rankName(record.anchor.rank)})</span> : null}</>],
    [t("facet.kind"), t(`kind.${record.anchor.kind}` as MessageKey)],
  ];
  if (record.host) rows.push([t("slide.field.host"), <SlideName record={{ anchor: record.host }} />]);
  if (label.type_status) rows.push([t("slide.field.type"), <span className={styles.type}>{label.type_status}</span>]);
  rows.push([t("facet.preparation"), [prep ? localised(prep.name, lang) : label.preparation, label.stain, label.mountant]
    .filter(Boolean).join(" · ")]);
  const where = [label.locality_text ?? record.place.locality_text, country].filter(Boolean).join(", ");
  if (where) rows.push([t("slide.field.place"), where]);
  if (label.collected_on || label.collector) {
    rows.push([t("slide.field.collected"), [day(label.collected_on), label.collector].filter(Boolean).join(" · ")]);
  }
  if (label.prepared_on || label.preparer) {
    rows.push([t("slide.field.prepared"), [day(label.prepared_on), label.preparer].filter(Boolean).join(" · ")]);
  }
  if (label.catalogue_number) rows.push([t("slide.field.catalogue"), <span className={styles.mono}>{label.catalogue_number}</span>]);
  rows.push([t("slide.field.format"), `${record.format.width_mm} x ${record.format.height_mm} mm${record.format.assumed
    ? ` (${t("slide.format.assumed")})` : ""}`]);
  if (record.coverslip) rows.push([t("slide.field.coverslip"), `${record.coverslip.long_mm} x ${record.coverslip.short_mm} mm`]);
  const node = tree.byId.get(record.placement.node);
  if (node) rows.push([t("slide.field.drawer"), <Link href={nodeHref(node.id)}>{localised(node.name, lang)}</Link>]);
  if (record.published_at) rows.push([t("slide.field.published"), day(record.published_at.slice(0, 10))]);

  return (
    <aside className={styles.record} aria-labelledby="record">
      <h2 id="record" className={styles.sectionTitle}>{t("slide.record")}</h2>
      <dl>{rows.map(([k, v]) => <div key={k} className={styles.row}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
      <div className={styles.quality} data-badge={record.quality.badge}>
        <p className={styles.badge}>{t(`quality.${record.quality.badge}` as MessageKey)}</p>
        <ul>
          {record.quality.checks.map((check) => (
            <li key={check.code} data-passed={check.passed}>
              <Glyph name={check.passed ? "check" : "warning"} size={16} />
              {t(`quality.check.${check.code}` as MessageKey)}
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}

function Provenance({ record }: { record: SlideRecord }) {
  const { t, date } = useI18n();
  return (
    <section aria-labelledby="provenance" className={styles.provenance}>
      <h2 id="provenance" className={styles.sectionTitle}>{t("slide.provenance")}</h2>
      <div className={styles.tableWrap}>
        <table data-testid="provenance">
          <thead>
            <tr>
              <th scope="col">{t("slide.prov.image")}</th>
              <th scope="col">{t("slide.prov.source")}</th>
              <th scope="col">{t("slide.prov.author")}</th>
              <th scope="col">{t("slide.prov.licence")}</th>
              <th scope="col">{t("slide.prov.retrieved")}</th>
              {record.assets.some(originalSha) ? <th scope="col">SHA-256</th> : null}
            </tr>
          </thead>
          <tbody>
            {record.assets.map((a) => (
              <tr key={a.id} data-asset={a.id}>
                <th scope="row" data-label={t("slide.prov.image")}>{t(`role.${a.role}` as MessageKey)}{a.plane ? ` ${a.plane.depth_um} µm` : ""}
                  {a.polarisation ? ` ${a.polarisation.state.toUpperCase()}` : ""}</th>
                <td data-label={t("slide.prov.source")}>
                  {a.source ? <a href={a.source.url}>{a.source.record_id}</a> : t("slide.prov.contributed")}
                </td>
                <td data-label={t("slide.prov.author")}>{a.creator ?? a.rights_holder ?? ""}</td>
                <td data-label={t("slide.prov.licence")}><a href={a.licence.uri}>{a.licence.short_name}</a></td>
                <td data-label={t("slide.prov.retrieved")}>
                  {a.source ? date(a.source.retrieved_on, { year: "numeric", month: "short", day: "numeric" }) : ""}
                </td>
                {record.assets.some(originalSha) ? (
                  <td data-label="SHA-256" className={styles.mono} title={originalSha(a) ?? undefined}
                    data-sha256={originalSha(a) ?? undefined}>{originalSha(a)?.slice(0, 12)}</td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
