# UI i18n + Lucide icons + branding (tg-checkstats)

## Goal

Polish the `tg-checkstats` web UI to better support non-English usage and improve readability:

- Default UI language: German
- Provide a language switch (German/English)
- Use Lucide icons for navigation/controls
- Remove timezone text (e.g. “Europe/Berlin”) from the meta pill
- Rename the UI title/brand to: “Analyse der Beförderungsentgeltzahlungsumgehungsmaßnahmen in Leipzig”
- Keep the metric option label “Messages” unchanged

## Design

### i18n (frontend-only)

- Add a lightweight translation layer in `src/tg_checkstats/web_assets/app.js`:
  - `state.lang` persisted in `localStorage` (`tg-checkstats.lang`)
  - `I18N` dictionary for `de` + `en`
  - `t(key, vars)` with `{placeholder}` substitution
  - `applyI18n()` updates static DOM nodes via `[data-i18n]` and re-renders language/year selects
- Translate JS-rendered UI strings (cards, tooltips, navigation hints).
- Localize weekday headings/labels (`Mon..Sun` → `Mo..So`) and month names via `Intl.DateTimeFormat` using `de-DE`/`en-US`.

### Meta pill

- Replace `timezone • …` with `Data loaded/Daten geladen • <metric>` to avoid leaking/over-emphasizing timezone metadata.

### Icons (no runtime fetching)

- Embed Lucide SVGs inline in `index.html` to avoid extra network requests and keep the UI fully static.

### Branding

- Update `<title>` and sidebar brand title to the new German name.

## Non-goals

- No translation of the metric option labels in the metric dropdown; “Messages” stays as-is.
- No backend changes required for i18n.

