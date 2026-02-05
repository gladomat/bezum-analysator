(() => {
  const state = {
    run: null,
    months: null,
    weeks: null,
    year: localStorage.getItem("tg-checkstats.year") || null,
    metric: localStorage.getItem("tg-checkstats.metric") || "check_message_count",
  };

  const $ = (id) => document.getElementById(id);

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
    return new Intl.NumberFormat(undefined).format(n);
  }

  function formatNumber(n, maxFractionDigits = 3) {
    return new Intl.NumberFormat(undefined, { maximumFractionDigits: maxFractionDigits }).format(n);
  }

  function formatPosteriorPct(p) {
    if (p == null || Number.isNaN(+p)) return "—";
    return `${Math.round(p * 100)}%`;
  }

  function posteriorTitle(row) {
    if (!row) return "";
    const mean = row.posterior_check_prob_mean;
    const lo = row.posterior_check_prob_low;
    const hi = row.posterior_check_prob_high;
    const s = row.posterior_successes;
    const n = row.posterior_trials;
    if (mean == null) return "";
    return `Posterior P(check in day)\nmean ${formatPosteriorPct(mean)}\n95% ~ [${formatPosteriorPct(lo)}, ${formatPosteriorPct(hi)}]\n${s}/${n} days with checks`;
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
    return new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" }).format(d);
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
    setCrumbs([{ text: state.run?.run_id || "run", bold: false }, { text: "error", bold: true }]);
    const list = (missing || []).map((f) => `<li class="mono">${f}</li>`).join("");
    $("content").innerHTML = `
      <div class="card error">
        <div class="card__title">No Data Artifacts Found</div>
        <div class="card__sub">This run directory is missing required UI artifacts.</div>
        <div>Missing files:</div>
        <ul>${list}</ul>
        <div class="card__sub" style="margin-top:10px">Fix: re-run <span class="mono">tg-checkstats analyze --force …</span> on this run.</div>
      </div>
    `;
  }

  function svgBarChart({ labels, displayLabels, values, onClick, formatY }) {
    const w = 900;
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
          const fill = idx % 2 === 0 ? "rgba(148,163,184,0.06)" : "rgba(148,163,184,0.02)";
          const labelX = Math.max(padL, x0 + 6);
          return `
            <rect x="${x0}" y="${padT - 10}" width="${width}" height="${h - padT - 6}" rx="10" fill="${fill}"></rect>
            <text x="${labelX}" y="${padT - 2}" font-size="12" fill="#94a3b8">${g.year}</text>
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
          <line x1="${padL}" y1="${y}" x2="${w - padR}" y2="${y}" stroke="rgba(148,163,184,0.20)" stroke-width="1"></line>
          <text x="${padL - 10}" y="${y + 4}" text-anchor="end" font-size="12" fill="#64748b">${label}</text>
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
          <rect x="${x}" y="${y}" width="${barW}" height="${bh}" rx="3" fill="rgba(25,127,230,.75)"></rect>
        </g>`;
      })
      .join("");
    const step = labelText.length <= 12 ? 1 : labelText.length <= 24 ? 2 : Math.ceil(labelText.length / 10);
    const ticks = labelText
      .map((l, i) => (i % step === 0 ? `<text x="${padL + i * (barW + 2)}" y="${h - 6}" font-size="12" fill="#64748b">${l}</text>` : ""))
      .join("");
    const svg = `
      <svg viewBox="0 0 ${w} ${h}" class="svg" preserveAspectRatio="none">
        <rect x="0" y="0" width="${w}" height="${h}" rx="12" fill="#ffffff" stroke="#e2e8f0"></rect>
        ${yearBg}
        ${yTicks}
        ${bars}
        ${allZero
        ? `<text x="${w / 2}" y="${h / 2}" text-anchor="middle" font-size="14" fill="#64748b">All values are 0</text>`
        : ""
      }
        ${ticks}
      </svg>
    `;
    const wrap = document.createElement("div");
    wrap.innerHTML = svg;
    wrap.querySelectorAll(".bar").forEach((g) => {
      g.style.cursor = "pointer";
      g.addEventListener("click", () => onClick(parseInt(g.getAttribute("data-i"), 10)));
    });
    return wrap.firstElementChild;
  }

  function renderOverview() {
    setActiveNav("overview");
    const yearSuffix = state.year ? ` ${state.year}` : "";
    setCrumbs([{ text: state.run.run_id, bold: false }, { text: `overview${yearSuffix}`, bold: true }]);
    setMetaPill(`${state.run.timezone || "Europe/Berlin"} • Data loaded`);

    const metric = state.metric;
    const allMonths = state.months || [];
    if (!allMonths.length) {
      $("content").innerHTML = `
        <div class="card">
          <div class="card__title">No data for selection</div>
          <div class="card__sub">Choose a different year (or “All”).</div>
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
          <div class="card__title">Monthly Activity Totals</div>
          <div class="card__sub">Totals by month (${metricLabel(metric)}).</div>
        </div>
        <div class="row__right">Click a bar to open month detail</div>
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
        renderPosteriorGrid({
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
          <div class="card__title">Per-Day In-Range Rate</div>
          <div class="card__sub">Normalized by days in range (${metricLabel(metric)}).</div>
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
        renderPosteriorGrid({
          labels,
          topLabels: labels.map(monthLabel),
          rows: months,
        })
      );
      rateCard.appendChild(block);
    });

    $("content").innerHTML = `<div class="grid"></div>`;
    const grid = document.querySelector(".grid");
    grid.appendChild(totalCard);
    grid.appendChild(rateCard);
  }

  function heatColor(value, max) {
    if (max <= 0) return "rgba(25,127,230,0)";
    const t = Math.min(1, value / max);
    return `rgba(25,127,230,${0.08 + t * 0.52})`;
  }

  function renderMonth(payload) {
    setActiveNav("month");
    setCrumbs([{ text: state.run.run_id, bold: false }, { text: `month ${payload.month}`, bold: true }]);
    setMetaPill(`${state.run.timezone || "Europe/Berlin"} • ${metricLabel(state.metric)}`);

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
          <button class="iconbtn" id="prevMonth" ${prevMonth ? "" : "disabled"} title="Previous month">←</button>
          <button class="iconbtn" id="nextMonth" ${nextMonth ? "" : "disabled"} title="Next month">→</button>
        </div>
        <div style="flex:1">
          <div class="card__title">Month ${payload.month}</div>
          <div class="card__sub">Weeks (rows) × weekdays (columns). Click a week label to open the week detail.</div>
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
    heat.innerHTML = `<div></div>` + ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => `<div class="heatmap__head">${d}</div>`).join("");

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
      <div class="card__title">Weekday Means</div>
      <div class="card__sub">Mean per weekday within the selected month range.</div>
      <div id="weekdayBars"></div>
    `;
    const labels = payload.weekday_stats.map((s) => s.weekday);
    const values = payload.weekday_stats.map((s) => metric === "check_event_count" ? s.mean_events_per_weekday_in_range : s.mean_messages_per_weekday_in_range);
    statsCard.querySelector("#weekdayBars").appendChild(
      svgBarChart({ labels, values, onClick: () => { } })
    );
    statsCard.appendChild(
      renderPosteriorGrid({
        labels,
        rows: payload.weekday_stats,
        cols: 7,
      })
    );

    $("content").innerHTML = "";
    $("content").appendChild(card);
    $("content").appendChild(statsCard);
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
        <rect x="${x}" y="${y}" width="${Math.max(1, barW - 2)}" height="${bh}" rx="2" fill="rgba(25,127,230,.72)"></rect>
      </g>`;
    }).join("");
    const tickHours = [0, 6, 12, 18, 23];
    const ticks = tickHours.map((hr) => {
      const x = pad + hr * barW + barW / 2;
      const label = String(hr).padStart(2, "0");
      return `<text x="${x}" y="${h - 6}" text-anchor="middle" font-size="12" fill="#64748b">${label}</text>`;
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
    setMetaPill(`${state.run.timezone || "Europe/Berlin"} • ${metricLabel(state.metric)}`);

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
          <button class="iconbtn" id="prevWeek" ${prevWeek ? "" : "disabled"} title="Previous week">←</button>
          <button class="iconbtn" id="nextWeek" ${nextWeek ? "" : "disabled"} title="Next week">→</button>
        </div>
        <div style="flex:1">
          <div class="card__title">${isoWeekLabelForStartDate(payload.week_start_date)}</div>
          <div class="card__sub">7 day panels, each with 24 hourly bins.</div>
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
        <div class="daycard__title">${d.weekday}</div>
        <div class="daycard__sub"><span class="mono">${d.date}</span> • total ${formatInt(value)}</div>
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
    return renderOverview();
  }

  async function init() {
    $("metric").value = state.metric;
    $("metric").addEventListener("change", () => {
      state.metric = $("metric").value;
      localStorage.setItem("tg-checkstats.metric", state.metric);
      render();
    });

    state.run = await api("/api/run");
    if (!state.run.missing_files || state.run.missing_files.length === 0) {
      state.months = await api("/api/months");
      // Ensure numeric keys are numbers (api already returns numbers, but keep robust)
      state.months = state.months.map((r) => ({
        ...r,
        month_check_message_count: +r.month_check_message_count,
        month_check_event_count: +r.month_check_event_count,
        messages_per_day_in_range: +r.messages_per_day_in_range,
        events_per_day_in_range: +r.events_per_day_in_range,
      }));
    }

    const years = uniqueYearsFromMonths(state.months || []);
    const defaultYear = (() => {
      const fromUrl = parseYearFromLocation();
      if (fromUrl && years.includes(fromUrl)) return fromUrl;
      const stored = state.year && years.includes(state.year) ? state.year : null;
      if (stored) return stored;
      const end = state.run && state.run.dataset && state.run.dataset.end_date;
      const endYear = typeof end === "string" ? end.slice(0, 4) : null;
      if (endYear && years.includes(endYear)) return endYear;
      return years.length ? years[years.length - 1] : null;
    })();

    state.year = defaultYear;
    localStorage.setItem("tg-checkstats.year", state.year || "");
    if (state.year) setYearInLocation(state.year);

    $("year").innerHTML =
      `<option value="">All</option>` + years.map((y) => `<option value="${y}">${y}</option>`).join("");
    $("year").value = state.year || "";
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

    if (state.run && state.run.dataset && state.run.dataset.start_date && state.run.dataset.end_date) {
      state.weeks = buildWeeksInRange(state.run.dataset.start_date, state.run.dataset.end_date);
    } else {
      state.weeks = [];
    }

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
    setMetaPill("Error");
    $("content").innerHTML = `<div class="card error"><div class="card__title">UI failed to load</div><div class="card__sub mono">${String(err)}</div></div>`;
  });
})();
