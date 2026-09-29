// /about: what Laminario is, the collection counted now, where its images come from and under which licences, how to
// cite and credit them, how an image becomes a stage, identification, what is never shown, the names behind the tree,
// and the software, fonts and map data it stands on (U15, R-1501 to R-1507). The prose is content.en.ts or
// content.es.ts; every count comes from GET /api/about.
import { useEffect, useState, type ReactNode } from "react";
import { aboutApi } from "../../about/api";
import { aboutEn } from "../../about/content.en";
import { aboutEs } from "../../about/content.es";
import type { AboutContent, LicenceFamily, LiveId, SourceId } from "../../about/model";
import { BlockView, Inlines } from "../../about/Rich";
import styles from "../../about/About.module.css";
import type { AboutRecord, CreditRecord } from "../../contract/catalog";
import { useI18n } from "../../i18n";
import { Place } from "../../router/Place";
import { localised, useTree } from "../../tree/TreeProvider";
import { CollectionTag } from "../../ui/Chip";
import { Skeleton } from "../../ui/Feedback";

/** A licence's short name: a Creative Commons URI as "CC BY-SA 3.0", ODbL, or the SPDX identifier as written. */
export function licenceName(licence: string | null | undefined, none: string): string {
  if (!licence) return none;
  const cc = /creativecommons\.org\/licenses\/([a-z-]+)\/(\d\.\d)(?:\/([a-z]{2}))?/.exec(licence);
  if (cc) return `CC ${cc[1].toUpperCase()} ${cc[2]}${cc[3] ? ` ${cc[3].toUpperCase()}` : ""}`;
  if (licence.includes("publicdomain/zero")) return "CC0 1.0";
  if (licence.includes("publicdomain/mark")) return "Public Domain Mark 1.0";
  if (licence.includes("opendatacommons.org/licenses/odbl")) return "ODbL 1.0";
  return licence;
}

