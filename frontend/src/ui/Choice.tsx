// Checkbox, radio group and switch. Checkbox and radio are the platform's own inputs (their keyboard behaviour and
// semantics come for free), drawn in the room's colours; the switch is a button with role="switch".
import { useId, type InputHTMLAttributes, type ReactNode } from "react";
import styles from "./Choice.module.css";

export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: ReactNode;
}

export function Checkbox({ label, className, ...input }: CheckboxProps) {
  return (
    <label className={[styles.choice, className].filter(Boolean).join(" ")}>
      <input type="checkbox" className={styles.box} {...input} />
      <span>{label}</span>
    </label>
  );
}

export interface RadioGroupProps<V extends string> {
  legend: string;
  name?: string;
  value: V;
  options: { value: V; label: ReactNode }[];
  onChange: (value: V) => void;
  inline?: boolean;
}

export function RadioGroup<V extends string>({ legend, name, value, options, onChange, inline }: RadioGroupProps<V>) {
  const fallback = useId();
  return (
    <fieldset className={[styles.group, inline ? styles.inline : ""].join(" ")}>
      <legend className={styles.legend}>{legend}</legend>
      {options.map((o) => (
        <label key={o.value} className={styles.choice}>
          <input type="radio" className={styles.radio} name={name ?? fallback} value={o.value}
            checked={value === o.value} onChange={() => onChange(o.value)} />
          <span>{o.label}</span>
        </label>
      ))}
    </fieldset>
  );
}

export interface SwitchProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function Switch({ label, checked, onChange, disabled }: SwitchProps) {
  return (
    <button type="button" role="switch" aria-checked={checked} disabled={disabled} className={styles.switch}
      onClick={() => onChange(!checked)}>
      <span className={styles.track} aria-hidden="true"><span className={styles.thumb} /></span>
      <span>{label}</span>
    </button>
  );
}
