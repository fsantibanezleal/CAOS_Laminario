// /contribute: the contributor's slide cases (R-1206), newest first: drafts to finish, cases being processed, and
// the published slides they became. A draft is reopened, or deleted after a confirmation; a case sent back by a
// failed image says why. A visitor is sent to sign in first; an account that may not contribute is told so.
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "wouter";
import { signInHref } from "../../account/api";
import { useSession } from "../../account/session";
import { contributeApi } from "../../contribute/api";
import { loadUnsent } from "../../contribute/draft";
import type { CaseSummary } from "../../contract/catalog";
import { useI18n } from "../../i18n";
import { Place } from "../../router/Place";
import { Button } from "../../ui/Button";
import { EmptyState, Skeleton } from "../../ui/Feedback";
import { Glyph } from "../../ui/Icon";
import styles from "./Contribute.module.css";

export function ContributeList() {
  const { t, date, plural } = useI18n();
  const session = useSession();
  const [location, navigate] = useLocation();
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [confirming, setConfirming] = useState<CaseSummary | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const unsent = loadUnsent();

  useEffect(() => {
    if (session.state === "ready" && !session.account) navigate(signInHref(location), { replace: true });
  }, [session.state, session.account, location, navigate]);

  useEffect(() => {
    if (!session.can("submit")) return undefined;
    const controller = new AbortController();
    contributeApi.list(controller.signal).then(setCases, () => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, [session]);

  useEffect(() => {
    if (confirming) dialog.current?.showModal();
    else dialog.current?.close();
  }, [confirming]);

  if (session.state !== "ready" || !session.account) {
    return <Place title={t("contribute.mine")} ready={false}><Skeleton lines={4} /></Place>;
  }
  if (!session.can("submit")) {
    return (
      <Place title={t("contribute.mine")}>
        <EmptyState icon="life" title={t("contribute.notAllowed.title")}>{t("contribute.notAllowed.body")}</EmptyState>
      </Place>
    );
  }

  const remove = async (item: CaseSummary) => {
    await contributeApi.remove(item.id);
    setConfirming(null);
    setCases((list) => list?.filter((c) => c.id !== item.id) ?? null);
  };

  return (
    <Place title={t("contribute.mine")} ready={cases !== null}>
      <div className={styles.listHead}>
        <p className={styles.lead}>{t("contribute.list.lead")}</p>
        <Link href="/contribute/new" className={styles.primaryLink}>
          <Glyph name="plus" size={20} />
          <span>{unsent ? t("contribute.list.continueUnsent") : t("contribute.list.new")}</span>
        </Link>
      </div>
      {failed ? <p role="alert" className={styles.problem}>{t("contribute.list.failed")}</p> : null}
      {cases === null && !failed ? <Skeleton lines={5} /> : null}
      {cases && cases.length === 0 ? (
        <EmptyState icon="life" title={t("contribute.list.empty.title")}>{t("contribute.list.empty.body")}</EmptyState>
      ) : null}
      {cases && cases.length > 0 ? (
        <ul className={styles.cases}>
          {cases.map((item) => {
            const images = item.images ?? [];
            const withFile = images.filter((i) => i.has_file).length;
            const failedImages = images.filter((i) => i.status === "failed").length;
            return (
              <li key={item.id} className={styles.caseRow} data-status={item.status}>
                <span className={styles.statusMark} aria-hidden="true">
                  <Glyph name={item.status === "draft" ? "draft" : item.status === "processing" ? "clock" : "check"}
                    size={24} />
                </span>
                <div className={styles.caseText}>
                  <p className={styles.caseName}>
                    {item.status === "published"
                      ? <Link href={`/s/${item.id}`}>{item.name}</Link>
                      : <Link href={`/contribute/${item.id}`}>{item.name}</Link>}
                    <span className={styles.caseId}>{item.id}</span>
                  </p>
                  <p className={styles.caseMeta}>
                    <span className={styles.badge} data-status={item.status}>{t(`contribute.status.${item.status}`)}</span>
                    <span>{plural("count.images", images.length)}</span>
                    {item.status === "draft" ? <span>{t("contribute.list.files", { done: withFile, all: images.length })}</span>
                      : null}
                    <span>{t("contribute.list.updated", { when: date(item.updated_at, { dateStyle: "medium",
                      timeStyle: "short" }) })}</span>
                  </p>
                  {item.status_reason ? <p className={styles.reason}><Glyph name="warning" size={16} />
                    <span>{item.status_reason}</span></p> : null}
                  {failedImages ? <p className={styles.reason}>{plural("contribute.list.failedImages", failedImages)}</p>
                    : null}
                </div>
                <div className={styles.caseActions}>
                  {item.status === "draft" ? (
                    <>
                      <Link href={`/contribute/${item.id}`} className={styles.quietLink}>
                        <Glyph name="edit" size={20} /><span>{t("contribute.list.open")}</span>
                      </Link>
                      <Button variant="quiet" icon="delete" onClick={() => setConfirming(item)}>
                        {t("contribute.list.delete")}
                      </Button>
                    </>
                  ) : item.status === "processing" ? (
                    <Link href={`/contribute/${item.id}`} className={styles.quietLink}>
                      <Glyph name="clock" size={20} /><span>{t("contribute.list.progress")}</span>
                    </Link>
                  ) : (
                    <Link href={`/s/${item.id}`} className={styles.quietLink}>
                      <Glyph name="slide" size={20} /><span>{t("contribute.list.view")}</span>
                    </Link>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      ) : null}
      <dialog ref={dialog} className={styles.dialog} onClose={() => setConfirming(null)}
        aria-labelledby="delete-title">
        {confirming ? (
          <form method="dialog" className={styles.dialogBody}>
            <h2 id="delete-title">{t("contribute.delete.title", { name: confirming.name })}</h2>
            <p>{t("contribute.delete.body")}</p>
            <div className={styles.dialogActions}>
              <Button type="submit" variant="secondary">{t("action.cancel")}</Button>
              <Button variant="danger" icon="delete" onClick={() => void remove(confirming)}>
                {t("contribute.delete.confirm")}
              </Button>
            </div>
          </form>
        ) : null}
      </dialog>
    </Place>
  );
}
