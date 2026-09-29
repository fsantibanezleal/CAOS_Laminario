// The interface's two languages. The language follows the browser's preferences until the visitor chooses one; the
// choice is kept on this device and sets <html lang>. Plurals, numbers, dates and lists come from the platform's Intl.
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { en, type MessageKey } from "./en";
import { es } from "./es";
import { formatDate, pluralKey } from "./format";

export type Lang = "en" | "es";
export const LANGS: readonly Lang[] = ["en", "es"];
const CATALOGUES: Record<Lang, Record<string, string>> = { en, es };
const STORAGE_KEY = "laminario.lang";

/** The language the page opened in: set by the inline script in index.html before the first paint. */
export function initialLang(): Lang {
  const current = document.documentElement.lang;
  return current === "es" ? "es" : "en";
}

function remember(lang: Lang): void {
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    // storage may be blocked (a private window); the choice then lasts for this page only
  }
}

type Vars = Record<string, string | number>;

function fill(template: string, vars: Vars | undefined, lang: Lang): string {
  if (!vars) return template;
  const number = new Intl.NumberFormat(lang);
  return template.replace(/\{(\w+)\}/g, (whole, name: string) => {
    const value = vars[name];
    if (value === undefined) return whole;
    return typeof value === "number" ? number.format(value) : value;
  });
}

export interface I18n {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: MessageKey, vars?: Vars) => string;
  /** A count in words: ``plural("count.slides", 3)`` picks "count.slides.other" and fills {count}. */
  plural: (base: string, count: number, vars?: Vars) => string;
  number: (value: number, options?: Intl.NumberFormatOptions) => string;
  date: (value: Date | string, options?: Intl.DateTimeFormatOptions) => string;
  list: (items: string[]) => string;
}

const Context = createContext<I18n | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);

  const setLang = useCallback((next: Lang) => {
    document.documentElement.lang = next;
    remember(next);
    setLangState(next);
  }, []);

  const value = useMemo<I18n>(() => {
    const catalogue = CATALOGUES[lang];
    return {
      lang,
      setLang,
      t: (key, vars) => fill(catalogue[key] ?? en[key], vars, lang),
      plural: (base, count, vars) => {
        const key = pluralKey(lang, base, count, (k) => k in catalogue);
        return fill(catalogue[key] ?? key, { count, ...vars }, lang);
      },
      number: (v, options) => new Intl.NumberFormat(lang, options).format(v),
      date: (v, options) => formatDate(lang, v, options),
      list: (items) => new Intl.ListFormat(lang, { style: "long", type: "conjunction" }).format(items),
    };
  }, [lang, setLang]);

  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useI18n(): I18n {
  const value = useContext(Context);
  if (!value) throw new Error("useI18n outside LanguageProvider");
  return value;
}
