// The print dialog (U14, R-1404 to R-1406): the selected slides' labels on a chosen stock. The visitor picks the stock
// (plain paper with cut marks, or a die-cut label sheet), the position of the first label (to use a part-used sheet),
// and the printer offset in 0.1 mm steps, which is kept on the device per stock. The test page comes first: every
// label's outline, printed at 100 % on plain paper and held against a sheet. Both are PDFs the browser opens.
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import type { StockRecord } from "../contract/catalog";
import { useI18n } from "../i18n";
import type { MessageKey } from "../i18n/en";
import { peopleApi, sheetUrl, testPageUrl, type Offset } from "../people/api";
import { Dialog } from "../ui/Overlay";
import { Select } from "../ui/Field";
import { Glyph } from "../ui/Icon";
import { Skeleton } from "../ui/Feedback";
import { localised } from "../tree/TreeProvider";
import { clampOffset, OFFSET_LIMIT, OFFSET_STEP, pagesFor, savedOffset, savedStock, saveOffset,
  saveStock } from "./printing";
import styles from "./PrintDialog.module.css";

export interface PrintDialogProps {
  open: boolean;
  onClose: () => void;
  /** The selected slides' ids, in the order their labels are printed. */
  slides: string[];
}

const PAGE_MM = { A4: [210, 297], Letter: [215.9, 279.4] } as const;
const fmt = (v: number) => String(Math.round(v * 100) / 100);

export function PrintDialog({ open, onClose, slides }: PrintDialogProps) {
  const { t, lang, plural, number } = useI18n();
  const [stocks, setStocks] = useState<StockRecord[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [stockId, setStockId] = useState("");
  const [start, setStart] = useState(0);
  const [offset, setOffset] = useState<Offset>({ dx: 0, dy: 0 });

  useEffect(() => {
    if (!open || stocks) return undefined;
    const controller = new AbortController();
    peopleApi.stocks(controller.signal).then((list) => {
      setStocks(list);
      const chosen = savedStock(list.map((s) => s.id), list[0]?.id ?? "");
      setStockId(chosen);
      setOffset(savedOffset(chosen));
    }, () => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, [open, stocks]);

  const stock = useMemo(() => stocks?.find((s) => s.id === stockId) ?? null, [stocks, stockId]);
  const choose = (id: string) => {
    setStockId(id);
    saveStock(id);
    setOffset(savedOffset(id));
    setStart(0);
  };
  const move = (axis: keyof Offset, raw: string) => {
    const next = { ...offset, [axis]: clampOffset(Number(raw.replace(",", "."))) };
    setOffset(next);
    if (stock) saveOffset(stock.id, next);
  };

  const groups = stocks ? (["plain", "stock"] as const).map((kind) => ({
    label: t(`labels.kind.${kind}`),
    options: stocks.filter((s) => s.kind === kind).map((s) => ({ value: s.id, label: localised(s.name, lang) })),
  })).filter((g) => g.options.length) : [];
  const pages = stock ? pagesFor(slides.length, start, stock.per_sheet) : 0;

  return (
    <Dialog open={open} title={t("labels.title")} onClose={onClose} actions={stock ? (
      <>
        <a className={styles.secondary} href={testPageUrl(stock.id, offset)} target="_blank" rel="noopener"
          data-print="test">
          <Glyph name="labels" size={20} />
          <span>{t("labels.test")}</span>
        </a>
        <a className={styles.primary} href={sheetUrl({ stock: stock.id, slides, start, offset, lang })}
          target="_blank" rel="noopener" data-print="sheet" aria-disabled={slides.length ? undefined : true}
          onClick={(e) => { if (!slides.length) e.preventDefault(); }}>
          <Glyph name="print" size={20} />
          <span>{t("labels.print", { count: slides.length })}</span>
        </a>
      </>
    ) : undefined}>
      <p className={styles.lead}>{plural("labels.lead", slides.length)}</p>
      {failed ? <p role="alert" className={styles.problem}>{t("labels.failed")}</p> : null}
      {!stocks && !failed ? <Skeleton lines={4} /> : null}
      {stock ? (
        <div className={styles.body}>
          <Select label={t("labels.stock")} value={stock.id} options={[]} groups={groups}
            onChange={(e) => choose(e.target.value)} />
          <p className={styles.facts} data-stock={stock.id}>
            {t("labels.facts", { w: number(stock.width_mm, { maximumFractionDigits: 2 }),
              h: number(stock.height_mm, { maximumFractionDigits: 2 }), across: stock.columns, down: stock.rows,
              count: stock.per_sheet, page: t(`labels.page.${stock.page}`) })}
          </p>
          <p className={styles.source}>{t("labels.source", { source: stock.source })}</p>
          {stock.warnings?.length ? (
            <ul className={styles.warnings}>
              {stock.warnings?.map((w) => (
                <li key={w}><Glyph name="warning" size={16} /><span>{t(`labels.warning.${w}` as MessageKey)}</span></li>
              ))}
            </ul>
          ) : null}
          <SheetMap stock={stock} start={start} count={slides.length} onStart={setStart} />
          <p className={styles.pages} role="status">
            {t("labels.from", { position: start + 1 })} · {plural("labels.pages", pages)}
          </p>
          <fieldset className={styles.offset}>
            <legend>{t("labels.offset")}</legend>
            <p className={styles.hint} id="offset-hint">{t("labels.offset.hint", { limit: OFFSET_LIMIT })}</p>
            <div className={styles.offsetFields}>
              {(["dx", "dy"] as const).map((axis) => (
                <label key={axis} className={styles.offsetField}>
                  <span>{t(`labels.offset.${axis}`)}</span>
                  <span className={styles.unit}>
                    <input type="number" inputMode="decimal" step={OFFSET_STEP} min={-OFFSET_LIMIT} max={OFFSET_LIMIT}
                      value={fmt(offset[axis])} aria-describedby="offset-hint"
                      onChange={(e) => move(axis, e.target.value)} />
                    <span aria-hidden="true">mm</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
          <p className={styles.hint}>{t("labels.scale")}</p>
        </div>
      ) : null}
    </Dialog>
  );
}

/**
 * The sheet drawn at its page's proportion, one position per label: choosing one starts the labels there. The
 * positions are a radio group (arrow keys move between them), numbered as the sheet is read, row by row.
 */
function SheetMap({ stock, start, count, onStart }: { stock: StockRecord; start: number; count: number;
  onStart: (i: number) => void }) {
  const { t } = useI18n();
  const [pw, ph] = PAGE_MM[stock.page];
  const used = (i: number) => i >= start && i < start + count;
  const style = { "--columns": stock.columns, "--ratio": `${pw} / ${ph}` } as CSSProperties;
  return (
    <fieldset className={styles.sheetField}>
      <legend>{t("labels.start")}</legend>
      <div className={styles.sheet} style={style} data-positions={stock.per_sheet}>
        {Array.from({ length: stock.per_sheet }, (_, i) => {
          const row = Math.floor(i / stock.columns) + 1;
          const column = (i % stock.columns) + 1;
          return (
            <label key={i} className={styles.position} data-used={used(i) || undefined}
              data-start={i === start || undefined}>
              <input type="radio" name="start" value={i} checked={i === start} onChange={() => onStart(i)}
                aria-label={t("labels.position", { n: i + 1, row, column })} />
              <span aria-hidden="true">{i === start ? i + 1 : ""}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
