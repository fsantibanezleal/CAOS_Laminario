// Tooltip, dialog and toasts.
// - The tooltip opens on hover and on keyboard focus, stays while the pointer is over it, and Escape closes it
//   (WCAG 2.2 SC 1.4.13); it describes its trigger (aria-describedby).
// - The dialog is the platform's modal <dialog> (it keeps focus inside and makes the page inert); on closing, focus
//   returns to what opened it.
// - Toasts are announced politely and stay until dismissed: nothing disappears on a timer (WCAG 2.2 SC 2.2.1).
import { cloneElement, createContext, useCallback, useContext, useEffect, useId, useLayoutEffect, useMemo, useRef,
  useState,
  type ReactElement, type ReactNode } from "react";
import { useI18n } from "../i18n";
import { IconButton } from "./Button";
import { Glyph } from "./Icon";
import styles from "./Overlay.module.css";

export function Tooltip({ text, children }: { text: string; children: ReactElement<Record<string, unknown>> }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const anchor = useRef<HTMLSpanElement>(null);
  const tip = useRef<HTMLSpanElement>(null);
  const [place, setPlace] = useState<{ left: number; top: number } | null>(null);

  useEffect(() => {
    if (!open) return undefined;
    const escape = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [open]);

  // Placed above its trigger, centred, and kept inside the viewport; while closed it takes no space at all.
  useLayoutEffect(() => {
    if (!open || !anchor.current || !tip.current) return;
    const a = anchor.current.getBoundingClientRect();
    const t = tip.current.getBoundingClientRect();
    const margin = 8;
    const left = Math.min(Math.max(a.left + a.width / 2 - t.width / 2, margin),
      document.documentElement.clientWidth - t.width - margin);
    const above = a.top - t.height - 8;
    setPlace({ left, top: above >= margin ? above : a.bottom + 8 });
  }, [open, text]);

  return (
    <span ref={anchor} className={styles.tipAnchor} onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => { setOpen(false); setPlace(null); }} onFocus={() => setOpen(true)}
      onBlur={() => { setOpen(false); setPlace(null); }}>
      {cloneElement(children, { "aria-describedby": id })}
      <span ref={tip} role="tooltip" id={id} className={styles.tip} data-open={open || undefined}
        style={place ? { left: place.left, top: place.top } : undefined}>{text}</span>
    </span>
  );
}

export interface DialogProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  actions?: ReactNode;
}

export function Dialog({ open, title, onClose, children, actions }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const opener = useRef<Element | null>(null);
  const titleId = useId();
  const { t } = useI18n();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      opener.current = document.activeElement;
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  const closed = () => {
    onClose();
    const back = opener.current as HTMLElement | null;
    back?.focus?.();
  };

  return (
    <dialog ref={ref} className={styles.dialog} aria-labelledby={titleId} onClose={closed}
      onCancel={(e) => { e.preventDefault(); closed(); }}>
      <div className={styles.dialogHead}>
        <h2 id={titleId} className={styles.dialogTitle}>{title}</h2>
        <IconButton icon="close" label={t("action.close")} onClick={closed} />
      </div>
      <div className={styles.dialogBody}>{children}</div>
      {actions ? <div className={styles.dialogActions}>{actions}</div> : null}
    </dialog>
  );
}

type Tone = "good" | "warn" | "bad" | "info";
interface Toast { id: number; text: string; tone: Tone }
interface ToastApi { show: (text: string, tone?: Tone) => void }

const ToastContext = createContext<ToastApi | null>(null);

export function ToastRegion({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const next = useRef(1);
  const { t } = useI18n();
  const show = useCallback((text: string, tone: Tone = "info") => {
    setToasts((list) => [...list, { id: next.current++, text, tone }]);
  }, []);
  const api = useMemo(() => ({ show }), [show]);
  const glyph = { good: "check", warn: "warning", bad: "warning", info: "info" } as const;
  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className={styles.toasts} role="status" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={[styles.toast, styles[toast.tone]].join(" ")}>
            <Glyph name={glyph[toast.tone]} size={20} />
            <p>{toast.text}</p>
            <IconButton icon="close" label={t("action.dismiss")}
              onClick={() => setToasts((list) => list.filter((x) => x.id !== toast.id))} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const api = useContext(ToastContext);
  if (!api) throw new Error("useToast outside ToastRegion");
  return api;
}
