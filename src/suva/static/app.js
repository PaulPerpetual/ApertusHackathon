/* Suva Urteilsradar: ranked judgement cards, side panel, human overrides with simple name attribution. */
const I18N = {
  de: {
    app_title: "Urteilsradar", search: "Suchen (Titel, Nummer, Schlagwort)", show_low: "Wenig relevante zeigen",
    add: "+ Urteil zusammenfassen", who: "Wer bearbeitet?", who_hint: "Ihr Name wird bei Änderungen angezeigt. Keine Anmeldung nötig.",
    cancel: "Abbrechen", add_title: "Weiteres Urteil zusammenfassen", add_hint: "Geschäftsnummer (z.B. 8C_145/2025) oder Link von bger.ch",
    start: "Starten", name_set: "Name festlegen", edited_by: "bearbeitet von", ai: "KI", relevance: "Relevanz",
    why: "Begründung (Triage)", details: "Details", original: "Originalurteil", open_bger: "Auf bger.ch öffnen",
    summary_de: "Zusammenfassung DE", summary_fr: "Résumé FR", text: "Urteilstext", history: "Verlauf",
    edit: "Bearbeiten", save: "Speichern", show_ai: "KI-Original anzeigen", hide_ai: "KI-Original ausblenden",
    no_summary: "Noch keine Zusammenfassung.", generate: "Jetzt zusammenfassen", no_text: "Volltext nicht im Cache.",
    revert: "KI-Score wiederherstellen", score_ai: "KI-Score", score_human: "Manuell", decided: "Entscheid", published: "Publiziert",
    division: "Abteilung", model: "Modell", n_shown: (n, t) => `${n} von ${t} Urteilen · nach Relevanz sortiert · ziehen zum Umsortieren, Score anklicken zum Ändern`,
    saved: "Gespeichert", queued: "Wird verarbeitet …", done: "Fertig", failed: "Fehler", no_history: "Keine manuellen Änderungen.",
    h_score: "Score geändert", h_revert: "Score zurückgesetzt", h_summary_de: "Zusammenfassung DE bearbeitet", h_summary_fr: "Résumé FR bearbeitet",
    mock: "Mock-Modell", demo: "Demo", suva_party: "Suva Partei", human_example: "Suva-Originalzusammenfassung",
    view_radar: "Radar", view_kb: "Bibliothek", kind_all: "Alle", kind_suva: "Suva", kind_ai: "KI", kind_edited: "Bearbeitet",
    kb_search: "Bibliothek durchsuchen (Stichwort, Artikel, Nummer)", kb_n: (n) => `${n} Zusammenfassungen`, read_only: "Nur lesen",
    in_radar: "Im Radar öffnen", author: "Autor:in",
  },
  fr: {
    app_title: "Radar des arrêts", search: "Rechercher (titre, numéro, mot-clé)", show_low: "Afficher les moins pertinents",
    add: "+ Résumer un arrêt", who: "Qui modifie ?", who_hint: "Votre nom s'affiche lors des modifications. Pas d'inscription.",
    cancel: "Annuler", add_title: "Résumer un autre arrêt", add_hint: "Numéro de dossier (p.ex. 8C_145/2025) ou lien bger.ch",
    start: "Lancer", name_set: "Définir le nom", edited_by: "modifié par", ai: "IA", relevance: "Pertinence",
    why: "Justification (triage)", details: "Détails", original: "Arrêt original", open_bger: "Ouvrir sur bger.ch",
    summary_de: "Zusammenfassung DE", summary_fr: "Résumé FR", text: "Texte de l'arrêt", history: "Historique",
    edit: "Modifier", save: "Enregistrer", show_ai: "Afficher l'original IA", hide_ai: "Masquer l'original IA",
    no_summary: "Pas encore de résumé.", generate: "Résumer maintenant", no_text: "Texte intégral pas en cache.",
    revert: "Rétablir le score IA", score_ai: "Score IA", score_human: "Manuel", decided: "Décision", published: "Publié",
    division: "Cour", model: "Modèle", n_shown: (n, t) => `${n} sur ${t} arrêts · triés par pertinence · glisser pour réordonner, cliquer le score pour le modifier`,
    saved: "Enregistré", queued: "En cours …", done: "Terminé", failed: "Erreur", no_history: "Aucune modification manuelle.",
    h_score: "Score modifié", h_revert: "Score rétabli", h_summary_de: "Zusammenfassung DE modifiée", h_summary_fr: "Résumé FR modifié",
    mock: "Modèle fictif", demo: "Démo", suva_party: "Suva partie", human_example: "Résumé original Suva",
    view_radar: "Radar", view_kb: "Bibliothèque", kind_all: "Tous", kind_suva: "Suva", kind_ai: "IA", kind_edited: "Modifiés",
    kb_search: "Rechercher dans la bibliothèque (mot-clé, article, numéro)", kb_n: (n) => `${n} résumés`, read_only: "Lecture seule",
    in_radar: "Ouvrir dans le radar", author: "Auteur·e",
  },
};

