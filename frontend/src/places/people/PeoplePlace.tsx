// /people/<handle>: an account's profile and its cabinet (U14, R-1401 to R-1403, R-1408). The profile says who the
// account is in the collection (its role, when it joined and was last active) and what it has done (published and
// verified slides, identifications of others' slides by category, annotations); never its email. Its slides lie in
// drawers, one per collection, as a drawer's tray lays them; its identifications list each slide with the anchor it
// gave and whether that is the community's anchor now. Anyone may select slides and print their labels on a stock;
// the account itself may export its own slides, with their exact places.
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { Link, useLocation, useParams, useSearch } from "wouter";
import { ApiError } from "../../api/client";
import { useResource } from "../../api/useResource";
import { useSession } from "../../account/session";
import type { PersonIdentificationRecord, ProfileRecord, SlideSummary } from "../../contract/catalog";
import { useI18n } from "../../i18n";
import { PrintDialog } from "../../labels/PrintDialog";
import { EXPORT_URL, PAGE, peopleApi } from "../../people/api";
import { Place } from "../../router/Place";
import { nameParts, trayReference } from "../../slide/names";
import { TraySlide } from "../../slide/TraySlide";
import { localised, nodeHref, useTree, type TreeIndex } from "../../tree/TreeProvider";
import { Button } from "../../ui/Button";
import { CollectionTag } from "../../ui/Chip";
import { Checkbox } from "../../ui/Choice";
import { EmptyState, Skeleton } from "../../ui/Feedback";
import { Glyph, Icon } from "../../ui/Icon";
import { Tabs } from "../../ui/Tabs";
import { NotFoundPlace } from "../NotFoundPlace";
import styles from "./People.module.css";

type Tab = "slides" | "identifications";

export function PeoplePlace() {
  const params = useParams<{ handle: string }>();
  const handle = (params.handle ?? "").toLowerCase();
  const { t } = useI18n();
  const tree = useTree();
  const profile = useResource<ProfileRecord>(`person:${handle}`, (signal) => peopleApi.profile(handle, signal));

  if (profile.state === "error" && profile.error instanceof ApiError && profile.error.status === 404) {
    return <NotFoundPlace />;
  }
  if (profile.state === "error") {
    return (
      <Place title={t("people.title")}>
        <p role="alert" className={styles.problem}>{t("people.failed")}</p>
      </Place>
    );
  }
  if (profile.state !== "ready" || profile.value.handle !== handle || tree.state !== "ready") {
    return <Place title={t("state.loading")} ready={false}><Skeleton lines={8} /></Place>;
  }
  return <Profile key={handle} profile={profile.value} tree={tree.tree} />;
}

