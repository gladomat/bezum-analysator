(() => {
  const state = {
    run: null,
    months: null,
    topLines: null,
    weeks: null,
    year: localStorage.getItem("tg-checkstats.year") || null,
    metric: localStorage.getItem("tg-checkstats.metric") || "check_message_count",
    lang: localStorage.getItem("tg-checkstats.lang") || "de",
    availableYears: null,
  };

  const $ = (id) => document.getElementById(id);

  const I18N = {
    de: {
      nav_overview: "Übersicht",
      nav_month: "Monat",
      nav_week: "Woche",
      nav_predict: "Prognose",
      hint_title: "Lokale UI",
      hint_text: "Lokal, kann Exporte hochladen und neue Runs analysieren.",
      label_upload: "Upload",
      upload_btn: "Export auswählen",
      upload_running: "Analysiere…",
      upload_done: "Upload fertig",
      label_metric: "Metrik",
      label_year: "Jahr",
      label_lang: "Sprache",
      loading: "Lädt…",
      meta_loaded: "Daten geladen",
      meta_error: "Fehler",
      year_all: "Alle",
      crumb_overview: "Übersicht",
      crumb_overview_year: "Übersicht {year}",
      crumb_month: "Monat {month}",
      no_data_title: "Keine Daten für Auswahl",
      no_data_sub: "Wähle ein anderes Jahr (oder „Alle“).",
      overview_totals_title: "Monatliche Gesamtaktivität",
      overview_totals_sub: "Summen pro Monat ({metric}).",
      overview_totals_hint: "Klicke auf einen Balken für die Monatsansicht",
      overview_rate_title: "Rate pro Tag (im Zeitraum)",
      overview_rate_sub: "Normalisiert nach Tagen im Zeitraum ({metric}).",
      overview_lines_title: "Häufigste kontrollierte Linien",
      overview_lines_sub: "Top-Linien nach erkannten Kontrollen.",
      month_lines_title: "Häufigste kontrollierte Linien im Monat {month}",
      month_lines_sub: "Erkannte Kontrollen im ausgewählten Monat.",
      lines_tram: "Tram",
      lines_bus: "Bus",
      lines_no_data: "Keine Linien erkannt",
      lines_axis_hint: "Von links nach rechts: häufig zu selten",
      month_prev: "Vorheriger Monat",
      month_next: "Nächster Monat",
      month_title: "Monat {month}",
      month_sub: "Wochen (Zeilen) × Wochentage (Spalten). Klicke auf ein Wochenlabel für die Wochenansicht.",
      predict_title: "Prognose: Kontrolle nach Uhrzeit",
      predict_sub: "P(>=1 Kontrolle) für die ausgewählte Linie am heutigen Wochentag (alle Daten).",
      predict_mode: "Modus",
      predict_line: "Linie",
      predict_now: "Jetzt",
      predict_weekday: "Wochentag",
      predict_hour: "Stunde",
      predict_n: "n={n} Tage",
      predict_no_data: "Zu wenig Daten für diesen Wochentag.",
      weekday_means_title: "Wochentagsmittel",
      weekday_means_sub: "Mittelwert pro Wochentag innerhalb des ausgewählten Monatszeitraums.",
      posterior_section_title: "A-Posteriori-Wahrscheinlichkeit einer Kontrolle",
      posterior_tooltip_header: "A-Posteriori P(Kontrolle am Tag)",
      posterior_tooltip_mean: "Mittelwert",
      posterior_tooltip_ci: "95% ~",
      posterior_tooltip_days: "{s}/{n} Tage mit Kontrollen",
      timewins_title: "Wahrscheinliche Kontrollzeiten (p10–p90, Mittelwert ± σ)",
      timewins_no_checks: "keine Kontrollen (n=0)",
      timewins_none_tooltip: "Keine stündlichen Kontrollereignisse in diesem Monat/Wochentag.",
      timewins_tooltip_header: "Gewichtet nach stündlichem check_event_count",
      timewins_tooltip_range: "p10–p90",
      timewins_tooltip_mean: "Mittelwert",
      timewins_tooltip_sd: "σ",
      timewins_tooltip_n: "n={n} Ereignisse",
      unit_minutes: "Minuten",
      week_prev: "Vorherige Woche",
      week_next: "Nächste Woche",
      week_sub: "7 Tageskarten, jeweils mit 24 Stunden-Bins.",
      week_total: "Summe",
      error_artifacts_title: "Keine UI-Artefakte gefunden",
      error_artifacts_sub: "In diesem Run-Verzeichnis fehlen erforderliche UI-Artefakte.",
      error_missing_files: "Fehlende Dateien:",
      error_fix: "Fix: re-run {cmd} auf diesem Run.",
      ui_failed_title: "UI konnte nicht geladen werden",
      chart_all_zero: "Alle Werte sind 0",
      lang_de: "Deutsch",
      lang_en: "English",
    },
    en: {
      nav_overview: "Overview",
      nav_month: "Month",
      nav_week: "Week",
      nav_predict: "Predict",
      hint_title: "Local UI",
      hint_text: "Local UI; can upload exports and analyze new runs.",
      label_upload: "Upload",
      upload_btn: "Choose export",
      upload_running: "Analyzing…",
      upload_done: "Upload done",
      label_metric: "Metric",
      label_year: "Year",
      label_lang: "Language",
      loading: "Loading…",
      meta_loaded: "Data loaded",
      meta_error: "Error",
      year_all: "All",
      crumb_overview: "Overview",
      crumb_overview_year: "Overview {year}",
      crumb_month: "Month {month}",
      no_data_title: "No data for selection",
      no_data_sub: "Choose a different year (or “All”).",
      overview_totals_title: "Monthly Activity Totals",
      overview_totals_sub: "Totals by month ({metric}).",
      overview_totals_hint: "Click a bar to open month detail",
      overview_rate_title: "Per-Day In-Range Rate",
      overview_rate_sub: "Normalized by days in range ({metric}).",
      overview_lines_title: "Most checked lines",
      overview_lines_sub: "Top lines by detected checks.",
      month_lines_title: "Most checked lines in {month}",
      month_lines_sub: "Detected checks in the selected month.",
      lines_tram: "Tram",
      lines_bus: "Bus",
      lines_no_data: "No lines detected",
      lines_axis_hint: "Left to right: most to least common",
      month_prev: "Previous month",
      month_next: "Next month",
      month_title: "Month {month}",
      month_sub: "Weeks (rows) × weekdays (columns). Click a week label to open the week detail.",
      predict_title: "Predict: checks by hour",
      predict_sub: "P(>=1 check) for the selected line on today’s weekday (all data).",
      predict_mode: "Mode",
      predict_line: "Line",
      predict_now: "Now",
      predict_weekday: "Weekday",
      predict_hour: "Hour",
      predict_n: "n={n} days",
      predict_no_data: "Not enough data for this weekday.",
      weekday_means_title: "Weekday Means",
      weekday_means_sub: "Mean per weekday within the selected month range.",
      posterior_section_title: "Posterior probability of being checked",
      posterior_tooltip_header: "Posterior P(check in day)",
      posterior_tooltip_mean: "mean",
      posterior_tooltip_ci: "95% ~",
      posterior_tooltip_days: "{s}/{n} days with checks",
      timewins_title: "Probable checking hours (p10–p90, mean ± σ)",
      timewins_no_checks: "no checks (n=0)",
      timewins_none_tooltip: "No hourly check events in this month/weekday.",
      timewins_tooltip_header: "Weighted by hourly check_event_count",
      timewins_tooltip_range: "p10–p90",
      timewins_tooltip_mean: "mean",
      timewins_tooltip_sd: "σ",
      timewins_tooltip_n: "n={n} events",
      unit_minutes: "minutes",
      week_prev: "Previous week",
      week_next: "Next week",
      week_sub: "7 day panels, each with 24 hourly bins.",
      week_total: "total",
      error_artifacts_title: "No Data Artifacts Found",
      error_artifacts_sub: "This run directory is missing required UI artifacts.",
      error_missing_files: "Missing files:",
      error_fix: "Fix: re-run {cmd} on this run.",
      ui_failed_title: "UI failed to load",
      chart_all_zero: "All values are 0",
      lang_de: "Deutsch",
      lang_en: "English",
    },
  };

  function t(key, vars) {
    const dict = I18N[state.lang] || I18N.de;
    const raw = dict[key] || I18N.de[key] || key;
    if (!vars) return raw;
    return Object.entries(vars).reduce((acc, [k, v]) => acc.replaceAll(`{${k}}`, String(v)), raw);
  }

  function localeTag() {
    return state.lang === "en" ? "en-US" : "de-DE";
  }

  function renderLangSelect() {
    if (!$("lang")) return;
    $("lang").innerHTML = `
        <option value="de">${t("lang_de")}</option>
        <option value="en">${t("lang_en")}</option>
      `;
    $("lang").value = state.lang || "de";
  }

  function renderYearSelectOptions() {
    if (!$("year") || !state.availableYears) return;
    const years = state.availableYears;
    $("year").innerHTML = `<option value="">${t("year_all")}</option>` + years.map((y) => `<option value="${y}">${y}</option>`).join("");
    $("year").value = state.year || "";
  }

  function applyI18n() {
    document.documentElement.lang = state.lang || "de";
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      el.textContent = t(key);
    });
    renderLangSelect();
    renderYearSelectOptions();
  }

  function parseYearFromLocation() {
    const params = new URLSearchParams(window.location.search || "");
    const year = params.get("year");
    return year && /^\d{4}$/.test(year) ? year : null;
  }

  function setYearInLocation(year) {
    const url = new URL(window.location.href);
    if (year && /^\d{4}$/.test(year)) url.searchParams.set("year", year);
    else url.searchParams.delete("year");
    history.replaceState({}, "", url.pathname + url.search);
  }

  function urlWithYear(path) {
    const year = state.year && /^\d{4}$/.test(state.year) ? state.year : null;
    if (!year) return path;
    const url = new URL(path, window.location.origin);
    url.searchParams.set("year", year);
    return url.pathname + url.search;
  }

  function urlWithExplicitYear(path, year) {
    const y = year && /^\d{4}$/.test(String(year)) ? String(year) : null;
    if (!y) return path;
    const url = new URL(path, window.location.origin);
    url.searchParams.set("year", y);
    return url.pathname + url.search;
  }

  function setActiveNav(route) {
    document.querySelectorAll(".nav__item").forEach((a) => a.classList.remove("is-active"));
    const link = document.querySelector(`.nav__item[data-nav="${route}"]`);
    if (link) link.classList.add("is-active");
  }

  function formatInt(n) {
    return new Intl.NumberFormat(localeTag()).format(n);
  }

  function formatNumber(n, maxFractionDigits = 3) {
    return new Intl.NumberFormat(localeTag(), { maximumFractionDigits: maxFractionDigits }).format(n);
  }

  function formatPosteriorPct(p) {
    if (p == null || Number.isNaN(+p)) return "—";
    return `${Math.round(p * 100)}%`;
  }

  function formatHHMMFromHour(hourFloat) {
    if (hourFloat == null || Number.isNaN(+hourFloat)) return "—";
    const totalMinutes = Math.round(+hourFloat * 60);
    const h = Math.floor(totalMinutes / 60);
    const m = totalMinutes % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
  }

  function formatHH00FromHour(hourInt) {
    if (hourInt == null || Number.isNaN(+hourInt)) return "—";
    return `${String(parseInt(hourInt, 10)).padStart(2, "0")}:00`;
  }

  function posteriorTitle(row) {
    if (!row) return "";
    const mean = row.posterior_check_prob_mean;
    const lo = row.posterior_check_prob_low;
    const hi = row.posterior_check_prob_high;
    const s = row.posterior_successes;
    const n = row.posterior_trials;
    if (mean == null) return "";
    return `${t("posterior_tooltip_header")}\n${t("posterior_tooltip_mean")} ${formatPosteriorPct(mean)}\n${t("posterior_tooltip_ci")} [${formatPosteriorPct(lo)}, ${formatPosteriorPct(hi)}]\n${t("posterior_tooltip_days", { s, n })}`;
  }

  function renderPosteriorGrid({ labels, topLabels, rows, cols }) {
    const grid = document.createElement("div");
    grid.className = "probgrid";
    grid.style.gridTemplateColumns = `repeat(${cols || labels.length}, 1fr)`;
    grid.innerHTML = labels
      .map((label, i) => {
        const row = rows[i];
        const top = topLabels ? topLabels[i] : label;
        const mean = row ? formatPosteriorPct(row.posterior_check_prob_mean) : "—";
        const title = posteriorTitle(row);
        return `
          <div class="probcell" title="${title.replace(/\"/g, "&quot;")}">
            <div class="probcell__top">${top}</div>
            <div class="probcell__main">${mean}</div>
          </div>
        `;
      })
      .join("");
    return grid;
  }

  function renderPosteriorSection({ title, labels, topLabels, rows, cols }) {
    const wrap = document.createElement("div");
    wrap.innerHTML = `<div class="probtitle">${title || t("posterior_section_title")}</div>`;
    wrap.appendChild(renderPosteriorGrid({ labels, topLabels, rows, cols }));
    return wrap;
  }

  function renderWeekdayTimeWindows(weekdayStats) {
    const wrap = document.createElement("div");
    wrap.className = "timewins";
    wrap.innerHTML = `
        <div class="probtitle">${t("timewins_title")}</div>
        <div class="timewins__axis">
          <span>00</span><span>06</span><span>12</span><span>18</span><span>24</span>
        </div>
        <div class="timewins__rows"></div>
      `;
    const rowsEl = wrap.querySelector(".timewins__rows");

    (weekdayStats || []).forEach((s) => {
      const start = s.probable_check_start_hour_p10;
      const end = s.probable_check_end_hour_p90;
      const mean = s.probable_check_mean_hour;
      const sdMin = s.probable_check_sd_minutes;
      const total = s.probable_check_total_events;

      const has = start != null && end != null && mean != null && sdMin != null && total > 0;
      const startPct = has ? (start / 24) * 100 : 0;
      const endPct = has ? ((end + 1) / 24) * 100 : 0; // end is an hour-bin; extend to end of bin
      const meanPct = has ? (mean / 24) * 100 : 0;
      const sdHours = has ? sdMin / 60.0 : 0;
      const sdLoPct = has ? (Math.max(0, mean - sdHours) / 24) * 100 : 0;
      const sdHiPct = has ? (Math.min(24, mean + sdHours) / 24) * 100 : 0;

      const subtitle = has
        ? `${formatHH00FromHour(start)}–${formatHH00FromHour(end)} • μ ${formatHHMMFromHour(mean)} ± ${Math.round(sdMin)}m`
        : t("timewins_no_checks");

      const title = has
        ? `${t("timewins_tooltip_header")}\n${t("timewins_tooltip_range")}: ${formatHH00FromHour(start)}–${formatHH00FromHour(end)}\n${t("timewins_tooltip_mean")}: ${formatHHMMFromHour(mean)}\n${t("timewins_tooltip_sd")}: ${Math.round(sdMin)} ${t("unit_minutes")}\n${t("timewins_tooltip_n", { n: total })}`
        : t("timewins_none_tooltip");

      const row = document.createElement("div");
      row.className = "timewins__row";
      row.innerHTML = `
          <div class="timewins__label">${displayWeekday(s.weekday)}</div>
          <div class="timewins__bar" title="${title.replace(/\"/g, "&quot;")}">
            ${has ? `<div class="timewins__fill" style="left:${startPct}%;width:${Math.max(0, endPct - startPct)}%"></div>` : ""}
            ${has ? `<div class="timewins__sd" style="left:${sdLoPct}%;width:${Math.max(0, sdHiPct - sdLoPct)}%"></div>` : ""}
            ${has ? `<div class="timewins__mean" style="left:${meanPct}%"></div>` : ""}
          </div>
          <div class="timewins__text">${subtitle}</div>
        `;
      rowsEl.appendChild(row);
    });

    return wrap;
  }

  function metricLabel(metric) {
    return metric === "check_event_count" ? "Events" : "Messages";
  }

  function getMonthRateRow(row, metric) {
    return metric === "check_event_count" ? row.events_per_day_in_range : row.messages_per_day_in_range;
  }

  function getMonthTotalRow(row, metric) {
    return metric === "check_event_count" ? row.month_check_event_count : row.month_check_message_count;
  }

  function api(path) {
    return fetch(path, { headers: { "accept": "application/json" } }).then(async (r) => {
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw Object.assign(new Error("API error"), { status: r.status, data });
      return data;
    });
  }

  async function loadRunData({ preserveYear = true } = {}) {
    const previousYear = preserveYear ? state.year : null;

    state.run = await api("/api/run");
    if (!state.run.missing_files || state.run.missing_files.length === 0) {
      state.months = await api("/api/months");
      state.topLines = await api("/api/top-lines");
      state.months = state.months.map((r) => ({
        ...r,
        month_check_message_count: +r.month_check_message_count,
        month_check_event_count: +r.month_check_event_count,
        messages_per_day_in_range: +r.messages_per_day_in_range,
        events_per_day_in_range: +r.events_per_day_in_range,
      }));
      state.topLines = {
        tram: (state.topLines?.tram || []).map((row) => ({
          line_id: String(row.line_id || ""),
          check_event_count: +row.check_event_count || 0,
        })),
        bus: (state.topLines?.bus || []).map((row) => ({
          line_id: String(row.line_id || ""),
          check_event_count: +row.check_event_count || 0,
        })),
      };
    } else {
      state.months = null;
      state.topLines = { tram: [], bus: [] };
    }

    const years = uniqueYearsFromMonths(state.months || []);
    state.availableYears = years;

    const nextYear = (() => {
      const fromUrl = parseYearFromLocation();
      if (fromUrl && years.includes(fromUrl)) return fromUrl;
      if (previousYear && years.includes(previousYear)) return previousYear;
      const stored = state.year && years.includes(state.year) ? state.year : null;
      if (stored) return stored;
      const end = state.run && state.run.dataset && state.run.dataset.end_date;
      const endYear = typeof end === "string" ? end.slice(0, 4) : null;
      if (endYear && years.includes(endYear)) return endYear;
      return years.length ? years[years.length - 1] : null;
    })();

    state.year = nextYear;
    localStorage.setItem("tg-checkstats.year", state.year || "");
    if (state.year) setYearInLocation(state.year);
    else setYearInLocation(null);

    renderYearSelectOptions();
    applyI18n();

    if (state.run && state.run.dataset && state.run.dataset.start_date && state.run.dataset.end_date) {
      state.weeks = buildWeeksInRange(state.run.dataset.start_date, state.run.dataset.end_date);
    } else {
      state.weeks = [];
    }
  }

  async function uploadExportFile(file) {
    if (!file) return;
    if (!$("uploadBtn") || !$("uploadFile")) return;

    $("uploadBtn").classList.add("is-disabled");
    setMetaPill(t("upload_running"));
    try {
      const body = await file.arrayBuffer();
      const r = await fetch("/api/upload", {
        method: "POST",
        headers: {
          accept: "application/json",
          "content-type": "application/octet-stream",
        },
        body,
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw Object.assign(new Error("Upload failed"), { status: r.status, data });

      await loadRunData({ preserveYear: false });
      setMetaPill(t("upload_done"));
      navigate("/");
    } finally {
      $("uploadBtn").classList.remove("is-disabled");
      $("uploadFile").value = "";
    }
  }

  function yearFromMonth(month) {
    const m = String(month || "").match(/^(\d{4})-\d{2}$/);
    return m ? m[1] : null;
  }

  function monthOfYear(month) {
    const m = String(month || "").match(/^\d{4}-(\d{2})$/);
    return m ? m[1] : "";
  }

  function monthLabel(month) {
    const mm = monthOfYear(month);
    return mm || String(month || "");
  }

  function monthName(month) {
    const m = String(month || "").match(/^(\d{4})-(\d{2})$/);
    if (!m) return String(month || "");
    const d = new Date(`${m[1]}-${m[2]}-01T00:00:00Z`);
    if (Number.isNaN(d.getTime())) return String(month || "");
    return new Intl.DateTimeFormat(localeTag(), { month: "long", year: "numeric" }).format(d);
  }

  const WEEKDAY_LABELS = {
    Mon: { de: "Mo", en: "Mon" },
    Tue: { de: "Di", en: "Tue" },
    Wed: { de: "Mi", en: "Wed" },
    Thu: { de: "Do", en: "Thu" },
    Fri: { de: "Fr", en: "Fri" },
    Sat: { de: "Sa", en: "Sat" },
    Sun: { de: "So", en: "Sun" },
  };

  function displayWeekday(label) {
    const entry = WEEKDAY_LABELS[String(label || "")];
    if (!entry) return String(label || "");
    return state.lang === "en" ? entry.en : entry.de;
  }

  function weekdayHeadLabels() {
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map(displayWeekday);
  }

  function uniqueYearsFromMonths(months) {
    const years = new Set();
    (months || []).forEach((r) => {
      const y = yearFromMonth(r.month);
      if (y) years.add(y);
    });
    return Array.from(years).sort();
  }

  function filteredMonthRows() {
    if (!state.months) return [];
    if (!state.year) return state.months;
    return state.months.filter((r) => yearFromMonth(r.month) === state.year);
  }

  function defaultMonthForYear() {
    const rows = filteredMonthRows();
    return rows.length ? rows[rows.length - 1].month : null;
  }

  function buildWeeksInRange(startDateStr, endDateStr) {
    const start = new Date(`${startDateStr}T00:00:00Z`);
    const end = new Date(`${endDateStr}T00:00:00Z`);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return [];

    // Normalize to Monday (UTC) <= start
    const day = start.getUTCDay(); // 0=Sun..6=Sat
    const mondayOffset = (day + 6) % 7;
    const cur = new Date(start.getTime() - mondayOffset * 86400000);

    const out = [];
    while (cur <= end) {
      out.push(cur.toISOString().slice(0, 10));
      cur.setUTCDate(cur.getUTCDate() + 7);
    }
    return out;
  }

  function isoWeekInfo(dateStr) {
    const d = new Date(`${dateStr}T00:00:00Z`);
    if (Number.isNaN(d.getTime())) return { isoYear: null, isoWeek: null };

    const target = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
    // ISO week starts Monday. Convert Sun..Sat => 6..5, so Mon=0..Sun=6.
    const weekday = (target.getUTCDay() + 6) % 7;
    // Move to Thursday in this week to determine ISO year.
    target.setUTCDate(target.getUTCDate() - weekday + 3);
    const isoYear = target.getUTCFullYear();

    // First Thursday of ISO year determines week 1.
    const firstThursday = new Date(Date.UTC(isoYear, 0, 4));
    const firstWeekday = (firstThursday.getUTCDay() + 6) % 7;
    firstThursday.setUTCDate(firstThursday.getUTCDate() - firstWeekday + 3);

    const week = 1 + Math.round((target.getTime() - firstThursday.getTime()) / 604800000);
    return { isoYear, isoWeek: week };
  }

  function isoWeekLabelForStartDate(weekStartDate) {
    const { isoWeek } = isoWeekInfo(weekStartDate);
    if (!isoWeek) return `Week ?? • ${weekStartDate}`;
    return `Week ${String(isoWeek).padStart(2, "0")} • ${weekStartDate}`;
  }

  function isoYearForWeekStartDate(weekStartDate) {
    const { isoYear } = isoWeekInfo(weekStartDate);
    return isoYear ? String(isoYear) : null;
  }

  function filteredWeeks() {
    if (!state.weeks) return [];
    if (!state.year) return state.weeks;
    return state.weeks.filter((w) => String(isoWeekInfo(w).isoYear) === state.year);
  }

  function defaultWeekForYear() {
    const weeks = filteredWeeks();
    return weeks.length ? weeks[weeks.length - 1] : null;
  }

  function setCrumbs(parts) {
    $("crumbs").innerHTML = parts.map((p) => (p.bold ? `<b>${p.text}</b>` : p.text)).join(" / ");
  }

  function setMetaPill(text) {
    $("metaPill").textContent = text;
  }

  function renderError(missing) {
    setActiveNav("overview");
    setCrumbs([{ text: state.run?.run_id || "run", bold: false }, { text: t("meta_error"), bold: true }]);
    const list = (missing || []).map((f) => `<li class="mono">${f}</li>`).join("");
    const cmdHtml = `<span class="mono">tg-checkstats analyze --force …</span>`;
    $("content").innerHTML = `
        <div class="card error">
          <div class="card__title">${t("error_artifacts_title")}</div>
          <div class="card__sub">${t("error_artifacts_sub")}</div>
          <div>${t("error_missing_files")}</div>
          <ul>${list}</ul>
          <div class="card__sub" style="margin-top:10px">${t("error_fix", { cmd: cmdHtml })}</div>
        </div>
      `;
  }

  function svgBarChart({ labels, displayLabels, values, onClick, formatY }) {
    const minBarPitch = 26;
    const w = Math.max(900, labels.length * minBarPitch + 100);
    const h = 180;
    const padL = 72;
    const padR = 18;
    const padT = 26;
    const padB = 30;
    const allZero = values.length > 0 && values.every((v) => v === 0);
    const max = Math.max(1, ...values);
    const plotW = w - padL - padR;
    const plotH = h - padT - padB;
    const barW = Math.max(2, plotW / values.length - 2);
    const labelText = displayLabels && displayLabels.length === labels.length ? displayLabels : labels;

    const yearGroups = [];
    for (let i = 0; i < labels.length; i++) {
      const y = yearFromMonth(labels[i]);
      if (!y) continue;
      if (yearGroups.length === 0 || yearGroups[yearGroups.length - 1].year !== y) {
        yearGroups.push({ year: y, start: i, end: i });
      } else {
        yearGroups[yearGroups.length - 1].end = i;
      }
    }
    const yearBg = yearGroups.length > 1
      ? yearGroups
        .map((g, idx) => {
          const x0 = padL + g.start * (barW + 2) - 2;
          const x1 = padL + (g.end + 1) * (barW + 2);
          const width = Math.max(0, x1 - x0);
          const fill = idx % 2 === 0 ? "var(--surface-alt)" : "transparent";
          const labelX = Math.max(padL, x0 + 6);
          return `
            <rect x="${x0}" y="${padT - 10}" width="${width}" height="${h - padT - 6}" rx="10" fill="${fill}"></rect>
            <text x="${labelX}" y="${padT - 2}" font-size="14" fill="var(--text-muted)" font-weight="600">${g.year}</text>
          `;
        })
        .join("")
      : "";

    const yTickValues = [0, 0.25, 0.5, 0.75, 1].map((t) => t * max);
    const yTicks = yTickValues
      .map((v) => {
        const y = padT + plotH - (plotH * v) / max;
        const label = formatY ? formatY(v) : formatNumber(v);
        return `
          <line x1="${padL}" y1="${y}" x2="${w - padR}" y2="${y}" stroke="var(--border)" stroke-dasharray="4" stroke-width="1"></line>
          <text x="${padL - 10}" y="${y + 4}" text-anchor="end" font-size="13" fill="var(--text-muted)">${label}</text>
        `;
      })
      .join("");

    const bars = values
      .map((v, i) => {
        const x = padL + i * (barW + 2);
        const bh = Math.round((plotH * v) / max);
        const y = padT + plotH - bh;
        const title = `${monthName(labels[i])}: ${formatY ? formatY(v) : formatNumber(v)}`;
        return `<g class="bar" data-i="${i}">
          <title>${title}</title>
          <rect x="${x}" y="${y}" width="${barW}" height="${bh}" rx="4" fill="var(--primary)"></rect>
        </g>`;
      })
      .join("");
    const step = labelText.length <= 12 ? 1 : labelText.length <= 24 ? 2 : Math.ceil(labelText.length / 10);
    const ticks = labelText
      .map((l, i) => (i % step === 0 ? `<text x="${padL + i * (barW + 2)}" y="${h - 6}" font-size="13" fill="var(--text-sub)">${l}</text>` : ""))
      .join("");
    const svg = `
      <svg viewBox="0 0 ${w} ${h}" class="svg" preserveAspectRatio="none">
        <rect x="0" y="0" width="${w}" height="${h}" rx="12" fill="transparent"></rect>
        ${yearBg}
        ${yTicks}
          ${bars}
          ${allZero
        ? `<text x="${w / 2}" y="${h / 2}" text-anchor="middle" font-size="16" fill="var(--text-muted)">${t("chart_all_zero")}</text>`
        : ""
      }
          ${ticks}
        </svg>
      `;
    const wrap = document.createElement("div");
    wrap.className = "chart-container";
    wrap.style.overflowX = "auto";
    wrap.innerHTML = svg;
    if (typeof onClick === "function") {
      wrap.querySelectorAll(".bar").forEach((g) => {
        g.style.cursor = "pointer";
        g.addEventListener("click", () => onClick(parseInt(g.getAttribute("data-i"), 10)));
      });
    }
    return wrap;
  }

  function buildLinePlot(title, rows) {
    const section = document.createElement("div");
    section.className = "line-plot-block";
    const hasRows = Array.isArray(rows) && rows.length > 0;
    section.innerHTML = `<div class="line-plot-title">${title}</div>`;
    if (!hasRows) {
      const empty = document.createElement("div");
      empty.className = "line-stats__empty";
      empty.textContent = t("lines_no_data");
      section.appendChild(empty);
      return section;
    }
    const labels = rows.map((row) => String(row.line_id || ""));
    const values = rows.map((row) => +row.check_event_count || 0);
    section.appendChild(
      svgBarChart({
        labels,
        displayLabels: labels,
        values,
        formatY: (v) => formatInt(Math.round(v)),
      })
    );
    return section;
  }

  function renderTopLinesCard({ title, subtitle, topLines }) {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
        <div class="row">
          <div>
            <div class="card__title">${title}</div>
            <div class="card__sub">${subtitle}</div>
            <div class="card__sub" style="margin-top:-16px">${t("lines_axis_hint")}</div>
          </div>
        </div>
      `;
    card.appendChild(buildLinePlot(t("lines_tram"), topLines?.tram || []));
    card.appendChild(buildLinePlot(t("lines_bus"), topLines?.bus || []));
    return card;
  }

  function renderOverview() {
    setActiveNav("overview");
    const crumb = state.year ? t("crumb_overview_year", { year: state.year }) : t("crumb_overview");
    setCrumbs([{ text: state.run.run_id, bold: false }, { text: crumb, bold: true }]);
    setMetaPill(`${t("meta_loaded")} • ${metricLabel(state.metric)}`);

    const metric = state.metric;
    const allMonths = state.months || [];
    if (!allMonths.length) {
      $("content").innerHTML = `
          <div class="card">
            <div class="card__title">${t("no_data_title")}</div>
            <div class="card__sub">${t("no_data_sub")}</div>
          </div>
        `;
      return;
    }

    const availableYears = uniqueYearsFromMonths(allMonths);
    const baseYear = state.year && availableYears.includes(state.year) ? state.year : availableYears[availableYears.length - 1];
    const baseYearNum = parseInt(baseYear, 10);
    const yearsToShow = [];
    for (let i = 0; i < 3; i++) {
      const y = String(baseYearNum - i);
      if (availableYears.includes(y)) yearsToShow.push(y);
    }

    const rowsForYear = (year) => allMonths.filter((r) => yearFromMonth(r.month) === year);

    const totalCard = document.createElement("div");
    totalCard.className = "card";
    totalCard.innerHTML = `
        <div class="row">
          <div>
            <div class="card__title">${t("overview_totals_title")}</div>
            <div class="card__sub">${t("overview_totals_sub", { metric: metricLabel(metric) })}</div>
          </div>
          <div class="row__right">${t("overview_totals_hint")}</div>
        </div>
      `;

    yearsToShow.forEach((year) => {
      const months = rowsForYear(year);
      const labels = months.map((r) => r.month);
      const values = months.map((r) => getMonthTotalRow(r, metric));
      const block = document.createElement("div");
      block.innerHTML = `<div class="card__title" style="margin-top:8px;font-size:14px">${year}</div>`;
      block.appendChild(
        svgBarChart({
          labels,
          displayLabels: labels.map(monthLabel),
          values,
          formatY: (v) => formatInt(Math.round(v)),
          onClick: (i) => navigateWithYear(`/month/${labels[i]}`, yearFromMonth(labels[i])),
        })
      );
      block.appendChild(
        renderPosteriorSection({
          labels,
          topLabels: labels.map(monthLabel),
          rows: months,
        })
      );
      totalCard.appendChild(block);
    });

    const rateCard = document.createElement("div");
    rateCard.className = "card";
    rateCard.innerHTML = `
        <div class="row">
          <div>
            <div class="card__title">${t("overview_rate_title")}</div>
            <div class="card__sub">${t("overview_rate_sub", { metric: metricLabel(metric) })}</div>
          </div>
        </div>
      `;

    yearsToShow.forEach((year) => {
      const months = rowsForYear(year);
      const labels = months.map((r) => r.month);
      const values = months.map((r) => getMonthRateRow(r, metric)).map((x) => Math.round(x * 1000) / 1000);
      const block = document.createElement("div");
      block.innerHTML = `<div class="card__title" style="margin-top:8px;font-size:14px">${year}</div>`;
      block.appendChild(
        svgBarChart({
          labels,
          displayLabels: labels.map(monthLabel),
          values,
          formatY: (v) => formatNumber(v, 3),
          onClick: (i) => navigateWithYear(`/month/${labels[i]}`, yearFromMonth(labels[i])),
        })
      );
      block.appendChild(
        renderPosteriorSection({
          labels,
          topLabels: labels.map(monthLabel),
          rows: months,
        })
      );
      rateCard.appendChild(block);
    });

    const topLinesCard = renderTopLinesCard({
      title: t("overview_lines_title"),
      subtitle: t("overview_lines_sub"),
      topLines: state.topLines,
    });

    $("content").innerHTML = `<div class="grid"></div>`;
    const grid = document.querySelector(".grid");
    grid.appendChild(totalCard);
    grid.appendChild(rateCard);
    grid.appendChild(topLinesCard);
  }

  function heatColor(value, max) {
    if (max <= 0) return "rgba(79, 70, 229, 0)";
    const t = Math.min(1, value / max);
    // Gradient from very light indigo to strong indigo
    return `rgba(79, 70, 229, ${0.05 + t * 0.85})`;
  }

  function renderMonth(payload) {
    setActiveNav("month");
    setCrumbs([{ text: state.run.run_id, bold: false }, { text: t("crumb_month", { month: payload.month }), bold: true }]);
    setMetaPill(`${t("meta_loaded")} • ${metricLabel(state.metric)}`);

    const metric = state.metric;
    const max = Math.max(0, ...payload.grid.map((c) => (metric === "check_event_count" ? c.check_event_count : c.check_message_count)));
    const monthList = filteredMonthRows().map((r) => r.month);
    const idx = monthList.indexOf(payload.month);
    const prevMonth = idx > 0 ? monthList[idx - 1] : null;
    const nextMonth = idx >= 0 && idx < monthList.length - 1 ? monthList[idx + 1] : null;

    const weekMap = new Map();
    payload.grid.forEach((c) => weekMap.set(`${c.week_start_date}:${c.weekday_idx}`, c));

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
        <div class="row">
          <div class="navarrows">
            <button class="iconbtn" id="prevMonth" ${prevMonth ? "" : "disabled"} title="${t("month_prev")}">←</button>
            <button class="iconbtn" id="nextMonth" ${nextMonth ? "" : "disabled"} title="${t("month_next")}">→</button>
          </div>
          <div style="flex:1">
            <div class="card__title">${t("month_title", { month: payload.month })}</div>
            <div class="card__sub">${t("month_sub")}</div>
          </div>
        </div>
        <div class="heatmap" id="heat"></div>
      `;

    card.querySelector("#prevMonth").addEventListener("click", () => {
      if (prevMonth) navigate(`/month/${prevMonth}`);
    });
    card.querySelector("#nextMonth").addEventListener("click", () => {
      if (nextMonth) navigate(`/month/${nextMonth}`);
    });

    const heat = card.querySelector("#heat");
    heat.innerHTML = `<div></div>` + weekdayHeadLabels().map((d) => `<div class="heatmap__head">${d}</div>`).join("");

    payload.weeks.forEach((w) => {
      const weekLabel = document.createElement("div");
      weekLabel.className = "heatmap__week";
      weekLabel.innerHTML = `<a href="/week/${w}" class="mono">${isoWeekLabelForStartDate(w)}</a>`;
      weekLabel.querySelector("a").addEventListener("click", (e) => {
        e.preventDefault();
        navigateWithYear(`/week/${w}`, isoYearForWeekStartDate(w));
      });
      heat.appendChild(weekLabel);

      for (let wd = 0; wd < 7; wd++) {
        const c = weekMap.get(`${w}:${wd}`) || { in_month: false, in_range: false, date: "", check_message_count: 0, check_event_count: 0 };
        const value = metric === "check_event_count" ? c.check_event_count : c.check_message_count;
        const dayNum = c.date ? c.date.slice(-2) : "";
        const tile = document.createElement("div");
        tile.className = "tile" + (c.in_month ? " is-clickable" : " is-out");
        tile.style.background = c.in_month ? heatColor(value, max) : "#fff";
        tile.innerHTML = `<div class="tile__d">${dayNum}</div><div class="tile__v">${formatInt(value)}</div>`;
        if (c.in_month) {
          tile.addEventListener("click", () => {
            // Find the week start for this day (already known by row week label); keep week navigation explicit.
            navigateWithYear(`/week/${w}`, isoYearForWeekStartDate(w));
          });
        }
        heat.appendChild(tile);
      }
    });

    const statsCard = document.createElement("div");
    statsCard.className = "card";
    statsCard.innerHTML = `
        <div class="card__title">${t("weekday_means_title")}</div>
        <div class="card__sub">${t("weekday_means_sub")}</div>
        <div id="weekdayBars"></div>
      `;
    const labels = payload.weekday_stats.map((s) => s.weekday);
    const displayLabels = labels.map(displayWeekday);
    const values = payload.weekday_stats.map((s) => metric === "check_event_count" ? s.mean_events_per_weekday_in_range : s.mean_messages_per_weekday_in_range);
    statsCard.querySelector("#weekdayBars").appendChild(
      svgBarChart({ labels, displayLabels, values, onClick: () => { } })
    );
    statsCard.appendChild(
      renderPosteriorSection({
        labels,
        topLabels: displayLabels,
        rows: payload.weekday_stats,
        cols: 7,
      })
    );
    statsCard.appendChild(renderWeekdayTimeWindows(payload.weekday_stats));

    $("content").innerHTML = "";
    $("content").appendChild(card);
    $("content").appendChild(statsCard);
    $("content").appendChild(
      renderTopLinesCard({
        title: t("month_lines_title", { month: payload.month }),
        subtitle: t("month_lines_sub"),
        topLines: payload.top_lines || { tram: [], bus: [] },
      })
    );
  }

  function svgHistogram(hours, metric) {
    const w = 520;
    const h = 120;
    const pad = 16;
    const values = hours.map((x) => (metric === "check_event_count" ? x.check_event_count : x.check_message_count));
    const max = Math.max(1, ...values);
    const barW = (w - pad * 2) / 24;
    const bars = values.map((v, i) => {
      const x = pad + i * barW + 1;
      const bh = Math.round(((h - pad * 2) * v) / max);
      const y = h - pad - bh;
      const hr = String(i).padStart(2, "0");
      return `<g class="bar">
        <title>${hr}:00</title>
        <rect x="${x}" y="${y}" width="${Math.max(1, barW - 2)}" height="${bh}" rx="2" fill="var(--primary)"></rect>
      </g>`;
    }).join("");
    const tickHours = [0, 6, 12, 18, 23];
    const ticks = tickHours.map((hr) => {
      const x = pad + hr * barW + barW / 2;
      const label = String(hr).padStart(2, "0");
      return `<text x="${x}" y="${h - 6}" text-anchor="middle" font-size="14" fill="#64748b">${label}</text>`;
    }).join("");
    return `
      <svg viewBox="0 0 ${w} ${h}" class="svg" preserveAspectRatio="none">
        <rect x="0" y="0" width="${w}" height="${h}" rx="12" fill="#ffffff" stroke="#e2e8f0"></rect>
        ${bars}
        ${ticks}
      </svg>
    `;
  }

  function renderWeek(payload) {
    setActiveNav("week");
    setCrumbs([{ text: state.run.run_id, bold: false }, { text: isoWeekLabelForStartDate(payload.week_start_date), bold: true }]);
    setMetaPill(`${t("meta_loaded")} • ${metricLabel(state.metric)}`);

    const metric = state.metric;
    const weeks = filteredWeeks();
    const idx = weeks.indexOf(payload.week_start_date);
    const prevWeek = idx > 0 ? weeks[idx - 1] : null;
    const nextWeek = idx >= 0 && idx < weeks.length - 1 ? weeks[idx + 1] : null;
    const wrap = document.createElement("div");
    wrap.className = "card";
    wrap.innerHTML = `
        <div class="row">
          <div class="navarrows">
            <button class="iconbtn" id="prevWeek" ${prevWeek ? "" : "disabled"} title="${t("week_prev")}">←</button>
            <button class="iconbtn" id="nextWeek" ${nextWeek ? "" : "disabled"} title="${t("week_next")}">→</button>
          </div>
          <div style="flex:1">
            <div class="card__title">${isoWeekLabelForStartDate(payload.week_start_date)}</div>
            <div class="card__sub">${t("week_sub")}</div>
          </div>
        </div>
        <div class="days" id="days"></div>
      `;
    wrap.querySelector("#prevWeek").addEventListener("click", () => {
      if (prevWeek) navigate(`/week/${prevWeek}`);
    });
    wrap.querySelector("#nextWeek").addEventListener("click", () => {
      if (nextWeek) navigate(`/week/${nextWeek}`);
    });
    const daysEl = wrap.querySelector("#days");
    payload.days.forEach((d) => {
      const value = metric === "check_event_count" ? d.check_event_count : d.check_message_count;
      const card = document.createElement("div");
      card.className = "daycard";
      card.innerHTML = `
          <div class="daycard__title">${displayWeekday(d.weekday)}</div>
          <div class="daycard__sub"><span class="mono">${d.date}</span> • ${t("week_total")} ${formatInt(value)}</div>
          ${svgHistogram(d.hours, metric)}
        `;
      daysEl.appendChild(card);
    });
    $("content").innerHTML = "";
    $("content").appendChild(wrap);
  }

  function parseRoute() {
    const path = window.location.pathname.replace(/\/+$/, "") || "/";
    if (path === "/") return { route: "overview" };
    const m = path.match(/^\/month\/(\d{4}-\d{2})$/);
    if (m) return { route: "month", month: m[1] };
    if (path === "/month") return { route: "month", month: null };
    const w = path.match(/^\/week\/(\d{4}-\d{2}-\d{2})$/);
    if (w) return { route: "week", week: w[1] };
    if (path === "/week") return { route: "week", week: null };
    if (path === "/predict") return { route: "predict" };
    return { route: "overview" };
  }

  function navigate(path) {
    history.pushState({}, "", urlWithYear(path));
    render();
  }

  function navigateWithYear(path, year) {
    const y = year && /^\d{4}$/.test(String(year)) ? String(year) : null;
    state.year = y;
    localStorage.setItem("tg-checkstats.year", state.year || "");
    setYearInLocation(state.year);
    history.pushState({}, "", urlWithExplicitYear(path, state.year));
    render();
  }

  async function render() {
    const yearFromUrl = parseYearFromLocation();
    if (yearFromUrl !== state.year) {
      state.year = yearFromUrl;
      localStorage.setItem("tg-checkstats.year", state.year || "");
      if ($("year")) $("year").value = state.year || "";
    }
    let { route, month, week } = parseRoute();
    setActiveNav(route);
    if (!state.run) return;

    if (state.run.missing_files && state.run.missing_files.length) {
      return renderError(state.run.missing_files);
    }

    if (route === "overview") return renderOverview();
    if (route === "month") {
      if (month && state.year && yearFromMonth(month) !== state.year) {
        const fallback = defaultMonthForYear();
        if (fallback) {
          history.replaceState({}, "", urlWithYear(`/month/${fallback}`));
          month = fallback;
        }
      }
      if (!month) {
        month = defaultMonthForYear();
        if (month) history.replaceState({}, "", urlWithYear(`/month/${month}`));
      }
      if (!month) return renderOverview();
      const payload = await api(`/api/month/${month}`);
      return renderMonth(payload);
    }
    if (route === "week") {
      if (week && state.year && isoYearForWeekStartDate(week) && isoYearForWeekStartDate(week) !== state.year) {
        const fallback = defaultWeekForYear();
        if (fallback) {
          history.replaceState({}, "", urlWithYear(`/week/${fallback}`));
          week = fallback;
        }
      }
      if (!week) {
        week = defaultWeekForYear();
        if (week) history.replaceState({}, "", urlWithYear(`/week/${week}`));
      }
      if (!week) return renderOverview();
      const payload = await api(`/api/week/${week}`);
      return renderWeek(payload);
    }
    if (route === "predict") return renderPredict();
    return renderOverview();
  }

  function modeLabel(mode) {
    return String(mode) === "bus" ? t("lines_bus") : t("lines_tram");
  }

  function formatPct(p) {
    if (p == null || Number.isNaN(+p)) return "—";
    return `${Math.round(+p * 100)}%`;
  }

  function svgProbWhiskerChart(rows, currentHour) {
    const w = 900;
    const h = 220;
    const padL = 56;
    const padR = 18;
    const padT = 16;
    const padB = 34;
    const plotW = w - padL - padR;
    const plotH = h - padT - padB;
    const barW = Math.max(6, plotW / 24 - 2);

    const y = (p) => padT + plotH - plotH * Math.min(1, Math.max(0, +p || 0));

    const yTicks = [0, 0.25, 0.5, 0.75, 1].map((v) => {
      const yy = y(v);
      const label = `${Math.round(v * 100)}%`;
      return `
        <line x1="${padL}" y1="${yy}" x2="${w - padR}" y2="${yy}" stroke="var(--border)" stroke-dasharray="4" stroke-width="1"></line>
        <text x="${padL - 10}" y="${yy + 4}" text-anchor="end" font-size="13" fill="var(--text-muted)">${label}</text>
      `;
    }).join("");

    const bars = (rows || []).map((r) => {
      const hour = +r.hour || 0;
      const mean = r.prob_mean;
      const lo = r.prob_low;
      const hi = r.prob_high;
      const x0 = padL + hour * (barW + 2);
      const isNow = currentHour != null && hour === +currentHour;
      const bh = Math.round(plotH * (mean == null ? 0 : Math.min(1, Math.max(0, +mean))));
      const yy = padT + plotH - bh;
      const title = [
        `${String(hour).padStart(2, "0")}:00`,
        `P ${formatPct(mean)}`,
        `95% [${formatPct(lo)}, ${formatPct(hi)}]`,
        `trials=${r.trials} successes=${r.successes}`,
      ].join("\n");

      const whisker = (lo == null || hi == null)
        ? ""
        : (() => {
          const yLo = y(lo);
          const yHi = y(hi);
          const cx = x0 + barW / 2;
          return `
            <line x1="${cx}" y1="${yHi}" x2="${cx}" y2="${yLo}" stroke="var(--text-main)" stroke-width="1.5" opacity="0.8"></line>
            <line x1="${cx - 6}" y1="${yHi}" x2="${cx + 6}" y2="${yHi}" stroke="var(--text-main)" stroke-width="1.5" opacity="0.8"></line>
            <line x1="${cx - 6}" y1="${yLo}" x2="${cx + 6}" y2="${yLo}" stroke="var(--text-main)" stroke-width="1.5" opacity="0.8"></line>
          `;
        })();

      return `
        <g class="bar">
          <title>${title}</title>
          <rect x="${x0}" y="${yy}" width="${barW}" height="${bh}" rx="4" fill="${isNow ? "var(--primary-hover)" : "var(--primary)"}" stroke="${isNow ? "var(--text-main)" : "transparent"}" stroke-width="${isNow ? 1.5 : 0}"></rect>
          ${whisker}
        </g>
      `;
    }).join("");

    const xTicks = Array.from({ length: 24 }, (_, hr) => hr).filter((hr) => hr % 2 === 0 || hr === 23).map((hr) => {
      const x0 = padL + hr * (barW + 2) + barW / 2;
      const label = String(hr).padStart(2, "0");
      return `<text x="${x0}" y="${h - 8}" text-anchor="middle" font-size="12" fill="var(--text-sub)">${label}</text>`;
    }).join("");

    const svg = `
      <svg viewBox="0 0 ${w} ${h}" class="svg" preserveAspectRatio="none">
        ${yTicks}
        ${bars}
        ${xTicks}
      </svg>
    `;
    const wrap = document.createElement("div");
    wrap.className = "chart-container";
    wrap.innerHTML = svg;
    return wrap;
  }

  async function renderPredict() {
    setActiveNav("predict");
    setCrumbs([{ text: state.run.run_id, bold: false }, { text: t("nav_predict"), bold: true }]);
    setMetaPill(`${t("meta_loaded")} • ${t("nav_predict")}`);

    const tramLines = (state.topLines?.tram || []).map((r) => String(r.line_id || "")).filter(Boolean);
    const busLines = (state.topLines?.bus || []).map((r) => String(r.line_id || "")).filter(Boolean);

    const storedMode = localStorage.getItem("tg-checkstats.predict.mode") || "tram";
    const mode = storedMode === "bus" ? "bus" : "tram";
    const lines = mode === "bus" ? busLines : tramLines;
    const storedLine = localStorage.getItem("tg-checkstats.predict.line") || "";
    const line = lines.includes(storedLine) ? storedLine : (lines[0] || "");

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="card__title">${t("predict_title")}</div>
      <div class="card__sub">${t("predict_sub")}</div>
      <div class="predict-controls">
        <div class="toggle">
          <label class="toggle__label" for="predictMode">${t("predict_mode")}</label>
          <div class="select-wrapper">
            <select id="predictMode">
              <option value="tram">${modeLabel("tram")}</option>
              <option value="bus">${modeLabel("bus")}</option>
            </select>
            <div class="select-arrow">
              <svg class="lucide" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
                fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="m6 9 6 6 6-6" />
              </svg>
            </div>
          </div>
        </div>
        <div class="toggle">
          <label class="toggle__label" for="predictLine">${t("predict_line")}</label>
          <div class="select-wrapper">
            <select id="predictLine"></select>
            <div class="select-arrow">
              <svg class="lucide" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
                fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="m6 9 6 6 6-6" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <div id="predictMeta" class="card__sub" style="margin-top:10px;margin-bottom:0"></div>
      <div id="predictChart" style="margin-top:14px"></div>
    `;

    const lineSelect = card.querySelector("#predictLine");
    const modeSelect = card.querySelector("#predictMode");
    modeSelect.value = mode;
    lineSelect.innerHTML = lines.map((l) => `<option value="${l}">${l}</option>`).join("");
    lineSelect.value = line;

    const load = async (m, l) => {
      if (!l) {
        card.querySelector("#predictMeta").textContent = t("predict_no_data");
        card.querySelector("#predictChart").innerHTML = "";
        return;
      }
      const payload = await api(`/api/predict/line/${encodeURIComponent(l)}?mode=${encodeURIComponent(m)}`);
      const weekday = payload.weekday ? displayWeekday(payload.weekday) : "—";
      const currentHour = payload.current_hour;
      const rowNow = (payload.hours || []).find((r) => +r.hour === +currentHour) || null;
      const trials = rowNow ? rowNow.trials : 0;
      const meta = `${t("predict_weekday")}: ${weekday} • ${t("predict_hour")}: ${String(currentHour).padStart(2, "0")}:00 • ${t("predict_n", { n: trials })} • ${t("predict_now")}: ${formatPct(rowNow ? rowNow.prob_mean : null)} (95% [${formatPct(rowNow ? rowNow.prob_low : null)}, ${formatPct(rowNow ? rowNow.prob_high : null)}])`;
      card.querySelector("#predictMeta").textContent = meta;
      card.querySelector("#predictChart").innerHTML = "";
      card.querySelector("#predictChart").appendChild(svgProbWhiskerChart(payload.hours || [], currentHour));
    };

    modeSelect.addEventListener("change", () => {
      const m = modeSelect.value === "bus" ? "bus" : "tram";
      localStorage.setItem("tg-checkstats.predict.mode", m);
      localStorage.removeItem("tg-checkstats.predict.line");
      navigate("/predict");
    });
    lineSelect.addEventListener("change", () => {
      const l = lineSelect.value || "";
      localStorage.setItem("tg-checkstats.predict.line", l);
      load(modeSelect.value, l).catch((err) => console.error(err));
    });

    $("content").innerHTML = "";
    $("content").appendChild(card);
    await load(mode, line);
  }

  async function init() {
    if (!["de", "en"].includes(state.lang)) state.lang = "de";
    localStorage.setItem("tg-checkstats.lang", state.lang);
    renderLangSelect();
    $("lang").addEventListener("change", () => {
      const next = $("lang").value || "de";
      state.lang = ["de", "en"].includes(next) ? next : "de";
      localStorage.setItem("tg-checkstats.lang", state.lang);
      applyI18n();
      render();
    });
    applyI18n();
    setMetaPill(t("loading"));

    $("metric").value = state.metric;
    $("metric").addEventListener("change", () => {
      state.metric = $("metric").value;
      localStorage.setItem("tg-checkstats.metric", state.metric);
      render();
    });

    if ($("uploadFile")) {
      $("uploadFile").addEventListener("change", () => {
        const file = $("uploadFile").files && $("uploadFile").files[0];
        uploadExportFile(file).catch((err) => {
          console.error(err);
          setMetaPill(t("meta_error"));
        });
      });
    }

    await loadRunData({ preserveYear: true });
    $("year").addEventListener("change", () => {
      const v = $("year").value || "";
      state.year = v && /^\d{4}$/.test(v) ? v : null;
      localStorage.setItem("tg-checkstats.year", state.year || "");
      setYearInLocation(state.year);

      const { route, month, week } = parseRoute();
      if (route === "month" && month && state.year && yearFromMonth(month) !== state.year) {
        const next = defaultMonthForYear();
        return navigate(next ? `/month/${next}` : "/");
      }
      if (route === "week" && week && state.year && isoYearForWeekStartDate(week) && isoYearForWeekStartDate(week) !== state.year) {
        const next = defaultWeekForYear();
        return navigate(next ? `/week/${next}` : "/");
      }
      render();
    });

    window.addEventListener("popstate", render);

    // Intercept sidebar navigation clicks for SPA behavior
    document.querySelectorAll(".nav__item").forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        const href = link.getAttribute("href");
        navigate(href);
      });
    });

    render();
  }

  init().catch((err) => {
    console.error(err);
    applyI18n();
    setMetaPill(t("meta_error"));
    $("content").innerHTML = `<div class="card error"><div class="card__title">${t("ui_failed_title")}</div><div class="card__sub mono">${String(err)}</div></div>`;
  });
})();