const store = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch {} },
};
const state = { view: "radar", kbKind: "", kbTag: "", lang: store.get("suva.lang", "de"), editor: store.get("suva.editor", ""), cards: [], open: null, tab: null, editing: false, showAi: false };
const $ = (s) => document.querySelector(s);
const t = (k, ...a) => { const v = I18N[state.lang][k]; return typeof v === "function" ? v(...a) : v ?? k; };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtTime = (iso) => { if (!iso) return ""; const d = new Date(iso); return d.toLocaleString(state.lang === "fr" ? "fr-CH" : "de-CH", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }); };
const band = (s) => (s >= 70 ? "hi" : s >= 40 ? "mid" : "lo");

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
function toast(msg) { const el = $("#toast"); el.textContent = msg; el.classList.add("show"); clearTimeout(toast.h); toast.h = setTimeout(() => el.classList.remove("show"), 2200); }

/* ---------- editor name (no login: name stored in this browser) ---------- */
function askName() {
  return new Promise((resolve) => {
    const dlg = $("#nameDlg"); $("#nameInput").value = state.editor;
    dlg.onclose = () => {
      const v = $("#nameInput").value.trim();
      if (dlg.returnValue === "ok" && v) { state.editor = v; store.set("suva.editor", v); renderChrome(); }
      resolve(state.editor || null);
    };
    dlg.showModal();
  });
}
async function requireName() { if (state.status?.read_only) { toast(t("read_only")); return null; } return state.editor || (await askName()); }

/* ---------- chrome / i18n ---------- */
function renderChrome() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => (el.placeholder = t(el.dataset.i18nPlaceholder)));
  $("#search").placeholder = state.view === "kb" ? t("kb_search") : t("search");
  document.querySelectorAll(".views button").forEach((b) => b.classList.toggle("on", b.dataset.view === state.view));
  const ro = state.status?.read_only;
  $("#addBtn").hidden = !!ro; $("#editorChip").hidden = !!ro;
  document.querySelectorAll(".lang button").forEach((b) => b.classList.toggle("on", b.dataset.lang === state.lang));
  $("#editorChip").textContent = state.editor ? "✎ " + state.editor : t("name_set");
  document.title = "Suva · " + t("app_title");
  if (state.status) { const b = $("#modelBadge"); b.textContent = ro ? t("read_only") : state.status.mock ? t("mock") : state.status.model; b.classList.toggle("warn", state.status.mock || !!ro); }
}

/* ---------- list ---------- */
function filtered() {
  const q = $("#search").value.trim().toLowerCase();
  const showLow = $("#showLow").checked;
  return state.cards.filter((c) => {
    if (!showLow && (c.score ?? 0) < 30 && c.slug !== state.open) return false;
    if (!q) return true;
    return [c.docket, c.title_de, c.title_fr, c.explanation_de, c.explanation_fr, c.subject, ...(c.tags || [])].join(" ").toLowerCase().includes(q);
  });
}