function Profile({ profile, tree }: { profile: ProfileRecord; tree: TreeIndex }) {
  const { t, plural, date, lang } = useI18n();
  const byCollection = profile.by_collection ?? {};
  const categories = profile.categories ?? {};
  const session = useSession();
  const search = useSearch();
  const [, navigate] = useLocation();
  const tab: Tab = new URLSearchParams(search).get("tab") === "identifications" ? "identifications" : "slides";
  const own = session.account?.handle === profile.handle;
  const [selected, setSelected] = useState<string[]>([]);
  const [selecting, setSelecting] = useState(false);
  const [printing, setPrinting] = useState(false);
  const day = (value: string) => date(value, { year: "numeric", month: "long", day: "numeric" });

  const collections = useMemo(() => orderOf(tree, Object.keys(byCollection)), [tree, byCollection]);
  const toggle = (id: string, on: boolean) => setSelected((list) => on ? [...list.filter((s) => s !== id), id]
    : list.filter((s) => s !== id));
  const addAll = (ids: string[]) => setSelected((list) => [...list, ...ids.filter((id) => !list.includes(id))]);

  const stats: [string, number][] = [
    [t("people.stat.slides"), profile.slides],
    [t("people.stat.verified"), profile.verified],
    [t("people.stat.identifications"), profile.identifications],
    [t("people.stat.annotations"), profile.annotations],
  ];

  const slidesPanel = profile.slides === 0 ? (
    <EmptyState icon="cabinet" title={t("people.slides.none")}>{own ? t("people.slides.none.own")
      : t("people.slides.none.body")}</EmptyState>
  ) : (
    <>
      <div className={styles.toolbar}>
        {selecting ? (
          <>
            <p className={styles.count} role="status">{plural("people.selected", selected.length)}</p>
            <Button variant="primary" icon="print" disabled={!selected.length} onClick={() => setPrinting(true)}>
              {t("people.printLabels")}
            </Button>
            <Button disabled={!selected.length} onClick={() => setSelected([])}>{t("people.clear")}</Button>
            <Button variant="quiet" onClick={() => { setSelecting(false); setSelected([]); }}>
              {t("people.selectDone")}
            </Button>
          </>
        ) : (
          <Button icon="labels" onClick={() => setSelecting(true)}>{t("people.select")}</Button>
        )}
      </div>
      {collections.map((id) => (
        <Drawer key={id} handle={profile.handle} collection={id} count={byCollection[id]} tree={tree}
          selecting={selecting} selected={selected} onToggle={toggle} onAll={addAll} />
      ))}
    </>
  );

  return (
    <Place title={profile.name} heading={<Heading profile={profile} />} wide
      trail={[{ label: t("nav.collections"), href: "/" }, { label: profile.name }]}>
      <section className={styles.who} aria-label={t("people.about")}>
        <p className={styles.facts}>
          <span className={styles.role}>{t(`account.role.${profile.role}`)}</span>
          <span>{t("people.joined", { when: day(profile.joined) })}</span>
          {profile.last_active ? <span>{t("people.active", { when: day(profile.last_active) })}</span> : null}
        </p>
        <dl className={styles.stats}>
          {stats.map(([label, value]) => (
            <div key={label} className={styles.stat}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        {profile.identifications ? (
          <p className={styles.categories}>
            <span className={styles.categoriesTitle}>{t("people.categories")}</span>
            {(["leading", "improving", "supporting", "maverick"] as const).map((k) => (
              <span key={k} className={styles.category} data-category={k}>
                {t(`community.category.${k}`)} <b>{categories[k] ?? 0}</b>
              </span>
            ))}
          </p>
        ) : null}
        {collections.length ? (
          <ul className={styles.collections} aria-label={t("people.byCollection")}>
            {collections.map((id) => {
              const node = tree.byId.get(id);
              return (
                <li key={id}>
                  <a href={`#drawer-${id.replace(".", "-")}`} className={styles.collectionLink}
                    onClick={() => { if (tab !== "slides") navigate(`/people/${profile.handle}`, { replace: true }); }}>
                    <CollectionTag collection={id} name={node ? localised(node.name, lang) : id} />
                    <span className={styles.collectionCount}>{byCollection[id]}</span>
                  </a>
                </li>
              );
            })}
          </ul>
        ) : null}
        {own ? (
          <p className={styles.export}>
            <a href={EXPORT_URL} download className={styles.exportLink}>
              <Glyph name="download" size={20} />
              <span>{t("people.export")}</span>
            </a>
            <span className={styles.hint}>{t("people.export.hint")}</span>
          </p>
        ) : null}
      </section>

      <Tabs<Tab> label={t("people.tabs")} selected={tab}
        onSelect={(k) => navigate(k === "slides" ? `/people/${profile.handle}` : `/people/${profile.handle}?tab=${k}`,
          { replace: true })}
        items={[
          { key: "slides", label: `${t("people.tab.slides")} (${profile.slides})`, panel: slidesPanel },
          { key: "identifications", label: `${t("people.tab.identifications")} (${profile.identifications})`,
            panel: tab === "identifications" ? <Identifications handle={profile.handle} total={profile.identifications}
              tree={tree} /> : null },
        ]} />
      <PrintDialog open={printing} onClose={() => setPrinting(false)} slides={selected} />
    </Place>
  );
}

function Heading({ profile }: { profile: ProfileRecord }) {
  return (
    <span className={styles.heading}>
      <Glyph name="account" size={32} className={styles.headingIcon} />
      <span className={styles.headingText}>
        <span>{profile.name}</span>
        <span className={styles.handle}>@{profile.handle}</span>
      </span>
    </span>
  );
}

/** The collections in the tree's order (realm by realm), whatever order the counts came in. */
function orderOf(tree: TreeIndex, ids: string[]): string[] {
  const order = tree.realms.flatMap((r) => (r.children ?? []).map((c) => c.id));
  return [...ids].sort((a, b) => {
    const ia = order.indexOf(a);
    const ib = order.indexOf(b);
    return (ia < 0 ? 999 : ia) - (ib < 0 ? 999 : ib) || a.localeCompare(b);
  });
}

interface DrawerProps {
  handle: string;
  collection: string;
  count: number;
  tree: TreeIndex;
  selecting: boolean;
  selected: string[];
  onToggle: (id: string, on: boolean) => void;
  onAll: (ids: string[]) => void;
}

/** One collection's drawer of the account's slides: its tray, a page at a time. */
function Drawer({ handle, collection, count, tree, selecting, selected, onToggle, onAll }: DrawerProps) {
  const { t, plural, lang } = useI18n();
  const [items, setItems] = useState<SlideSummary[] | null>(null);
  const [total, setTotal] = useState(count);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const node = tree.byId.get(collection);
  const anchor = `drawer-${collection.replace(".", "-")}`;

  useEffect(() => {
    const controller = new AbortController();
    peopleApi.slides(handle, collection, 0, controller.signal).then((page) => {
      setItems(page.items);
      setTotal(page.total);
    }, () => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, [handle, collection]);

  const more = async () => {
    if (!items) return;
    setBusy(true);
    try {
      const page = await peopleApi.slides(handle, collection, items.length);
      setItems([...items, ...page.items]);
      setTotal(page.total);
    } finally {
      setBusy(false);
    }
  };

  const hue = { "--tag-hue": `var(--h-${collection.split(".")[1]})` } as CSSProperties;
  return (
    <section className={styles.drawer} aria-labelledby={`${anchor}-title`} id={anchor} style={hue}>
      <div className={styles.drawerHead}>
        <h2 id={`${anchor}-title`} className={styles.drawerTitle}>
          <Icon name={node?.icon || collection} size={32} className={styles.drawerIcon} />
          {node ? <Link href={nodeHref(collection)}>{localised(node.name, lang)}</Link> : collection}
        </h2>
        <span className={styles.drawerCount}>{plural("count.slides", total)}</span>
        {selecting && items?.length ? (
          <Button size="small" onClick={() => onAll(items.map((s) => s.id))}>{t("people.selectDrawer")}</Button>
        ) : null}
      </div>
      {failed ? <p role="alert" className={styles.problem}>{t("people.failed")}</p> : null}
      {!items && !failed ? <Skeleton lines={3} /> : null}
      {items?.length ? (
        <ul className={styles.tray} style={{ "--ref": trayReference(items.map((s) => s.format)) } as CSSProperties}>
          {items.map((slide) => (
            <li key={slide.id} data-selected={selected.includes(slide.id) || undefined}>
              <TraySlide slide={slide} tree={tree} />
              {selecting ? (
                <Checkbox className={styles.pick} checked={selected.includes(slide.id)} data-pick={slide.id}
                  onChange={(e) => onToggle(slide.id, e.target.checked)}
                  label={<>{t("people.pick")}<span className="visually-hidden"> {slide.label?.catalogue_number
                    || slide.id}</span></>} />
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
      {items && items.length < total ? (
        <div className={styles.more}>
          <Button busy={busy} onClick={() => void more()}>{t("identify.more", {
            count: Math.min(PAGE, total - items.length) })}</Button>
        </div>
      ) : null}
    </section>
  );
}

/** The account's current identifications of others' slides, newest first. */
function Identifications({ handle, total, tree }: { handle: string; total: number; tree: TreeIndex }) {
  const { t, date } = useI18n();
  const [items, setItems] = useState<PersonIdentificationRecord[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    peopleApi.identifications(handle, 0, controller.signal).then(setItems,
      () => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, [handle]);

  const more = async () => {
    if (!items) return;
    setBusy(true);
    try {
      setItems([...items, ...await peopleApi.identifications(handle, items.length)]);
    } finally {
      setBusy(false);
    }
  };

  if (failed) return <p role="alert" className={styles.problem}>{t("people.failed")}</p>;
  if (!items) return <Skeleton lines={4} />;
  if (!items.length) {
    return <EmptyState icon="identify" title={t("people.idents.none")}>{t("people.idents.none.body")}</EmptyState>;
  }
  return (
    <>
      <ul className={styles.tray} style={{ "--ref": trayReference(items.map((i) => i.slide.format)) } as CSSProperties}>
        {items.map((i) => (
          <li key={i.id} className={styles.ident} data-identification={i.id}>
            <TraySlide slide={i.slide} tree={tree} />
            <dl className={styles.identFacts}>
              <div>
                <dt>{t("people.idents.gave")}</dt>
                <dd>
                  {nameParts(i.anchor).map((part, n) => (
                    <span key={n}>{n ? " " : ""}{part.italic ? <i className="binomial">{part.text}</i> : part.text}</span>
                  ))}
                </dd>
              </div>
              {i.category ? (
                <div>
                  <dt>{t("people.idents.category")}</dt>
                  <dd><span className={styles.category} data-category={i.category}>
                    {t(`community.category.${i.category}`)}</span></dd>
                </div>
              ) : null}
              <div>
                <dt>{t("people.idents.community")}</dt>
                <dd data-community={i.community}>
                  {i.community ? <><Glyph name="check" size={16} /> {t("people.idents.agrees")}</>
                    : t("people.idents.differs")}
                </dd>
              </div>
              <div>
                <dt>{t("people.idents.when")}</dt>
                <dd>{date(i.created_at, { year: "numeric", month: "short", day: "numeric" })}</dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
      {items.length < total ? (
        <div className={styles.more}>
          <Button busy={busy} onClick={() => void more()}>{t("identify.more", {
            count: Math.min(PAGE, total - items.length) })}</Button>
        </div>
      ) : null}
    </>
  );
}
