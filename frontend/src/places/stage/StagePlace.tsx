// /s/<id>/stage/<asset>: a slide's image under the microscope. The viewer is loaded only here (OpenSeadragon and
// Annotorious, a separate chunk); beside it, the slide's other images, each a step away.
import { lazy, Suspense } from "react";
import { Link, useParams } from "wouter";
import { api } from "../../api/client";
import { useResource } from "../../api/useResource";
import { useI18n } from "../../i18n";
import { Place } from "../../router/Place";
import { itemFor, stageItems, thumbnail } from "../../slide/assets";
import { localised, nodeHref, pathTo, useTree } from "../../tree/TreeProvider";
import { Skeleton } from "../../ui/Feedback";
import { NotFoundPlace } from "../NotFoundPlace";
import { SlideName } from "../slide/SlidePlace";
import styles from "./StagePlace.module.css";

const StageViewer = lazy(() => import("../../stage/StageViewer").then((m) => ({ default: m.StageViewer })));

export function StagePlace() {
  const { id, asset } = useParams<{ id: string; asset: string }>();
  const { t, lang, plural } = useI18n();
  const tree = useTree();
  const slide = useResource(`slide:${id.toUpperCase()}`, (signal) => api.slide(id, signal));
  const me = useResource("me", (signal) => api.me(signal));
  if (slide.state === "error") return <NotFoundPlace />;
  if (!slide.value || tree.state !== "ready") return <Place title={t("state.loading")} ready={false}><Skeleton lines={6} /></Place>;
  const record = slide.value;
  const items = stageItems(record.assets);
  const item = itemFor(items, Number(asset));
  if (!item) return <NotFoundPlace />;
  const trail = [{ label: t("nav.collections"), href: "/" }, ...pathTo(tree.tree, record.placement.node).map((n) => ({
    label: localised(n.name, lang), href: nodeHref(n.id), icon: n.id })),
  { label: record.id, href: `/s/${record.id}` }, { label: t("stage.title") }];
  const what = item.kind === "stack" ? t("slide.item.stack", { planes: plural("count.planes", item.planes.length) })
    : item.kind === "pair" ? t("slide.item.pair") : t("slide.item.single");

  return (
    <Place title={`${t("stage.title")}: ${record.label.name}`} trail={trail} wide
      heading={<span><SlideName record={record} /> <span className={styles.what}>· {what}</span></span>}>
      <div className={styles.body}>
        <Suspense fallback={<div className={styles.loading}><Skeleton lines={3} /></div>}>
          <StageViewer key={item.key} slideId={record.id} item={item} signedIn={Boolean(me.value)} />
        </Suspense>
        {items.length > 1 ? (
          <nav aria-label={t("stage.others")} className={styles.others}>
            <h2>{t("stage.others")}</h2>
            <ul>
              {items.map((other) => {
                const src = thumbnail(other.first, 240);
                return (
                  <li key={other.key}>
                    <Link href={`/s/${record.id}/stage/${other.first.id}`} aria-current={other === item ? "page" : undefined}>
                      {src ? <img src={src} alt="" loading="lazy" /> : <span className={styles.blank} />}
                      <span>{other.kind === "stack" ? t("slide.item.stack", { planes: plural("count.planes", other.planes.length) })
                        : other.kind === "pair" ? t("slide.item.pair") : t("slide.item.single")}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        ) : null}
        <p><Link href={`/s/${record.id}`}>{t("stage.back")}</Link></p>
      </div>
    </Place>
  );
}