export function AboutPlace() {
  const { t, lang, date, number } = useI18n();
  const content: AboutContent = lang === "es" ? aboutEs : aboutEn;
  const tree = useTree();
  const [about, setAbout] = useState<AboutRecord | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    aboutApi.read(controller.signal).then(setAbout, () => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, []);

  // Opened at a section (#licences, #cite), go there once the content that moves it has arrived.
  useEffect(() => {
    if (!about || !window.location.hash) return;
    document.getElementById(window.location.hash.slice(1))?.scrollIntoView();
  }, [about]);

  const w = content.live;
  const nodeName = (id: string) => {
    const node = tree.state === "ready" ? tree.tree.byId.get(id) : undefined;
    return node ? localised(node.name, lang) : id;
  };

  const credits = (items: CreditRecord[], caption: string | null, withCitation = false) => (
    <div className={styles.creditGroup}>
      {caption ? <h3 className={styles.h3}>{caption}</h3> : null}
      <ul className={styles.credits}>
        {items.map((item) => (
          <li key={item.id} data-credit={item.id}>
            <a href={item.url} rel="noreferrer" className={styles.creditName}>{item.name}</a>
            <span className={styles.creditLicence}>{licenceName(item.licence, w.none)}</span>
            {withCitation && item.citation ? (
              <span className={styles.citation}>
                {item.citation}{item.doi ? <> <a href={`https://doi.org/${item.doi}`} rel="noreferrer">
                  doi:{item.doi}</a></> : null}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );

  const live = (what: LiveId): ReactNode => {
    if (failed) return <p role="alert" className={styles.problem}>{w.failed}</p>;
    if (!about) return <Skeleton lines={4} />;
    const n = about.numbers;
    switch (what) {
      case "numbers": return (
        <div className={styles.numbers} data-live="numbers">
          <dl className={styles.stats}>
            {([[w.slides, n.slides], [w.base, n.by_origin?.base ?? 0], [w.contribution, n.by_origin?.contribution ?? 0],
              [w.wsi, n.wsi], [w.images, n.images], [w.countries, n.countries], [w.contributors, n.contributors],
              [w.identifications, n.identifications]] as [string, number][]).map(([label, value]) => (
              <div key={label} className={styles.stat}><dt>{label}</dt><dd>{number(value)}</dd></div>
            ))}
          </dl>
          <ul className={styles.realms}>
            {(n.realms ?? []).map((realm) => (
              <li key={realm.id}>
                <span className={styles.realmName}>{nodeName(realm.id)}</span>
                <span className={styles.realmCount}>{number(realm.slides)}</span>
                <span className={styles.realmCollections}>
                  {Object.entries(realm.collections ?? {}).map(([id, count]) => (
                    <span key={id} className={styles.realmCollection}>
                      <CollectionTag collection={id} name={nodeName(id)} /> <b>{number(count)}</b>
                    </span>
                  ))}
                </span>
              </li>
            ))}
          </ul>
          <p className={styles.readAt}>{w.read} {date(about.read_at, { dateStyle: "long", timeStyle: "short" })}</p>
        </div>
      );
      case "sources": return (
        <ul className={styles.cards} data-live="sources">
          {(about.sources ?? []).map((s) => (
            <li key={s.id} className={styles.card} data-source={s.id}>
              <h3 className={styles.cardTitle}>
                {s.url ? <a href={s.url} rel="noreferrer">{s.name}</a>
                  : s.name ?? (s.id === "contribution" ? w.contributions : w.others)}
              </h3>
              <p className={styles.cardNumbers}>
                <span>{w.slides_col}: <b>{number(s.slides)}</b></span>
                <span>{w.images_col}: <b>{number(s.images)}</b></span>
                {s.terms ? <a href={s.terms} rel="noreferrer">{w.terms}</a> : null}
              </p>
              <p><Inlines parts={content.sources[s.id as SourceId] ?? content.sources.other} /></p>
              <ul className={styles.licenceChips} aria-label={w.licences_col}>
                {Object.entries(s.licences ?? {}).map(([uri, count]) => (
                  <li key={uri}><a href={uri} rel="noreferrer">{licenceName(uri, w.none)}</a> <b>{number(count)}</b></li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      );
      case "licences": return (
        <ul className={styles.cards} data-live="licences">
          {(about.licences ?? []).map((l) => {
            const words = content.licences[l.family as LicenceFamily];
            return (
              <li key={l.uri} className={styles.card} data-licence={l.uri}>
                <h3 className={styles.cardTitle}><a href={l.uri} rel="noreferrer">{l.short}</a></h3>
                <p className={styles.cardNumbers}><span>{w.images_col}: <b>{number(l.images)}</b></span>
                  {words ? <span>{words.name}</span> : null}</p>
                {words ? <p><Inlines parts={words.text} /></p> : null}
              </li>
            );
          })}
        </ul>
      );
      case "vocabularies": return credits(about.vocabularies ?? [], null, true);
      case "software": return credits(about.software ?? [], w.software);
      case "fonts": return credits(about.fonts ?? [], w.fonts);
      case "map": return credits(about.map ?? [], w.map);
    }
  };

  return (
    <Place title={content.title} ready={about !== null || failed} wide
      trail={[{ label: t("nav.collections"), href: "/" }, { label: content.title }]}>
      <p className={styles.lead}>{content.lead}</p>
      <div className={styles.layout}>
        <nav className={styles.toc} aria-label={content.contents}>
          <h2 className={styles.tocTitle}>{content.contents}</h2>
          <ol>
            {content.sections.map((s) => <li key={s.id}><a href={`#${s.id}`}>{s.title}</a></li>)}
          </ol>
        </nav>
        <div className={styles.article}>
          {content.sections.map((section) => (
            <section key={section.id} id={section.id} aria-labelledby={`${section.id}-title`}
              className={styles.section}>
              <h2 id={`${section.id}-title`} className={styles.h2}>{section.title}</h2>
              {section.blocks.map((block, i) => <BlockView key={i} block={block} content={content} live={live} />)}
            </section>
          ))}
        </div>
      </div>
    </Place>
  );
}
