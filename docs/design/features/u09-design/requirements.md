# U9 · The design system · requirements

R-080, R-081, R-085 and R-089 are from the design document, shared by the interface units U9 to U15; U9 gates them
on the specimen place, and each later unit adds its places to the same gates. R-901 to R-905 are this unit's own.

```
R-080  THE interface SHALL show no horizontal page scroll at 360, 768, 1280 and 1920 px wide on every place, in both themes and both languages.
       Gate: frontend/gates/fit.mjs

R-081  THE design tokens SHALL give every text and icon colour a contrast ratio of at least 4.5 to 1 (3 to 1 for large text and icons) against its background in both themes.
       Gate: frontend/scripts/check-contrast.mjs

R-085  WHILE prefers-reduced-motion is set, THE interface SHALL run no transition longer than 0 ms except opacity.
       Gate: frontend/gates/motion.mjs

R-089  EVERY interface string SHALL exist in EN and ES.
       Gate: frontend/scripts/check-i18n.mjs

R-901  THE interface fonts SHALL be the exact rebuild of their pinned upstream files, and the subset of a font with a Reserved Font Name SHALL not carry that name.
       Gate: scripts/build_fonts.py

R-902  THE token stylesheet SHALL be the exact rebuild of the token source.
       Gate: frontend/scripts/build-tokens.mjs

R-903  WHEN a calendar date is shown, THE interface SHALL show the same calendar day in every time zone.
       Gate: frontend/src/i18n/format.test.ts

R-904  WHEN a dialog closes, THE interface SHALL return focus to the control that opened it, and WHEN Escape is pressed THE open tooltip SHALL close.
       Gate: frontend/gates/states.mjs

R-905  WHEN a place opens, THE page SHALL be painted in the room and the language stored on the device from its first frame.
       Gate: frontend/gates/fit.mjs
```