function cardHtml(c, i) {
  const title = (state.lang === "fr" ? c.title_fr : c.title_de) || c.subject || c.docket;
  const expl = state.lang === "fr" ? c.explanation_fr : c.explanation_de;
  const overridden = c.score_override !== null && c.score_override !== undefined;
  const edited = c.last_editor ? `<span class="edited" title="${esc(fmtTime(c.last_edit_at))}">✎ ${esc(c.last_editor)} · ${esc(fmtTime(c.last_edit_at))}</span>` : "";
  return `<li class="card ${c.slug === state.open ? "active" : ""} ${(c.score ?? 0) < 30 ? "low" : ""}" draggable="true" data-slug="${esc(c.slug)}">
    <div class="rank" title="drag">${i + 1}</div>
    <div class="score" data-score>
      <span class="num ${band(c.score ?? 0)}" title="${t("relevance")}">${c.score ?? "–"}</span>
      ${overridden ? `<span class="orig" title="${t("score_ai")}">${t("ai")} ${c.ai_score}</span>` : ""}
    </div>
    <div>
      <div class="c-title">${esc(title)}</div>
      <div class="c-sub"><span>${esc(c.docket)}</span>${c.decision_date ? `<span>${esc(c.decision_date)}</span>` : ""}
        ${c.source === "demo" ? `<span class="demo">${t("demo")}</span>` : ""}${edited}</div>
      <p class="c-expl">${esc(expl)}</p>
      <div class="tags">${c.suva_party ? `<span class="tag party">${t("suva_party")}</span>` : ""}${(c.tags || []).map((g) => `<span class="tag">${esc(g)}</span>`).join("")}</div>
    </div></li>`;
}

function renderList() {
  const list = filtered();
  $("#cards").innerHTML = list.map(cardHtml).join("");
  $("#listMeta").textContent = t("n_shown", list.length, state.cards.length);
}

async function load() {
  state.cards = await api("/api/judgements");
  renderList();
  if (state.open) renderPanel();
}

/* ---------- inline score edit ---------- */
async function editScore(slug, el) {
  if (!(await requireName())) return;
  const c = state.cards.find((x) => x.slug === slug);
  el.innerHTML = `<input type="number" min="0" max="100" value="${c.score ?? 0}">`;
  const inp = el.querySelector("input"); inp.focus(); inp.select();
  let done = false;
  const commit = async (save) => {
    if (done) return; done = true;
    const v = Math.max(0, Math.min(100, parseInt(inp.value, 10)));
    if (save && !Number.isNaN(v) && v !== c.score) { await setScore(slug, v); } else renderList();
  };
  inp.addEventListener("keydown", (e) => { if (e.key === "Enter") commit(true); if (e.key === "Escape") commit(false); });
  inp.addEventListener("blur", () => commit(true));
  inp.addEventListener("click", (e) => e.stopPropagation());
}
async function setScore(slug, score) {
  await api(`/api/judgements/${encodeURIComponent(slug)}/score`, { method: "PUT", body: JSON.stringify({ score, editor: state.editor }) });
  toast(t("saved")); await load();
}

/* ---------- drag and drop: new score = midpoint of the neighbours at the drop position ---------- */
let dragSlug = null;
function setupDnD() {
  const ol = $("#cards");
  ol.addEventListener("dragstart", (e) => { const li = e.target.closest(".card"); if (!li) return; dragSlug = li.dataset.slug; li.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; });
  ol.addEventListener("dragend", () => { dragSlug = null; ol.querySelectorAll(".card").forEach((x) => x.classList.remove("dragging", "drop-before", "drop-after")); });
  ol.addEventListener("dragover", (e) => {
    if (!dragSlug) return; e.preventDefault();
    const li = e.target.closest(".card"); ol.querySelectorAll(".drop-before,.drop-after").forEach((x) => x.classList.remove("drop-before", "drop-after"));
    if (!li || li.dataset.slug === dragSlug) return;
    const r = li.getBoundingClientRect(); li.classList.add(e.clientY < r.top + r.height / 2 ? "drop-before" : "drop-after");
  });
  ol.addEventListener("drop", async (e) => {
    e.preventDefault();
    const li = e.target.closest(".card"); if (!li || !dragSlug || li.dataset.slug === dragSlug) return;
    const before = li.classList.contains("drop-before");
    const slug = dragSlug;
    if (!(await requireName())) return;
    const list = filtered().filter((c) => c.slug !== slug);
    let idx = list.findIndex((c) => c.slug === li.dataset.slug) + (before ? 0 : 1);
    const above = list[idx - 1], below = list[idx];
    let score;
    if (!above) score = Math.min(100, Math.ceil(((below?.score ?? 50) + 100) / 2));
    else if (!below) score = Math.max(0, Math.floor(above.score / 2));
    else score = Math.round((above.score + below.score) / 2);
    await setScore(slug, score);
  });
}

