// /search: the whole collection, or one cabinet or drawer (?node=), searched by words and narrowed by facets. With
// no words and no filters it lists every slide, newest first.
import { useState } from "react";
import { Explorer } from "../../explore/Explorer";
import { useI18n } from "../../i18n";
import { Place } from "../../router/Place";
import { useTree } from "../../tree/TreeProvider";
import { TreeGate } from "../TreeGate";
import styles from "./SearchPlace.module.css";

export function SearchPlace() {
  const { t } = useI18n();
  const tree = useTree();
  const [ready, setReady] = useState(false);
  return (
    <Place title={t("search.title")} ready={ready} trail={[{ label: t("nav.collections"), href: "/" },
      { label: t("search.title") }]}>
      <p className={styles.intro}>{t("search.intro")}</p>
      <TreeGate tree={tree}>
        {(index) => (
          <Explorer tree={index} collections searchLabel={t("search.field")} onReady={setReady}
            emptyTitle={t("explore.empty.title")} emptyBody={t("explore.empty.body")} />
        )}
      </TreeGate>
    </Place>
  );
}
