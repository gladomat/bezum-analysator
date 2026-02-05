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

  function setActiveNav(route) {
    document.querySelectorAll(".nav__item").forEach((a) => a.classList.remove("is-active"));
    const link = document.querySelector(`.nav__item[data-nav="${route}"]`);
    if (link) link.classList.add("is-active");
  }

  function formatInt(n) {
    return new Intl.NumberFormat(undefined).format(n);
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

  function filteredWeeks() {
    if (!state.weeks) return [];
    if (!state.year) return state.weeks;
    return state.weeks.filter((w) => String(w).startsWith(`${state.year}-`));
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

  function svgBarChart({ labels, displayLabels, values, onClick }) {
    const w = 900;
    const h = 180;
    const pad = 26;
    const allZero = values.length > 0 && values.every((v) => v === 0);
    const max = Math.max(1, ...values);
    const barW = Math.max(2, (w - pad * 2) / values.length - 2);
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
          const x0 = pad + g.start * (barW + 2) - 2;
          const x1 = pad + (g.end + 1) * (barW + 2);
          const width = Math.max(0, x1 - x0);
          const fill = idx % 2 === 0 ? "rgba(148,163,184,0.06)" : "rgba(148,163,184,0.02)";
          const labelX = Math.max(pad, x0 + 6);
          return `
            <rect x="${x0}" y="${pad - 10}" width="${width}" height="${h - pad - 6}" rx="10" fill="${fill}"></rect>
            <text x="${labelX}" y="${pad - 2}" font-size="10" fill="#94a3b8">${g.year}</text>
          `;
        })
        .join("")
      : "";
    const bars = values
      .map((v, i) => {
        const x = pad + i * (barW + 2);
        const bh = Math.round(((h - pad * 2) * v) / max);
        const y = h - pad - bh;
        const title = `${labels[i]}: ${v}`;
        return `<g class="bar" data-i="${i}">
          <title>${title}</title>
          <rect x="${x}" y="${y}" width="${barW}" height="${bh}" rx="3" fill="rgba(25,127,230,.75)"></rect>
        </g>`;
      })
      .join("");
    const step = labelText.length <= 12 ? 1 : labelText.length <= 24 ? 2 : Math.ceil(labelText.length / 10);
    const ticks = labelText
      .map((l, i) => (i % step === 0 ? `<text x="${pad + i * (barW + 2)}" y="${h - 6}" font-size="10" fill="#64748b">${l}</text>` : ""))
      .join("");
    const svg = `
      <svg viewBox="0 0 ${w} ${h}" class="svg" preserveAspectRatio="none">
        <rect x="0" y="0" width="${w}" height="${h}" rx="12" fill="#ffffff" stroke="#e2e8f0"></rect>
        ${yearBg}
        ${bars}
        ${allZero
        ? `<text x="${w / 2}" y="${h / 2}" text-anchor="middle" font-size="12" fill="#64748b">All values are 0</text>`
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
    const months = filteredMonthRows();
    if (!months.length) {
      $("content").innerHTML = `
        <div class="card">
          <div class="card__title">No data for selection</div>
          <div class="card__sub">Choose a different year (or “All”).</div>
        </div>
      `;
      return;
    }
    const labels = months.map((r) => r.month);
    const displayLabels = state.year ? labels.map(monthLabel) : labels;
    const totals = months.map((r) => getMonthTotalRow(r, metric));
    const rates = months.map((r) => getMonthRateRow(r, metric));

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
    totalCard.appendChild(
      svgBarChart({
        labels,
        displayLabels,
        values: totals,
        onClick: (i) => navigate(`/month/${labels[i]}`),
      })
    );

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
    rateCard.appendChild(
      svgBarChart({
        labels,
        displayLabels,
        values: rates.map((x) => Math.round(x * 1000) / 1000),
        onClick: (i) => navigate(`/month/${labels[i]}`),
      })
    );

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
      weekLabel.innerHTML = `<a href="/week/${w}" class="mono">${w}</a>`;
      weekLabel.querySelector("a").addEventListener("click", (e) => {
        e.preventDefault();
        navigate(`/week/${w}`);
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
            navigate(`/week/${w}`);
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
      return `<rect x="${x}" y="${y}" width="${Math.max(1, barW - 2)}" height="${bh}" rx="2" fill="rgba(25,127,230,.72)"></rect>`;
    }).join("");
    return `
      <svg viewBox="0 0 ${w} ${h}" class="svg" preserveAspectRatio="none">
        <rect x="0" y="0" width="${w}" height="${h}" rx="12" fill="#ffffff" stroke="#e2e8f0"></rect>
        ${bars}
      </svg>
    `;
  }

  function renderWeek(payload) {
    setActiveNav("week");
    setCrumbs([{ text: state.run.run_id, bold: false }, { text: `week ${payload.week_start_date}`, bold: true }]);
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
          <div class="card__title">Week ${payload.week_start_date}</div>
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
      if (week && state.year && !String(week).startsWith(`${state.year}-`)) {
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
      if (route === "week" && week && state.year && !String(week).startsWith(`${state.year}-`)) {
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
