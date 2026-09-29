// /contribute/new and /contribute/<id>: a slide case, filled in section by section (what it shows, the slide, the
// images, the place, the drawer, then review and send), with the slide drawn beside the form as it is described.
// The server's validation (POST /api/slide-cases/validate) runs as the contributor goes; its messages, in the page's
// language (R-1202), appear by a section once the contributor has been through it, and all of them on saving. An
// unsent case is kept on this device; a stored one is the server's draft, reopened here (R-1206).
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useParams } from "wouter";
import { signInHref } from "../../account/api";
import { useSession } from "../../account/session";
import { ApiError } from "../../api/client";
import { contributeApi, isValidation } from "../../contribute/api";
import { byField, emptyCase, forgetUnsent, fromSubmission, imageOf, loadUnsent, saveUnsent, sectionOf, toSubmission,
  type CaseDraft } from "../../contribute/draft";
import { worded } from "../../contribute/messages";
import type { CaseRecord, ValidationError, ValidationFlag } from "../../contract/catalog";
import type { SlideCaseSubmission } from "../../contract/ingest";
import { useI18n } from "../../i18n";
import { Place } from "../../router/Place";
import { Button } from "../../ui/Button";
import { EmptyState, Skeleton } from "../../ui/Feedback";
import { Glyph } from "../../ui/Icon";
import styles from "./Contribute.module.css";
import { ImagesSection } from "./ImagesSection";
import { PlaceSection } from "./PlaceSection";
import { PlacementSection } from "./PlacementSection";
import { STEPS, type ErrorOptions, type Step } from "./sections";
import { SendSection } from "./SendSection";
import { SlidePreview } from "./SlidePreview";
import { SlideSection } from "./SlideSection";
import { SpecimenSection } from "./SpecimenSection";
import { useCaseFiles } from "./useCaseFiles";

const STEP_GLYPH: Record<Step, string> = { specimen: "search", slide: "slide", images: "camera", place: "pin",
  placement: "cabinet", send: "upload" };

