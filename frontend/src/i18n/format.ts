// Formatting through the platform's Intl, kept pure so it can be tested without a page.

const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

/**
 * A date in words. A date-only value ("1962-08-31", as labels and records give a collection date) is a calendar day,
 * not an instant: JavaScript reads it as midnight UTC, so it is formatted in UTC, or a visitor west of Greenwich
 * would see the day before.
 */
export function formatDate(lang: string, value: Date | string, options?: Intl.DateTimeFormatOptions): string {
  const calendarDay = typeof value === "string" && DATE_ONLY.test(value);
  const base: Intl.DateTimeFormatOptions = options ?? { dateStyle: "long" };
  return new Intl.DateTimeFormat(lang, calendarDay ? { ...base, timeZone: "UTC" } : base).format(new Date(value));
}

/** The CLDR plural category of a count in a language, falling back to "other" when the catalogue lacks it. */
export function pluralKey(lang: string, base: string, count: number, has: (key: string) => boolean): string {
  const category = new Intl.PluralRules(lang).select(count);
  return has(`${base}.${category}`) ? `${base}.${category}` : `${base}.other`;
}