/* ---------- side panel ---------- */
async function openPanel(slug) {
  state.open = slug; state.editing = false; state.showAi = false; state.tab = state.tab || "summary_" + state.lang;
  $("#panel").hidden = false; renderList(); await renderPanel();
}
function closePanel() { state.open = null; $("#panel").hidden = true; renderList(); }

async function renderPanel() {
  const d = await api(`/api/judgements/${encodeURIComponent(state.open)}`);
  const a = d.assessment || {};
  const L = state.lang;
  $("#pDocket").innerHTML = `${esc(d.docket)} ${d.source === "demo" ? `<span class="demo">${t("demo")}</span>` : ""}`;
  $("#pTitle").textContent = (L === "fr" ? a.title_fr : a.title_de) || d.subject || d.docket;
  const overridden = a.score_override !== null && a.score_override !== undefined;
  const score = overridden ? a.score_override : a.ai_score;
  const tabs = ["summary_de", "summary_fr", "text", "history"];
  let html = `
    <div class="section"><h4>${t("relevance")}</h4>
      <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">
        <span class="score"><span class="num ${band(score ?? 0)}" style="padding:6px 14px">${score ?? "–"}</span></span>
        <span class="muted">${t("score_ai")}: ${a.ai_score ?? "–"}${overridden ? ` · ${t("score_human")}: ${a.score_override} (${esc(a.override_by)}, ${esc(fmtTime(a.override_at))})` : ""}</span>
        ${overridden ? `<button class="btn small" id="revertBtn">${t("revert")}</button>` : ""}
      </div></div>
    <div class="section"><h4>${t("why")}</h4><p>${esc(L === "fr" ? a.explanation_fr : a.explanation_de)}</p>
      <div class="tags">${a.suva_party ? `<span class="tag party">${t("suva_party")}</span>` : ""}${(a.tags || []).map((g) => `<span class="tag">${esc(g)}</span>`).join("")}</div></div>
    <div class="section"><h4>${t("details")}</h4><div class="kv">
      ${d.decision_date ? `<span class="muted">${t("decided")}</span><span>${esc(d.decision_date)}</span>` : ""}
      ${d.publication_date ? `<span class="muted">${t("published")}</span><span>${esc(d.publication_date)}</span>` : ""}
      ${d.division ? `<span class="muted">${t("division")}</span><span>${esc(d.division)}</span>` : ""}
      <span class="muted">${t("model")}</span><span>${esc(a.model || "–")}</span>
      ${d.url ? `<span class="muted">${t("original")}</span><span><a href="${esc(d.url)}" target="_blank" rel="noopener">${t("open_bger")} ↗</a></span>` : ""}
    </div></div>
    <div class="tabs">${tabs.map((k) => `<button data-tab="${k}" class="${state.tab === k ? "on" : ""}">${t(k)}${k === "history" && d.history.length ? ` (${d.history.length})` : ""}</button>`).join("")}</div>
    <div class="section" id="tabBody">`;

  if (state.tab.startsWith("summary_")) {
    const lang = state.tab.slice(-2);
    const s = d.summaries[lang];
    if (!s) {
      html += `<p class="muted">${t("no_summary")}</p>`;
      if (d.text) html += `<button class="btn primary" id="genBtn">${t("generate")}</button>`;
    } else if (state.editing) {
      html += `<textarea class="summary-edit" id="sumEdit">${esc(s.text)}</textarea>
        <div class="row"><button class="btn" id="cancelEdit">${t("cancel")}</button><button class="btn primary" id="saveEdit">${t("save")}</button></div>`;
    } else {
      const meta = s.edited_by ? `<span class="edited">✎ ${t("edited_by")} ${esc(s.edited_by)} · ${esc(fmtTime(s.edited_at))}</span>`
        : s.model === "suva-human-example" ? `<span class="tag">${t("human_example")}</span>` : `<span class="tag">${t("ai")} · ${esc(s.model)}</span>`;
      html += `<div class="c-sub">${meta}</div><div class="summary">${esc(s.text)}</div>
        <div class="row">${s.edited_by && s.ai_text ? `<button class="btn small" id="toggleAi">${state.showAi ? t("hide_ai") : t("show_ai")}</button>` : ""}
        <button class="btn" id="editBtn">${t("edit")}</button></div>
        ${state.showAi && s.ai_text ? `<div class="ai-orig">${esc(s.ai_text)}</div>` : ""}`;
    }
  } else if (state.tab === "text") {
    html += d.text ? `<div class="original">${esc(d.text)}</div>` : `<p class="muted">${t("no_text")}</p>`;
  } else {
    html += d.history.length
      ? `<ul class="history">${d.history.map((h) => `<li><b>${esc(h.editor)}</b> · ${esc(fmtTime(h.at))} · ${t("h_" + h.field.replace("_score", ""))}${h.field.includes("score") ? `: ${esc(h.old_value)} → ${esc(h.new_value)}` : ""}</li>`).join("")}</ul>`
      : `<p class="muted">${t("no_history")}</p>`;
  }
  html += `</div>`;
  $("#pBody").innerHTML = html;

  $("#pBody").querySelectorAll("[data-tab]").forEach((b) => (b.onclick = () => { state.tab = b.dataset.tab; state.editing = false; renderPanel(); }));
  const on = (id, fn) => { const el = document.getElementById(id); if (el) el.onclick = fn; };
  on("editBtn", async () => { if (await requireName()) { state.editing = true; renderPanel(); } });
  on("cancelEdit", () => { state.editing = false; renderPanel(); });
  on("toggleAi", () => { state.showAi = !state.showAi; renderPanel(); });
  on("saveEdit", async () => {
    const lang = state.tab.slice(-2);
    await api(`/api/judgements/${encodeURIComponent(state.open)}/summary/${lang}`, { method: "PUT", body: JSON.stringify({ text: $("#sumEdit").value, editor: state.editor }) });
    state.editing = false; toast(t("saved")); await load();
  });
  on("revertBtn", async () => {
    if (!(await requireName())) return;
    await api(`/api/judgements/${encodeURIComponent(state.open)}/score`, { method: "DELETE", body: JSON.stringify({ editor: state.editor }) });
    await load();
  });
  on("genBtn", () => startAdd(d.docket));
}