export function CaseEditor() {
  const params = useParams<{ id?: string }>();
  const id = params.id && params.id !== "new" ? params.id : null;
  const { t } = useI18n();
  const session = useSession();
  const [location, navigate] = useLocation();
  const [draft, setDraft] = useState<CaseDraft | null>(null);
  const [record, setRecord] = useState<CaseRecord | null>(null);
  const [savedJson, setSavedJson] = useState<string | null>(null);
  const [missing, setMissing] = useState(false);
  const [step, setStep] = useState<Step>("specimen");
  const [visited, setVisited] = useState<Set<Step>>(new Set());
  const [showAll, setShowAll] = useState(false);
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [flags, setFlags] = useState<ValidationFlag[]>([]);
  const [checking, setChecking] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveProblem, setSaveProblem] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const top = useRef<HTMLDivElement>(null);

  // Signed in, and allowed to contribute; else to sign in first.
  useEffect(() => {
    if (session.state === "ready" && !session.account) navigate(signInHref(location), { replace: true });
  }, [session.state, session.account, location, navigate]);

  // The case: the stored draft, or the one kept on this device, or a new one.
  useEffect(() => {
    if (!session.can("submit")) return undefined;
    if (!id) {
      const kept = loadUnsent();
      const fresh = kept ?? emptyCase();
      setDraft(fresh);
      setRecord(null);
      setSavedJson(null);
      return undefined;
    }
    const controller = new AbortController();
    contributeApi.get(id, controller.signal).then((r) => {
      setRecord(r);
      const opened = fromSubmission(r.submission as unknown as SlideCaseSubmission);
      setDraft(opened);
      setSavedJson(JSON.stringify(toSubmission(opened)));
      setShowAll(true);
      if (r.status !== "draft" || new URLSearchParams(window.location.search).get("step") === "send") setStep("send");
    }, (e: unknown) => {
      if (!controller.signal.aborted && e instanceof ApiError && e.status === 404) setMissing(true);
    });
    return () => controller.abort();
    // The account is read once it is known; the id names the case.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, session.state]);

  const refresh = useCallback(async () => {
    if (!record) return;
    try {
      setRecord(await contributeApi.get(record.id));
    } catch {
      // the next read will try again
    }
  }, [record]);

  const update = useCallback((change: (d: CaseDraft) => CaseDraft) => setDraft((d) => (d ? change(d) : d)), []);
  const submission = useMemo(() => (draft ? toSubmission(draft) : null), [draft]);
  const json = useMemo(() => (submission ? JSON.stringify(submission) : ""), [submission]);
  const dirty = record ? json !== savedJson : true;
  const editable = !record || record.status === "draft";

  // Kept on this device while unsent.
  useEffect(() => {
    if (draft && !record && !id) saveUnsent(draft);
  }, [draft, record, id]);

  // The server's validation as the contributor goes, 600 ms after the last change.
  useEffect(() => {
    if (!submission) return undefined;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setChecking(true);
      contributeApi.validate(submission, controller.signal).then((result) => {
        setErrors(result.errors ?? []);
        setFlags(result.flags ?? []);
      }, () => undefined).finally(() => { if (!controller.signal.aborted) setChecking(false); });
    }, 600);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [json]); // eslint-disable-line react-hooks/exhaustive-deps

  const files = useCaseFiles(record, draft?.specimen.geoprivacy ?? "open", refresh);

  const shown = useCallback((path: string) => showAll || visited.has(sectionOf(path)), [showAll, visited]);
  const errorsByField = useMemo(() => byField(errors), [errors]);
  const flagsByField = useMemo(() => byField(flags), [flags]);
  const lookup = useCallback(<T extends ValidationError | ValidationFlag>(map: Map<string, T[]>, path: string,
    options?: ErrorOptions) => {
    const found: T[] = [];
    for (const [field, list] of map) {
      if (field === path || (options?.prefix && field.startsWith(`${path}.`))) found.push(...list);
    }
    return found.length ? found.map((item) => worded(t, item)).join(" ") : undefined;
  }, [t]);
  const errorFor = useCallback((path: string, options?: ErrorOptions) =>
    (shown(path) ? lookup(errorsByField, path, options) : undefined), [shown, lookup, errorsByField]);
  const flagFor = useCallback((path: string, options?: ErrorOptions) => lookup(flagsByField, path, options),
    [lookup, flagsByField]);

  const countFor = (s: Step) => errors.filter((e) => sectionOf(e.field) === s).length;

  const go = (next: Step, field?: string) => {
    setVisited((v) => new Set(v).add(step));
    setStep(next);
    requestAnimationFrame(() => {
      top.current?.scrollIntoView({ block: "start" });
      const index = field ? imageOf(field) : null;
      const target = index !== null ? document.querySelectorAll("[data-family]")[index] : null;
      (target as HTMLElement | null)?.scrollIntoView({ block: "center" });
      top.current?.querySelector<HTMLElement>("h2")?.focus();
    });
  };

  const save = async () => {
    if (!submission) return;
    setShowAll(true);
    setVisited(new Set(STEPS));
    setSaving(true);
    setSaveProblem(null);
    try {
      const answer = record ? await contributeApi.change(record.id, submission) : await contributeApi.create(submission);
      if (isValidation(answer)) {
        setErrors(answer.errors ?? []);
        setSaveProblem(t("send.notSaved"));
        return;
      }
      const storedId = (answer as { id: string }).id;
      const stored = await contributeApi.get(storedId);
      setRecord(stored);
      setSavedJson(json);
      if (!record) {
        forgetUnsent();
        navigate(`/contribute/${storedId}?step=send`, { replace: true });
      }
    } catch (e) {
      setSaveProblem(e instanceof ApiError && e.reason ? e.reason : t("account.error.server"));
    } finally {
      setSaving(false);
    }
  };

  const submit = async () => {
    if (!record) return;
    setSubmitting(true);
    try {
      setRecord(await contributeApi.submit(record.id));
    } catch (e) {
      setSaveProblem(e instanceof ApiError && e.reason ? e.reason : t("account.error.server"));
    } finally {
      setSubmitting(false);
    }
  };

  if (missing) {
    return (
      <Place title={t("contribute.case")}>
        <EmptyState icon="life" title={t("contribute.missing.title")}>{t("contribute.missing.body")}</EmptyState>
      </Place>
    );
  }
  if (session.state !== "ready" || !session.account || !draft) {
    return <Place title={t("contribute.case")} ready={false}><Skeleton lines={8} /></Place>;
  }
  if (!session.can("submit")) {
    return (
      <Place title={t("contribute.case")}>
        <EmptyState icon="life" title={t("contribute.notAllowed.title")}>{t("contribute.notAllowed.body")}</EmptyState>
      </Place>
    );
  }

  const title = draft.specimen.anchor?.name ?? t("contribute.newCase");
  const at = STEPS.indexOf(step);
  const props = { draft, update: editable ? update : () => undefined, errorFor, flagFor };
  const trail = [{ label: t("contribute.mine"), href: "/contribute" }, { label: record?.id ?? t("contribute.newCase") }];

  return (
    <Place title={`${t("contribute.case")}: ${title}`} trail={trail} wide
      heading={<span className={styles.editorHeading}>
        {draft.specimen.anchor?.kind === "taxon" ? <i>{title}</i> : title}
        {record ? <span className={styles.badge} data-status={record.status}>{t(`contribute.status.${record.status}`)}</span>
          : <span className={styles.badge}>{t("contribute.status.unsent")}</span>}
      </span>}>
      <div className={styles.editor}>
        <aside className={styles.side}>
          <SlidePreview draft={draft} />
          <nav aria-label={t("contribute.sections")} className={styles.rail}>
            <ol>
              {STEPS.map((s, i) => {
                const count = countFor(s);
                const seen = showAll || visited.has(s);
                return (
                  <li key={s}>
                    <button type="button" className={styles.railStep} aria-current={s === step ? "step" : undefined}
                      onClick={() => go(s)} data-state={s !== "send" && seen ? (count ? "errors" : "done") : undefined}>
                      <span className={styles.railNumber}>{i + 1}</span>
                      <Glyph name={STEP_GLYPH[s]} size={20} />
                      <span className={styles.railName}>{t(`step.${s}`)}</span>
                      {s !== "send" && seen && count ? (
                        <span className={styles.railCount}>{t("contribute.problems", { count })}</span>
                      ) : null}
                      {s !== "send" && seen && !count ? <Glyph name="check" size={16} className={styles.railOk} /> : null}
                    </button>
                  </li>
                );
              })}
            </ol>
          </nav>
          {!record ? <p className={styles.fieldHint}>{t("contribute.keptHere")}</p> : null}
        </aside>

        <section className={styles.sheet} aria-labelledby="step-title" ref={top as never}>
          <h2 id="step-title" tabIndex={-1} className={styles.stepTitle}>
            <span className={styles.stepNumber}>{at + 1}</span>{t(`step.${step}`)}
          </h2>
          <p className={styles.stepLead}>{t(`step.${step}.lead`)}</p>
          {!editable && step !== "send" ? (
            <p className={styles.notice}><Glyph name="info" size={20} /><span>{t("contribute.readOnly")}</span></p>
          ) : null}
          <fieldset disabled={!editable && step !== "send"} className={styles.unstyled}>
            {step === "specimen" ? <SpecimenSection {...props} /> : null}
            {step === "slide" ? <SlideSection {...props} /> : null}
            {step === "images" ? <ImagesSection {...props}
              hasFile={(token) => Boolean(record?.images?.find((i) => i.token === token)?.has_file)} /> : null}
            {step === "place" ? <PlaceSection {...props} /> : null}
            {step === "placement" ? <PlacementSection {...props} /> : null}
          </fieldset>
          {step === "send" ? (
            <SendSection draft={draft} record={record} errors={errors} flags={flags} checking={checking} dirty={dirty}
              saving={saving} saveProblem={saveProblem} submitting={submitting} onSave={() => void save()}
              onSubmit={() => void submit()} goTo={go} files={files} />
          ) : null}
          <div className={styles.stepNav}>
            {at > 0 ? <Button icon="chevron-right" className={styles.back} onClick={() => go(STEPS[at - 1])}>
              {t("contribute.previous")}</Button> : <span />}
            {at < STEPS.length - 1 ? (
              <Button variant="primary" onClick={() => go(STEPS[at + 1])}>{t("contribute.next", {
                name: t(`step.${STEPS[at + 1]}`) })}</Button>
            ) : null}
          </div>
        </section>
      </div>
    </Place>
  );
}
