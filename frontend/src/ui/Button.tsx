// Buttons: primary (one per view: the action the place is for), secondary, quiet, danger; and the icon button, whose
// name is always given to assistive technology.
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { useI18n } from "../i18n";
import styles from "./Button.module.css";
import { Glyph, type IconSize } from "./Icon";

type Variant = "primary" | "secondary" | "quiet" | "danger";
type Size = "small" | "medium";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  busy?: boolean;
  icon?: string;
  children: ReactNode;
}

export function Button({ variant = "secondary", size = "medium", busy = false, icon, children, className, disabled,
  type = "button", ...rest }: ButtonProps) {
  const { t } = useI18n();
  return (
    <button type={type} className={[styles.button, styles[variant], styles[size], className].filter(Boolean).join(" ")}
      disabled={disabled} aria-busy={busy || undefined} {...rest}>
      {busy ? <span className={styles.spinner} aria-hidden="true" /> : icon ? <Glyph name={icon} size={20} /> : null}
      <span>{children}</span>
      {busy ? <span className="visually-hidden">{t("state.busy")}</span> : null}
    </button>
  );
}

export interface IconButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  icon: string;
  label: string;
  variant?: "quiet" | "secondary";
  iconSize?: IconSize;
}

export function IconButton({ icon, label, variant = "quiet", iconSize = 20, className, type = "button",
  ...rest }: IconButtonProps) {
  return (
    <button type={type} aria-label={label} title={label}
      className={[styles.button, styles.iconOnly, styles[variant], className].filter(Boolean).join(" ")} {...rest}>
      <Glyph name={icon} size={iconSize} />
    </button>
  );
}