/* ---------- add / summarise another judgement ---------- */
async function startAdd(docket) {
  await api("/api/judgements", { method: "POST", body: JSON.stringify({ docket, editor: state.editor || null }) });
  toast(t("queued"));
  const poll = async () => {
    const s = await api("/api/status"); const job = s.jobs[docket];
    if (!job || job.status === "running") return setTimeout(poll, 3000);
    if (job.status === "done") { toast(t("done")); await load(); openPanel(job.slug); } else toast(`${t("failed")}: ${job.message}`);
  };
  setTimeout(poll, 3000);
}

/* ---------- knowledge base (library of all summaries, incl. Suva's own) ---------- */
function highlight(text, q) {
  let h = esc(text);
  q.toLowerCase().split(/\s+/).filter((x) => x.length > 1).forEach((term) => {
    const re = new RegExp("(" + term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
    h = h.replace(re, "<mark>$1</mark>");
  });
  return h;
}
async function loadKb() {
  const q = $("#search").value.trim();
  const params = new URLSearchParams({ q, tag: state.kbTag, kind: state.kbKind, lang: state.lang });
  const r = await api("/api/kb?" + params);
  $("#kbMeta").textContent = t("kb_n", r.total);
  $("#kbTags").innerHTML = (state.kbTag && !r.tags.includes(state.kbTag) ? [state.kbTag, ...r.tags] : r.tags).slice(0, 24)
    .map((g) => `<span class="tag ${g === state.kbTag ? "on" : ""}" data-tag="${esc(g)}">${esc(g)}</span>`).join("");
  $("#kbList").innerHTML = r.results.map((e) => {
    const title = (state.lang === "fr" ? e.title_fr : e.title_de) || e.docket;
    return `<li class="kb-item" data-slug="${esc(e.slug || "")}" data-docket="${esc(e.docket)}">
      <div class="c-sub"><b>${esc(e.docket)}</b>${e.date ? `<span>${esc(e.date)}</span>` : ""}<span class="kind ${e.kind}">${t("kind_" + e.kind)}</span>${e.score != null ? `<span>${t("relevance")} ${e.score}</span>` : ""}</div>
      <div class="c-title">${esc(title)}</div>
      <p class="snip">${highlight(e.snippet, q)}</p>
      <div class="tags">${(e.tags || []).map((g) => `<span class="tag">${esc(g)}</span>`).join("")}</div></li>`;
  }).join("");
}
async function openExample(docket) {
  const ex = await api("/api/kb/example/" + encodeURIComponent(docket));
  state.open = null; $("#panel").hidden = false;
  $("#pDocket").innerHTML = `${esc(ex.docket)} <span class="kind suva">${t("kind_suva")}</span>`;
  $("#pTitle").textContent = ex.title;
  $("#pBody").innerHTML = `
    <div class="section"><div class="kv"><span class="muted">${t("author")}</span><span>${esc(ex.author)}</span>
      ${ex.url ? `<span class="muted">${t("original")}</span><span><a href="${esc(ex.url)}" target="_blank" rel="noopener">${t("open_bger")} ↗</a></span>` : ""}</div></div>
    <div class="section"><h4>${t("summary_de")}</h4><div class="summary">${esc(ex.de)}</div></div>
    <div class="section"><h4>${t("summary_fr")}</h4><div class="summary">${esc(ex.fr)}</div></div>`;
}
function setView(v) {
  state.view = v; $("#radarView").hidden = v !== "radar"; $("#kbView").hidden = v !== "kb";
  $("#showLow").parentElement.hidden = v !== "radar";
  renderChrome(); v === "kb" ? loadKb() : renderList();
}

/* ---------- wiring ---------- */
function init() {
  renderChrome();
  document.querySelectorAll(".lang button").forEach((b) => (b.onclick = () => { state.lang = b.dataset.lang; store.set("suva.lang", state.lang); if (state.tab?.startsWith("summary_")) state.tab = "summary_" + state.lang; renderChrome(); state.view === "kb" ? loadKb() : renderList(); if (state.open) renderPanel(); }));
  $("#editorChip").onclick = askName;
  let deb; $("#search").oninput = () => { if (state.view === "kb") { clearTimeout(deb); deb = setTimeout(loadKb, 200); } else renderList(); };
  document.querySelectorAll(".views button").forEach((b) => (b.onclick = () => setView(b.dataset.view)));
  $("#kbKind").onclick = (e) => { const b = e.target.closest("[data-kind]"); if (!b) return; state.kbKind = b.dataset.kind; $("#kbKind").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b)); loadKb(); };
  $("#kbTags").onclick = (e) => { const g = e.target.closest("[data-tag]"); if (!g) return; state.kbTag = state.kbTag === g.dataset.tag ? "" : g.dataset.tag; loadKb(); };
  $("#kbList").onclick = (e) => { const li = e.target.closest(".kb-item"); if (!li) return; li.dataset.slug ? openPanel(li.dataset.slug) : openExample(li.dataset.docket); };
  $("#showLow").onchange = renderList;
  $("#closePanel").onclick = closePanel;
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && state.open && !document.querySelector("dialog[open]")) closePanel(); });
  $("#cards").addEventListener("click", (e) => {
    const li = e.target.closest(".card"); if (!li) return;
    const sc = e.target.closest("[data-score]");
    if (sc) { e.stopPropagation(); editScore(li.dataset.slug, sc); return; }
    openPanel(li.dataset.slug);
  });
  $("#addBtn").onclick = () => { const dlg = $("#addDlg"); $("#addInput").value = ""; dlg.onclose = () => { const v = $("#addInput").value.trim(); if (dlg.returnValue === "ok" && v) startAdd(v); }; dlg.showModal(); };
  setupDnD();
  api("/api/status").then((s) => { state.status = s; renderChrome(); });
  load();
}
init();
