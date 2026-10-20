const data = window.PLATFORM;
const state = {
  view: "overview",
  firmId: data.firms[0] ? data.firms[0].firm_id : "",
  projectId: data.projects[0] ? data.projects[0].selection_id : "",
  query: "",
};

const views = [
  ["overview", "Market"],
  ["firms", "Firms"],
  ["projects", "Projects"],
  ["patterns", "Patterns"],
  ["lab", "Laboratory"],
  ["unexpected", "Unexpected"],
  ["explorer", "Explorer"],
  ["methods", "Methods"],
];

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[ch]));
}

function pct(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function num(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toFixed(digits);
}

function firmName(id) {
  const firm = data.firms.find((item) => item.firm_id === id);
  return firm ? firm.name : id;
}

function projectById(id) {
  return data.projects.find((item) => item.selection_id === id);
}

function projectTitle(project) {
  if (project.district && project.school) return `${project.district} — ${project.school}`;
  return project.school || project.label;
}

function bars(items, label, value, color = "observed") {
  const max = Math.max(...items.map((item) => Number(value(item)) || 0), 0.001);
  return items.map((item) => `
    <div class="bar-row">
      <span>${esc(label(item))}</span>
      <div class="track"><div class="fill ${color}" style="width:${(Number(value(item)) / max) * 100}%"></div></div>
      <span>${Number(value(item)) <= 1 ? pct(value(item)) : esc(Math.round(Number(value(item))))}</span>
    </div>`).join("");
}

function coefficientPlot(rows) {
  const width = 640;
  const height = rows.length * 28 + 16;
  const scale = 2.2;
  const mid = 250;
  const marks = rows.map((row, index) => {
    const y = 18 + index * 28;
    const x = mid + Number(row.estimate) * 40;
    const lo = mid + Number(row.ci_low) * 40;
    const hi = mid + Number(row.ci_high) * 40;
    return `
      <text x="0" y="${y + 4}">${esc(row.term)}</text>
      <line class="whisker" x1="${lo}" x2="${hi}" y1="${y}" y2="${y}"/>
      <circle class="dot" cx="${x}" cy="${y}" r="3.5"/>`;
  }).join("");
  return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}">
    <line x1="${mid}" x2="${mid}" y1="0" y2="${height}" stroke="#2c3440"/>
    ${marks}
  </svg>`;
}

function renderNav() {
  document.getElementById("nav").innerHTML = views.map(([id, label]) =>
    `<button data-view="${id}" class="${state.view === id ? "active" : ""}">${label}</button>`
  ).join("");
  document.getElementById("vintage").textContent =
    `${data.overview.first_date} – ${data.overview.last_date} · generated ${data.generated_at.slice(0, 10)}`;
}

function overview() {
  const o = data.overview;
  const q = data.quality;
  return `
    <section class="grid">
      ${[
        ["Competitions", o.competitions],
        ["Finalist rows", o.finalist_rows],
        ["Firms", o.firms],
        ["Mean finalists", num(o.mean_finalists)],
        ["Unique winners", o.unique_winners],
        ["Top-5 win share", pct(o.top5_share)],
        ["Winner HHI", num(o.hhi, 3)],
        ["Rows with a budget", q.records_with_budget],
      ].map(([label, value]) => `<article class="card"><span class="meta">${label}</span><strong>${esc(value)}</strong></article>`).join("")}
    </section>
    <div class="layout">
      <section class="panel">
        <h2>Wins by year</h2>
        <p class="note">Observed competitions in the model sample.</p>
        ${bars(o.by_year, (row) => row.year, (row) => row.competitions)}
      </section>
      <section class="panel">
        <h2>Newcomer share of wins</h2>
        <p class="note">A newcomer has no earlier finalist row in this archive. Pre-2007 work is unobserved.</p>
        ${bars(o.by_year, (row) => row.year, (row) => row.newcomer_win_share, "model")}
      </section>
    </div>
    <section class="panel" style="margin-top:0.8rem">
      <h2>School category of the winning entry</h2>
      <p class="note">Parsed from the school name. Unspecified means the published name did not say.</p>
      ${bars(o.by_grade, (row) => row.category, (row) => row.wins)}
    </section>`;
}

function firms() {
  const options = data.firms.map((firm) =>
    `<option value="${esc(firm.firm_id)}" ${firm.firm_id === state.firmId ? "selected" : ""}>${esc(firm.name)} (${firm.wins}/${firm.appearances})</option>`
  ).join("");
  const firm = data.firms.find((item) => item.firm_id === state.firmId) || data.firms[0];
  const meetings = data.projects.filter((project) => project.finalists.some((finalist) => finalist.firm_id === firm.firm_id));
  const opponents = {};
  meetings.forEach((project) => {
    const self = project.finalists.find((finalist) => finalist.firm_id === firm.firm_id);
    project.finalists.forEach((finalist) => {
      if (finalist.firm_id === firm.firm_id) return;
      const key = finalist.firm;
      opponents[key] = opponents[key] || { firm: key, meetings: 0, ahead: 0 };
      opponents[key].meetings += 1;
      if (self.rank < finalist.rank) opponents[key].ahead += 1;
    });
  });
  const h2h = Object.values(opponents).sort((a, b) => b.meetings - a.meetings).slice(0, 8);
  const grades = Object.entries(firm.by_grade).map(([category, value]) =>
    `<tr><td>${esc(category)}</td><td>${value.wins}</td><td>${value.appearances}</td><td>${pct(value.wins / value.appearances)}</td></tr>`
  ).join("");
  return `
    <div class="controls"><label>Firm<select id="firm-select">${options}</select></label></div>
    <section class="grid">
      <article class="card"><span class="meta">Finalist appearances</span><strong>${firm.appearances}</strong></article>
      <article class="card"><span class="meta">Wins</span><strong>${firm.wins}</strong></article>
      <article class="card"><span class="meta">Win rate</span><strong>${pct(firm.win_rate)}</strong><span class="note">${pct(firm.wilson_low)} – ${pct(firm.wilson_high)}</span></article>
      <article class="card"><span class="meta">Selection rating</span><strong>${num(firm.rating, 2)}</strong><span class="note">Full-sample procurement strength</span></article>
    </section>
    <div class="layout">
      <section class="panel">
        <h2>By school category</h2>
        <table><tr><th>Category</th><th>Wins</th><th>Appearances</th><th>Rate</th></tr>${grades}</table>
        <p class="note">${firm.first_year}–${firm.last_year}. ${firm.joint_venture ? "Kept as a joint venture or association, not merged into a parent." : "Not flagged as a joint venture."}</p>
        <p class="note">Cost performance is not scored. Design quality is not directly measured. The rating is not a preselection forecast.</p>
      </section>
      <section class="panel">
        <h2>Head-to-head published rank</h2>
        <p class="note">Count of shared finalist sets in which this firm was listed ahead of the other. Not a causal match effect.</p>
        <table><tr><th>Other finalist</th><th>Meetings</th><th>Listed ahead</th></tr>
          ${h2h.map((row) => `<tr><td>${esc(row.firm)}</td><td>${row.meetings}</td><td>${row.ahead}</td></tr>`).join("")}
        </table>
      </section>
    </div>`;
}

function projects() {
  const options = data.projects.map((project) =>
    `<option value="${esc(project.selection_id)}" ${project.selection_id === state.projectId ? "selected" : ""}>${esc(project.date)} · ${esc(projectTitle(project))}</option>`
  ).join("");
  const project = projectById(state.projectId) || data.projects[0];
  const rows = project.finalists.map((finalist) => `<tr>
      <td>${finalist.rank}</td>
      <td>${esc(finalist.firm)}${finalist.winner ? " · selected" : ""}</td>
      <td>${finalist.prior_wins}</td>
      <td>${finalist.prior_finals}</td>
      <td>${finalist.prior_grade_wins}</td>
      <td>${finalist.newcomer ? "yes" : "no"}</td>
      <td>${pct(finalist.p_retrospective)}</td>
      <td>${finalist.p_preperiod === null ? "—" : pct(finalist.p_preperiod)}</td>
    </tr>`).join("");
  return `
    <div class="controls"><label>Project<select id="project-select">${options}</select></label></div>
    <section class="panel">
      <h2>${esc(projectTitle(project))}</h2>
      <p>${esc(project.district)} · ${esc(project.category)} · ${esc(project.round)} · ${project.n_finalists} finalists
        ${project.budget_mid ? `· published range midpoint $${Number(project.budget_mid).toLocaleString()}` : ""}</p>
      <p class="note">Retrospective probabilities are fit on the full sample, including later competitions. They are not a forecast that was available on ${esc(project.date)}. Pre-period probabilities exist for 2019 onward and were fit only through 2018.</p>
      <p><a href="${esc(project.source_url)}">Official source</a> · rank method ${esc(project.rank_method)}</p>
      <table>
        <tr><th>Rank</th><th>Firm</th><th>Prior wins</th><th>Prior finals</th><th>Grade wins</th><th>Newcomer</th><th>Retrospective p</th><th>Pre-2019 model p</th></tr>
        ${rows}
      </table>
    </section>`;
}

function patterns() {
  return `
    <div class="layout">
      <section class="panel">
        <h2>Observed win rate by prior wins</h2>
        <p class="note">Each finalist appearance is one trial. Intervals are Wilson 95% intervals. This is descriptive, not the controlled logit effect.</p>
        <table>
          <tr><th>Prior wins</th><th>Wins</th><th>Appearances</th><th>Rate</th><th>Interval</th></tr>
          ${data.experience_curve.map((row) => `<tr><td>${esc(row.prior_wins)}</td><td>${row.wins}</td><td>${row.finalist_appearances}</td><td>${pct(row.win_rate)}</td><td>${pct(row.wilson_low)} – ${pct(row.wilson_high)}</td></tr>`).join("")}
        </table>
      </section>
      <section class="panel">
        <h2>Conditional-logit coefficients</h2>
        <p class="note">Modeled association. The mark is the estimate and the line is the bootstrap interval. Zero is the vertical rule.</p>
        ${coefficientPlot(data.coefficients)}
      </section>
    </div>
    <section class="panel" style="margin-top:0.8rem">
      <h2>2019-forward calibration of the pre-period logit</h2>
      <p class="note">Predicted probability versus the observed win frequency in that bin. Sample sizes are finalist rows, so they are smaller than a claim about competitions.</p>
      <table>
        <tr><th>Predicted bin</th><th>Mean predicted</th><th>Observed</th><th>Rows</th><th>Interval</th></tr>
        ${data.calibration.map((row) => `<tr><td>${esc(row.bin)}</td><td>${pct(row.mean_predicted)}</td><td>${pct(row.observed_win_rate)}</td><td>${row.finalist_rows}</td><td>${pct(row.wilson_low)} – ${pct(row.wilson_high)}</td></tr>`).join("")}
      </table>
    </section>`;
}

function lab() {
  const modelOptions = data.lab.models.map((model) =>
    `<option value="${model.through_year}">History through ${model.through_year} (${model.competitions} competitions)</option>`
  ).join("");
  const firmOptions = `<option value="__newcomer__">Newcomer, no archive history</option>` + data.lab.firm_names.map((firm) =>
    `<option value="${esc(firm.firm_id)}">${esc(firm.name)}</option>`
  ).join("");
  return `
    <section class="panel">
      <h2>Hypothetical finalist set</h2>
      <p class="note">Scores use the conditional logit and firm history dated on or before the cutoff. This is not a prediction for an unnamed real procurement, and it ignores interview evidence.</p>
      <div class="controls">
        <label>History cutoff<select id="lab-year">${modelOptions}</select></label>
        <label>Grade<select id="lab-grade">
          <option>elementary</option><option>middle</option><option>high</option><option>unspecified</option>
        </select></label>
        <label>Contest year<input id="lab-contest-year" value="2027" size="6"></label>
      </div>
      <div class="controls">
        <label>Firm 1<select class="lab-firm">${firmOptions}</select></label>
        <label>Firm 2<select class="lab-firm">${firmOptions}</select></label>
        <label>Firm 3<select class="lab-firm">${firmOptions}</select></label>
        <label>Firm 4<select class="lab-firm">${firmOptions}</select></label>
      </div>
      <button id="lab-run" type="button">Estimate probabilities</button>
      <div id="lab-out"></div>
    </section>`;
}

function snapshot(firmId, year) {
  if (!firmId || firmId === "__newcomer__") return null;
  const rows = data.lab.snapshots.filter((row) => row.firm_id === firmId && row.through_year <= year);
  return rows.length ? rows[rows.length - 1] : null;
}

function labScore(features, coefficients) {
  return coefficients.reduce((sum, row) => sum + features[row.term] * Number(row.estimate), 0);
}

function runLab() {
  const year = Number(document.getElementById("lab-year").value);
  const grade = document.getElementById("lab-grade").value;
  const contestYear = Number(document.getElementById("lab-contest-year").value);
  const model = data.lab.models.find((item) => item.through_year === year);
  const chosen = [...document.querySelectorAll(".lab-firm")].map((node) => node.value).filter(Boolean);
  const seen = new Set();
  const unique = [];
  chosen.forEach((firmId) => {
    if (firmId !== "__newcomer__" && seen.has(firmId)) return;
    seen.add(firmId);
    unique.push(firmId);
  });
  const out = document.getElementById("lab-out");
  if (unique.length < 2) {
    out.innerHTML = `<p class="note">Choose at least two distinct firms. A one-firm set has no competition to score.</p>`;
    return;
  }
  const outside = unique.length > 6 || unique.length < 2 || !Number.isFinite(contestYear);
  const rows = unique.map((firmId) => {
    const history = snapshot(firmId, year);
    const priorWins = history ? history.prior_wins : 0;
    const priorFinals = history ? history.prior_finals : 0;
    const gradeWins = history ? (history[`${grade}_wins`] || 0) : 0;
    const features = {
      prior_wins: priorWins,
      prior_grade_wins: grade === "unspecified" ? 0 : gradeWins,
      prior_finals: priorFinals,
      newcomer: priorFinals === 0 ? 1 : 0,
      prior_wins_x_field: priorWins * (unique.length - 3),
      prior_wins_x_time: priorWins * ((contestYear - 2016) / 10),
      prior_wins_x_high: priorWins * (grade === "high" ? 1 : 0),
    };
    const name = firmId === "__newcomer__" ? "Newcomer, no archive history" : firmName(firmId);
    return { firmId, name, features, history };
  });
  const point = rows.map((row) => labScore(row.features, model.coefficients));
  const maxPoint = Math.max(...point);
  const weights = point.map((score) => Math.exp(score - maxPoint));
  const total = weights.reduce((sum, weight) => sum + weight, 0);
  const probs = weights.map((weight) => weight / total);
  const draws = model.bootstrap || [];
  const bands = rows.map((row) => {
    if (!draws.length) return [null, null];
    const simulated = draws.map((draw) => {
      const scores = rows.map((candidate) => model.feature_names.reduce((sum, name, index) => sum + candidate.features[name] * draw[index], 0));
      const shift = Math.max(...scores);
      const w = scores.map((score) => Math.exp(score - shift));
      const z = w.reduce((sum, value) => sum + value, 0);
      return w[rows.indexOf(row)] / z;
    }).sort((a, b) => a - b);
    return [simulated[Math.floor(0.05 * simulated.length)], simulated[Math.floor(0.95 * simulated.length)]];
  });
  out.innerHTML = `
    <p class="note">${outside ? "This field size or year is outside the usual historical range. Treat the number as a sketch." : "Field size is inside the range usually published."}
    Budget is not an input: historical pages do not carry a comparable preselection budget. Grade ${esc(grade)} uses only wins in that parsed category.</p>
    <table>
      <tr><th>Firm</th><th>Prior wins</th><th>Prior finals</th><th>Probability</th><th>Bootstrap interval</th></tr>
      ${rows.map((row, index) => `<tr>
        <td>${esc(row.name)}</td>
        <td>${row.features.prior_wins}</td>
        <td>${row.features.prior_finals}</td>
        <td>${pct(probs[index])}</td>
        <td>${bands[index][0] === null ? "not estimated" : `${pct(bands[index][0])} – ${pct(bands[index][1])}`}</td>
      </tr>`).join("")}
    </table>`;
}

function unexpected() {
  if (!data.anomalies.length) {
    return `<section class="panel"><h2>Unexpected model outcomes</h2><p>No competition met the walk-forward threshold. That threshold is a winner probability of 15% or less when the model preferred a different firm.</p></section>`;
  }
  return `
    <section class="panel">
      <h2>Unexpected model outcomes</h2>
      <p>These competitions are places where a model trained only on earlier years gave the eventual top-ranked firm a low probability. They are not evidence of misconduct, favoritism, or a flawed district. Interview performance and materials are absent from the file.</p>
      ${data.anomalies.map((row) => `
        <article class="panel" style="margin-top:0.6rem">
          <h3>${esc(row.selection_date)} · ${esc(row.district)} — ${esc(row.school_name)}</h3>
          <p>Selected: ${esc(row.winner)} at ${pct(row.winner_probability)}. Model favorite: ${esc(row.favorite)} at ${pct(row.favorite_probability)}.
          Prior wins ${row.winner_prior_wins} versus ${row.favorite_prior_wins}. Training competitions: ${row.training_competitions}.</p>
          <p><a href="${esc(row.source_url)}">Official record</a></p>
          <table>
            <tr><th>Rank</th><th>Firm</th><th>Prior wins</th><th>Walk-forward p</th></tr>
            ${row.finalists.map((finalist) => `<tr><td>${finalist.rank}</td><td>${esc(finalist.firm)}</td><td>${finalist.prior_wins}</td><td>${pct(finalist.probability)}</td></tr>`).join("")}
          </table>
        </article>`).join("")}
    </section>`;
}

function explorer() {
  const query = state.query.toLowerCase();
  const rows = data.projects.filter((project) =>
    `${projectTitle(project)} ${project.district} ${project.school}`.toLowerCase().includes(query)
  ).slice(0, 80);
  return `
    <div class="controls">
      <label>Search projects<input id="search" value="${esc(state.query)}" placeholder="District or school"></label>
      <button id="download" type="button">Download model competitions CSV</button>
    </div>
    <section class="panel">
      <table>
        <tr><th>Date</th><th>Project</th><th>Category</th><th>Finalists</th><th>Selected</th><th>Source</th></tr>
        ${rows.map((project) => {
          const winner = project.finalists.find((finalist) => finalist.winner);
          return `<tr><td>${esc(project.date)}</td><td>${esc(projectTitle(project))}</td><td>${esc(project.category)}</td><td>${project.n_finalists}</td><td>${esc(winner ? winner.firm : "")}</td><td><a href="${esc(project.source_url)}">record</a></td></tr>`;
        }).join("")}
      </table>
      <p class="note">Showing ${rows.length} matching model competitions. The processed CSV files in data/processed contain the full extract, including alias audit and shortlists.</p>
    </section>`;
}

function methods() {
  return `
    <section class="stack">
      <article class="panel">
        <h2>What the probabilities are</h2>
        <ul>${data.limits.map((line) => `<li>${esc(line)}</li>`).join("")}</ul>
      </article>
      <article class="panel">
        <h2>Holdout metrics</h2>
        <table>
          <tr><th>Model</th><th>Sample</th><th>Competitions</th><th>Log loss</th><th>Top-choice accuracy</th><th>Brier</th></tr>
          ${data.metrics.map((row) => `<tr><td>${esc(row.model)}</td><td>${esc(row.sample)}</td><td>${row.competitions}</td><td>${num(row.log_loss, 3)}</td><td>${pct(row.top_choice_accuracy)}</td><td>${num(row.brier, 3)}</td></tr>`).join("")}
        </table>
      </article>
      <article class="panel">
        <h2>Hypotheses</h2>
        ${data.hypotheses.map((row) => `
          <h3>${esc(row.id)} <span class="tag ${esc(row.status)}">${esc(row.status)}</span></h3>
          <p>${esc(row.statement)}</p>
          <p>${esc(row.detail)}</p>
          <p class="note">${esc(row.limitation)}</p>`).join("")}
      </article>
      <article class="panel">
        <h2>Sources</h2>
        <table>
          <tr><th>Source</th><th>Local file</th><th>Link</th></tr>
          ${data.sources.map((source) => `<tr><td>${esc(source.title)}</td><td>${esc(source.file_present)}</td><td><a href="${esc(source.url)}">open</a></td></tr>`).join("")}
        </table>
      </article>
    </section>`;
}

const renderers = { overview, firms, projects, patterns, lab, unexpected, explorer, methods };

function render() {
  renderNav();
  document.getElementById("main").innerHTML = renderers[state.view]();
  document.querySelectorAll(".nav button").forEach((button) => {
    button.onclick = () => { state.view = button.dataset.view; render(); };
  });
  const firmSelect = document.getElementById("firm-select");
  if (firmSelect) firmSelect.onchange = () => { state.firmId = firmSelect.value; render(); };
  const projectSelect = document.getElementById("project-select");
  if (projectSelect) projectSelect.onchange = () => { state.projectId = projectSelect.value; render(); };
  const search = document.getElementById("search");
  if (search) search.oninput = () => { state.query = search.value; render(); };
  const download = document.getElementById("download");
  if (download) download.onclick = () => {
    const header = ["date", "district", "school", "category", "n_finalists", "winner", "source_url"];
    const lines = [header.join(",")].concat(data.projects.map((project) => {
      const winner = project.finalists.find((finalist) => finalist.winner);
      return [project.date, project.district, project.school, project.category, project.n_finalists, winner ? winner.firm : "", project.source_url]
        .map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",");
    }));
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "msba_model_competitions.csv";
    link.click();
    URL.revokeObjectURL(url);
  };
  const labRun = document.getElementById("lab-run");
  if (labRun) labRun.onclick = runLab;
}

if (!data) {
  document.getElementById("main").innerHTML = "<p>platform.js is missing. Run python -m msba_dsp.pipeline.</p>";
} else {
  render();
}
