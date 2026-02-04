(() => {
  const state = {
    run: null,
    months: null,
    metric: localStorage.getItem("tg-checkstats.metric") || "check_message_count",
  };

  const $ = (id) => document.getElementById(id);

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

  function svgBarChart({ labels, values, onClick }) {
    const w = 900;
    const h = 180;
    const pad = 26;
    const max = Math.max(1, ...values);
    const barW = Math.max(2, (w - pad * 2) / values.length - 2);
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
    const ticks = labels
      .map((l, i) => (i % Math.ceil(labels.length / 10) === 0 ? `<text x="${pad + i * (barW + 2)}" y="${h - 6}" font-size="10" fill="#64748b">${l}</text>` : ""))
      .join("");
    const svg = `
      <svg viewBox="0 0 ${w} ${h}" class="svg" preserveAspectRatio="none">
        <rect x="0" y="0" width="${w}" height="${h}" rx="12" fill="#ffffff" stroke="#e2e8f0"></rect>
        ${bars}
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
    setCrumbs([{ text: state.run.run_id, bold: false }, { text: "overview", bold: true }]);
    setMetaPill(`${state.run.timezone || "Europe/Berlin"} • Data loaded`);

    const metric = state.metric;
    const months = state.months;
    const labels = months.map((r) => r.month);
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

    const weekMap = new Map();
    payload.grid.forEach((c) => weekMap.set(`${c.week_start_date}:${c.weekday_idx}`, c));

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="card__title">Activity Heatmap</div>
      <div class="card__sub">Weeks (rows) × weekdays (columns). Click a week label to open the week detail.</div>
      <div class="heatmap" id="heat"></div>
    `;

    const heat = card.querySelector("#heat");
    heat.innerHTML = `<div></div>` + ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map((d) => `<div class="heatmap__head">${d}</div>`).join("");

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
        const c = weekMap.get(`${w}:${wd}`) || { in_month:false, in_range:false, date:"", check_message_count:0, check_event_count:0 };
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
      svgBarChart({ labels, values, onClick: () => {} })
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
    const wrap = document.createElement("div");
    wrap.className = "card";
    wrap.innerHTML = `
      <div class="card__title">Hourly Histograms</div>
      <div class="card__sub">7 day panels, each with 24 hourly bins.</div>
      <div class="days" id="days"></div>
    `;
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
    const w = path.match(/^\/week\/(\d{4}-\d{2}-\d{2})$/);
    if (w) return { route: "week", week: w[1] };
    return { route: "overview" };
  }

  function navigate(path) {
    history.pushState({}, "", path);
    render();
  }

  async function render() {
    const { route, month, week } = parseRoute();
    setActiveNav(route);
    if (!state.run) return;

    if (state.run.missing_files && state.run.missing_files.length) {
      return renderError(state.run.missing_files);
    }

    if (route === "overview") return renderOverview();
    if (route === "month" && month) {
      const payload = await api(`/api/month/${month}`);
      return renderMonth(payload);
    }
    if (route === "week" && week) {
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

    window.addEventListener("popstate", render);
    render();
  }

  init().catch((err) => {
    console.error(err);
    setMetaPill("Error");
    $("content").innerHTML = `<div class="card error"><div class="card__title">UI failed to load</div><div class="card__sub mono">${String(err)}</div></div>`;
  });
})();

