// Progress (a bar with its value, or an indeterminate one), a skeleton for content that is on its way, and the empty
// state, which says why a place is empty and what can be done.
import type { ReactNode } from "react";
import { useI18n } from "../i18n";
import styles from "./Feedback.module.css";
import { Icon } from "./Icon";

export function Progress({ label, value }: { label: string; value?: number }) {
  const { number } = useI18n();
  const known = value !== undefined;
  return (
    <div className={styles.progress}>
      <div className={styles.progressHead}>
        <span>{label}</span>
        {known ? <span className={styles.value}>{number(value, { style: "percent" })}</span> : null}
      </div>
      <div role="progressbar" aria-label={label} aria-valuemin={known ? 0 : undefined} aria-valuemax={known ? 1 : undefined}
        aria-valuenow={known ? value : undefined} aria-valuetext={known ? number(value, { style: "percent" }) : undefined}
        className={[styles.track, known ? "" : styles.indeterminate].join(" ")}>
        <div className={styles.fill} style={known ? { width: `${Math.round(value * 100)}%` } : undefined} />
      </div>
    </div>
  );
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  const { t } = useI18n();
  return (
    <div className={styles.skeleton} role="status" aria-label={t("state.loading")}>
      {Array.from({ length: lines }, (_, i) => (
        <span key={i} className={styles.line} style={{ width: `${[92, 78, 64, 86][i % 4]}%` }} aria-hidden="true" />
      ))}
    </div>
  );
}

export function EmptyState({ icon, title, children, action }: { icon: string; title: string; children: ReactNode;
  action?: ReactNode }) {
  return (
    <div className={styles.empty}>
      <Icon name={icon} size={48} />
      <h3 className={styles.emptyTitle}>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
