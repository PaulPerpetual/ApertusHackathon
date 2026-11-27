/* Urteilsradar: one macOS-style list of rulings (Neu · Alle · Erledigt), sortable columns, filters,
   detail pane, human score overrides and summary edits with simple name attribution. */
const I18N = {
  de: {
    app_title: "Urteilsradar", search: "Suchen", scope_new: "Neu", scope_all: "Alle", scope_done: "Erledigt",
    min_relevance: "Relevanz ab", sort_by: "Sortieren nach", asc: "Aufsteigend", desc: "Absteigend", keyword: "Schlagwort", all_keywords: "Alle Schlagworte",
    preview_lines: "Begründung in der Liste", all_lines: "alle", col_relevance: "Relevanz", col_ruling: "Urteil", col_title: "Titel", col_docket: "Nummer", col_date: "Entscheiddatum", col_tags: "Schlagworte", col_edited: "Bearbeitet",
    n_shown: (n, t) => `${n} von ${t}`, empty_new: "Keine neuen Urteile über dieser Relevanzschwelle.", empty: "Keine Urteile gefunden.",
    add: "Urteil manuell hinzufügen …", add_title: "Urteil manuell hinzufügen", add_hint: "Geschäftsnummer (z.B. 8C_145/2025) oder Link von bger.ch",
    start: "Zusammenfassen", cancel: "Abbrechen", who: "Wer bearbeitet?", who_hint: "Ihr Name wird bei Änderungen angezeigt. Keine Anmeldung nötig.",
    name: "Name", key: "Editor-Schlüssel (nur für den Server)", editor_set: (n) => n ? `Name: ${n} …` : "Name festlegen …",
    model: "Modell", mock: "Mock (kein LLM)", read_only: "Nur lesen",
    mark_done: "Erledigt", reopen: "Wieder öffnen", done_by: (n, at) => `Erledigt von ${n}, ${at}`, moved_done: "Nach «Erledigt» verschoben", moved_new: "Wieder geöffnet",
    relevance: "Relevanz", manual: "manuell", score_ai: "KI-Score", score_human: "Manuell", revert: "KI-Score wiederherstellen", edit_score: "Klicken zum Ändern",
    why: "Begründung", details: "Details", decided: "Entscheid", published: "Publiziert", division: "Abteilung", original: "Originalurteil", open_bger: "Auf bger.ch öffnen",
    summary_de: "Zusammenfassung DE", summary_fr: "Résumé FR", text: "Urteilstext", history: "Verlauf",
    edit: "Bearbeiten", edit_summary: "Zusammenfassung bearbeiten", adjust_score: "Score anpassen", save: "Speichern", show_ai: "KI-Original anzeigen", hide_ai: "KI-Original ausblenden", edited_by: "bearbeitet von", ai: "KI",
    no_summary: "Noch keine Zusammenfassung.", generate: "Jetzt zusammenfassen", no_text: "Volltext nicht verfügbar.", no_history: "Keine manuellen Änderungen.",
    h_score: "Score geändert", h_revert: "Score zurückgesetzt", h_summary_de: "Zusammenfassung DE bearbeitet", h_summary_fr: "Résumé FR bearbeitet", h_status: "Status",
    st_new: "neu", st_done: "erledigt", saved: "Gespeichert", failed_action: "Nicht gespeichert", err_key: "Editor-Schlüssel fehlt oder ist falsch (⋯ → Name/Schlüssel)", queued: "Wird verarbeitet …", done: "Fertig", failed: "Fehler",
    suva_party: "Suva Partei", human_example: "Suva-Originalzusammenfassung", demo: "Demo",
    cite_missing: "Erwägung im Volltext nicht gefunden", cite_hint: "Zur Erwägung im Urteilstext springen",
  },
  fr: {
    app_title: "Radar des arrêts", search: "Rechercher", scope_new: "Nouveaux", scope_all: "Tous", scope_done: "Traités",
    min_relevance: "Pertinence dès", sort_by: "Trier par", asc: "Croissant", desc: "Décroissant", keyword: "Mot-clé", all_keywords: "Tous les mots-clés",
    preview_lines: "Justification dans la liste", all_lines: "tout", col_relevance: "Pertinence", col_ruling: "Arrêt", col_title: "Titre", col_docket: "Numéro", col_date: "Date de l\u2019arrêt", col_tags: "Mots-clés", col_edited: "Modifié",
    n_shown: (n, t) => `${n} sur ${t}`, empty_new: "Aucun nouvel arrêt au-dessus de ce seuil.", empty: "Aucun arrêt trouvé.",
    add: "Ajouter un arrêt manuellement …", add_title: "Ajouter un arrêt manuellement", add_hint: "Numéro de dossier (p.ex. 8C_145/2025) ou lien bger.ch",
    start: "Résumer", cancel: "Annuler", who: "Qui modifie ?", who_hint: "Votre nom s'affiche lors des modifications. Pas d'inscription.",
    name: "Nom", key: "Clé d'éditeur (serveur uniquement)", editor_set: (n) => n ? `Nom : ${n} …` : "Définir le nom …",
    model: "Modèle", mock: "Fictif (sans LLM)", read_only: "Lecture seule",
    mark_done: "Traité", reopen: "Rouvrir", done_by: (n, at) => `Traité par ${n}, ${at}`, moved_done: "Déplacé vers « Traités »", moved_new: "Rouvert",
    relevance: "Pertinence", manual: "manuel", score_ai: "Score IA", score_human: "Manuel", revert: "Rétablir le score IA", edit_score: "Cliquer pour modifier",
    why: "Justification", details: "Détails", decided: "Décision", published: "Publié", division: "Cour", original: "Arrêt original", open_bger: "Ouvrir sur bger.ch",
    summary_de: "Zusammenfassung DE", summary_fr: "Résumé FR", text: "Texte de l'arrêt", history: "Historique",
    edit: "Modifier", edit_summary: "Modifier le résumé", adjust_score: "Ajuster le score", save: "Enregistrer", show_ai: "Afficher l'original IA", hide_ai: "Masquer l'original IA", edited_by: "modifié par", ai: "IA",
    no_summary: "Pas encore de résumé.", generate: "Résumer maintenant", no_text: "Texte intégral indisponible.", no_history: "Aucune modification manuelle.",
    h_score: "Score modifié", h_revert: "Score rétabli", h_summary_de: "Zusammenfassung DE modifiée", h_summary_fr: "Résumé FR modifié", h_status: "Statut",
    st_new: "nouveau", st_done: "traité", saved: "Enregistré", failed_action: "Non enregistré", err_key: "Clé d\u2019éditeur manquante ou incorrecte (⋯ → Nom/clé)", queued: "En cours …", done: "Terminé", failed: "Erreur",
    suva_party: "Suva partie", human_example: "Résumé original Suva", demo: "Démo",
    cite_missing: "Considérant introuvable dans le texte", cite_hint: "Aller au considérant dans le texte de l'arrêt",
  },
};

const store = {
  get(k, d) { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch {} },
};
const readSet = new Set((() => { try { return JSON.parse(store.get("lex.read", "[]")); } catch { return []; } })());
const saveRead = () => store.set("lex.read", JSON.stringify([...readSet]));

const state = {
  lang: store.get("suva.lang", "de"), editor: store.get("suva.editor", ""),
  scope: store.get("lex.scope", "new"), sort: store.get("lex.sort", "score"), dir: store.get("lex.dir", "desc"),
  minScore: parseInt(store.get("lex.min", "40"), 10), tag: "", cards: [], open: null, tab: null, editing: false, showAi: false, status: null,
};
const $ = (s) => document.querySelector(s);
const t = (k, ...a) => { const v = I18N[state.lang][k]; return typeof v === "function" ? v(...a) : v ?? k; };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const locale = () => (state.lang === "fr" ? "fr-CH" : "de-CH");
const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString(locale(), { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "");
const fmtDate = (d) => (d && /^\d{4}-\d{2}-\d{2}/.test(d) ? new Date(d.slice(0, 10)).toLocaleDateString(locale(), { day: "2-digit", month: "2-digit", year: "numeric" }) : d || "");
const band = (s) => (s >= 70 ? "hi" : s >= 40 ? "mid" : "lo");
const titleOf = (c) => (state.lang === "fr" ? c.title_fr : c.title_de) || c.subject || c.docket;
const whyOf = (c) => (state.lang === "fr" ? c.explanation_fr : c.explanation_de) || "";
const isDone = (c) => c.status === "done";
const readOnly = () => !!state.status?.read_only;

/* ---------- API (live FastAPI, or static JSON export on GitHub Pages; see docs/API.md) ---------- */
const STATIC = location.hostname.endsWith("github.io") || window.LEX_STATIC === true || location.protocol === "file:";
const staticUrl = (p) => p.replace(/^\/api\//, "api/").replace(/%2F/gi, "_") + ".json";
async function api(path, opts = {}) {
  if (STATIC) {
    if (opts.method && opts.method !== "GET") throw new Error(t("read_only"));
    const r = await fetch(staticUrl(path));
    if (!r.ok) throw new Error(`${r.status} ${path}`);
    const data = await r.json();
    if (path === "/api/status") Object.assign(data, { read_only: true, static: true, jobs: data.jobs || {} });
    return data;
  }
  // API_BASE: the page's own path prefix, so the UI also works behind a reverse-proxy prefix
  // (https://api.robotross.art/lex/ -> "/lex"). Override with window.LEX_API_BASE (e.g. from GitHub Pages).
  const API_BASE = window.LEX_API_BASE ?? location.pathname.replace(/\/[^/]*$/, "");
  const send = () => {
    const headers = { "Content-Type": "application/json" };
    const key = store.get("lex.key", "");
    if (key && opts.method && opts.method !== "GET") headers["X-Lex-Key"] = key;  // hosted API: writes need a key
    return fetch(API_BASE + path, { ...opts, headers });
  };
  let r = await send();
  if (r.status === 401 && opts.method && opts.method !== "GET") {
    if (await askEditor(true)) r = await send();
  }
  if (!r.ok) { const e = new Error(await r.text()); e.status = r.status; throw e; }
  return r.json();
}
function errText(e) {
  if (e?.status === 401) return t("err_key");
  if (e?.status === 403) return t("read_only");
  let m = e?.message || String(e); try { m = JSON.parse(m).detail || m; } catch (_) {}
  return String(m).slice(0, 160);
}
function toast(msg) { const el = $("#toast"); el.textContent = msg; el.classList.add("show"); clearTimeout(toast.h); toast.h = setTimeout(() => el.classList.remove("show"), 2400); }

/* ---------- editor name + optional server key (no accounts; kept in this browser) ---------- */
function askEditor(focusKey = false) {
  return new Promise((resolve) => {
    const dlg = $("#nameDlg");
    $("#nameInput").value = state.editor; $("#keyInput").value = store.get("lex.key", "");
    $("#keyField").hidden = STATIC || !(state.status?.editor_key_required || focusKey);
    dlg.onclose = () => {
      if (dlg.returnValue === "ok") {
        const v = $("#nameInput").value.trim(); if (v) { state.editor = v; store.set("suva.editor", v); }
        const k = $("#keyInput").value.trim(); if (!$("#keyField").hidden) store.set("lex.key", k);
        renderChrome();
      }
      resolve(dlg.returnValue === "ok" && !!state.editor);
    };
    dlg.showModal();
    (focusKey ? $("#keyInput") : $("#nameInput")).focus();
  });
}
async function requireName() {
  if (readOnly()) { toast(t("read_only")); return null; }
  return state.editor || ((await askEditor()) ? state.editor : null);
}

/* ---------- chrome ---------- */
function renderChrome() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => (el.placeholder = t(el.dataset.i18nPlaceholder)));
  document.querySelectorAll("[data-lang]").forEach((b) => b.classList.toggle("on", b.dataset.lang === state.lang));
  document.querySelectorAll("#scope [data-scope]").forEach((b) => b.classList.toggle("on", b.dataset.scope === state.scope));
  $("#sortBy").value = state.sort;
  const lines = store.get("lex.whyLines", "4");
  document.documentElement.style.setProperty("--why-lines", lines === "0" ? "999" : lines);
  document.querySelectorAll("#whyLines [data-lines]").forEach((b) => b.classList.toggle("on", b.dataset.lines === lines));
  document.querySelectorAll("#mhead [data-sort]").forEach((b) => { b.classList.toggle("on", b.dataset.sort === state.sort); b.classList.toggle("asc", state.dir === "asc"); });
  $("#sortDir").textContent = state.dir === "desc" ? "↓" : "↑"; $("#sortDir").title = state.dir === "desc" ? t("desc") : t("asc");
  $("#editorBtn").textContent = t("editor_set", state.editor);
  $("#addBtn").hidden = readOnly(); $("#editorBtn").hidden = readOnly();
  $("#minScore").value = state.minScore; $("#minScoreOut").textContent = state.minScore;
  if (state.status) $("#modelInfo").textContent = (readOnly() ? t("read_only") + " · " : "") + t("model") + ": " + (state.status.mock ? t("mock") : state.status.model);
  document.title = t("app_title");
}

function renderTagFilter() {
  const freq = {}, label = {};
  state.cards.forEach((c) => tagsOf(c).forEach((g) => { freq[g.key] = (freq[g.key] || 0) + 1; label[g.key] = label[g.key] || g.label; }));
  const tags = Object.keys(freq).sort((a, b) => freq[b] - freq[a] || label[a].localeCompare(label[b]));
  $("#tagFilter").innerHTML = `<option value="">${t("all_keywords")}</option>` +
    tags.map((g) => `<option value="${esc(g)}" ${g === state.tag ? "selected" : ""}>${esc(label[g])} (${freq[g]})</option>`).join("");
}

/* tags: DE is the key (filter works across languages); FR label when triage delivered a 1:1 translation */
function tagsOf(c) {
  const de = c.tags || [], fr = c.tags_fr || [];
  return de.map((k, i) => ({ key: k, label: state.lang === "fr" && fr.length === de.length ? fr[i] : k }));
}

/* ---------- list ---------- */
function visible() {
  const q = $("#search").value.trim().toLowerCase();
  const rows = state.cards.filter((c) => {
    if (state.scope === "new" && isDone(c)) return false;
    if (state.scope === "done" && !isDone(c)) return false;
    if ((c.score ?? 0) < state.minScore && c.slug !== state.open) return false;
    if (state.tag && !(c.tags || []).includes(state.tag)) return false;
    if (q && ![c.docket, c.title_de, c.title_fr, c.explanation_de, c.explanation_fr, c.subject, ...(c.tags || []), ...(c.tags_fr || [])].join(" ").toLowerCase().includes(q)) return false;
    return true;
  });
  const key = {
    score: (c) => c.score ?? -1, title: (c) => titleOf(c).toLowerCase(), docket: (c) => c.docket,
    date: (c) => c.decision_date || c.publication_date || "", edited: (c) => c.last_edit_at || "",
  }[state.sort];
  const dir = state.dir === "desc" ? -1 : 1;
  rows.sort((a, b) => { const x = key(a), y = key(b); return (x < y ? -1 : x > y ? 1 : 0) * dir || a.docket.localeCompare(b.docket); });
  return rows;
}

function rowHtml(c) {
  const s = c.score ?? 0;
  const overridden = c.score_override !== null && c.score_override !== undefined;
  const unread = !readSet.has(c.slug) && !isDone(c);
  const tip = `${t("score_ai")}: ${c.ai_score ?? "–"}${overridden ? ` · ${t("score_human")}: ${c.score_override} (${c.override_by || ""})` : ""} · ${t("edit_score")}`;
  const edited = c.last_editor ? `<span class="edited">✎ ${esc(c.last_editor)} · ${esc(fmtTime(c.last_edit_at))}</span>` : "";
  return `<li data-slug="${esc(c.slug)}" class="mrow ${c.slug === state.open ? "sel" : ""} ${unread ? "unread" : ""} ${c.last_editor ? "is-edited" : ""}">
    <div class="m-dot">${unread ? '<span class="dot"></span>' : ""}</div>
    <div class="m-score ${overridden ? "manual" : ""}" data-score title="${esc(tip)}">
      <span class="n">${c.score ?? "–"}</span>
      <span class="level"><i class="${band(s)}" style="width:${s}%"></i></span>
    </div>
    <div class="m-main">
      <div class="m-top"><span class="t">${esc(titleOf(c))}</span><span class="m-date">${esc(fmtDate(c.decision_date || c.publication_date))}</span></div>
      <div class="m-sub">${esc(c.docket)}${c.source === "demo" ? ` · ${t("demo")}` : ""}</div>
      <p class="why">${esc(whyOf(c))}</p>
      <div class="m-foot"><div class="tags">${c.suva_party ? `<span class="tag">${t("suva_party")}</span>` : ""}${tagsOf(c).map((g) => `<span class="tag">#${esc(g.label)}</span>`).join("")}</div>${edited}</div>
    </div>
    <div class="m-act">${readOnly() ? "" : `<button class="act" data-act="${isDone(c) ? "reopen" : "done"}" title="${isDone(c) ? t("reopen") : t("mark_done")}">${isDone(c) ? "↺" : "✓"}</button>`}</div>
  </li>`;
}

function renderList() {
  const rows = visible();
  $("#rows").innerHTML = rows.map(rowHtml).join("");
  const inScope = state.cards.filter((c) => (state.scope === "all" ? true : state.scope === "done" ? isDone(c) : !isDone(c))).length;
  $("#listMeta").textContent = t("n_shown", rows.length, inScope);
  const nNew = state.cards.filter((c) => !isDone(c) && !readSet.has(c.slug) && (c.score ?? 0) >= state.minScore).length;
  $("#cNew").textContent = nNew || ""; $("#cDone").textContent = state.cards.filter(isDone).length || "";
  $("#empty").hidden = rows.length > 0; $("#empty").textContent = state.scope === "new" ? t("empty_new") : t("empty");
}

async function load() {
  state.cards = await api("/api/judgements");
  renderTagFilter(); renderList();
  if (state.open) renderPanel();
}

/* ---------- score edit in the cell ---------- */
async function editScore(slug, el) {
  if (!(await requireName())) return;
  const c = state.cards.find((x) => x.slug === slug);
  el.innerHTML = `<input type="number" min="0" max="100" value="${c.score ?? 0}">`;
  const inp = el.querySelector("input"); inp.focus(); inp.select();
  let done = false;
  const commit = async (save) => {
    if (done) return; done = true;
    const v = Math.max(0, Math.min(100, parseInt(inp.value, 10)));
    if (save && !Number.isNaN(v) && v !== c.score) {
      el.classList.add("manual"); el.innerHTML = `<span class="n">${v}</span><span class="level"><i class="${band(v)}" style="width:${v}%"></i></span>`;
      await setScore(slug, v);
    } else { await pointerReleased(); renderList(); if (state.open) renderPanel(); }
  };
  inp.addEventListener("keydown", (e) => { e.stopPropagation(); if (e.key === "Enter") commit(true); if (e.key === "Escape") commit(false); });
  inp.addEventListener("blur", () => commit(true));
  inp.addEventListener("click", (e) => e.stopPropagation());
}
async function setScore(slug, score) {
  try {
    await api(`/api/judgements/${encodeURIComponent(slug)}/score`, { method: "PUT", body: JSON.stringify({ score, editor: state.editor }) });
    toast(t("saved"));
  } catch (e) { toast(`${t("failed_action")}: ${errText(e)}`); }
  await pointerReleased(); await load();
}
// Re-rendering the list between mousedown and click swallows the click; wait until the pointer is up.
let pointerDown = false;
document.addEventListener("pointerdown", () => (pointerDown = true), true);
document.addEventListener("pointerup", () => setTimeout(() => (pointerDown = false)), true);
const pointerReleased = () => new Promise((r) => (function wait() { pointerDown ? setTimeout(wait, 30) : setTimeout(r); })());

/* ---------- done / reopen (team-wide), read (this browser) ---------- */
async function setDone(slug, done) {
  if (!(await requireName())) return;
  await api(`/api/judgements/${encodeURIComponent(slug)}/status`, { method: "PUT", body: JSON.stringify({ status: done ? "done" : "new", editor: state.editor }) });
  toast(done ? t("moved_done") : t("moved_new"));
  if (done && state.scope === "new" && state.open === slug) {
    const rows = visible(); const i = rows.findIndex((c) => c.slug === slug);
    const next = rows[i + 1] || rows[i - 1];
    await load(); next ? openPanel(next.slug) : closePanel();
  } else await load();
}
function markRead(slug) { if (!readSet.has(slug)) { readSet.add(slug); saveRead(); } }

/* ---------- citations: "(Erw. 4.2)" / "(consid. 5.2)" link to the consideration in the original text ---------- */
const CITE_RE = /\b(Erw(?:ägung(?:en)?)?\.?|E\.|consid(?:érants?)?\.?|cons\.|considérants?)\s*(\d+(?:\.\d+)*)/g;
function linkCitations(text) {
  return esc(text).replace(CITE_RE, (m, word, num) => `<a href="#" class="cite" data-erw="${num}" title="${t("cite_hint")}">${word} ${num}</a>`);
}
function renderOriginal(text) {
  const lines = text.split("\n");
  let started = false;
  const head = /^(Erwägungen?|Erwägung|Considérant en droit|Considérants?|Considerando in diritto|Diritto)\s*:?\s*$/i;
  const seen = new Set(); const out = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!started && head.test(line.trim())) { started = true; out.push(`<b>${esc(line)}</b>`); continue; }
    const m = started && line.match(/^\s*(\d+(?:\.\d+)*)\.?(?:\s|$)/);
    if (m && !seen.has(m[1])) {
      seen.add(m[1]);
      const body = /^\s*[\d.]+\s*$/.test(line) && i + 1 < lines.length ? line + "\n" + lines[++i] : line;  // bare "5.2." line joins its paragraph
      out.push(`<span class="erw-anchor" id="erw-${m[1]}">${esc(body)}</span>`);
    } else out.push(esc(line));
  }
  return out.join("\n");
}

// Same "Erw. N" anchors for the formatted original: number the paragraphs after the "Erwägungen" heading.
function anchorHtml(root) {
  if (!root) return;
  const head = /^(Erwägungen?|Considérant en droit|Considérants?|Considerando in diritto|Diritto)\s*:?\s*$/i;
  const blocks = [...root.querySelectorAll("p, div, li, td, h1, h2, h3, h4, h5, h6")].filter((el) => !el.querySelector("p, div, li, td"));
  let started = false; const seen = new Set();
  for (const el of blocks) {
    const txt = el.textContent.trim();
    if (!started) { if (head.test(txt)) started = true; continue; }
    const m = txt.match(/^(\d+(?:\.\d+)*)\.?(?:\s|$)/);
    if (m && !seen.has(m[1])) { seen.add(m[1]); el.id = "erw-" + m[1]; el.classList.add("erw-anchor"); }
  }
}

/* ---------- detail pane ---------- */
async function openPanel(slug) {
  state.open = slug; state.editing = false; state.showAi = false; state.tab = state.tab || "summary_" + state.lang;
  markRead(slug);
  $("#panel").hidden = false; renderList(); await renderPanel();
  const tr = document.querySelector(`#rows [data-slug="${CSS.escape(slug)}"]`); if (tr) tr.scrollIntoView({ block: "nearest" });
}
function closePanel() { state.open = null; $("#panel").hidden = true; renderList(); }

async function renderPanel() {
  const d = await api(`/api/judgements/${encodeURIComponent(state.open)}`);
  const a = d.assessment || {};
  const L = state.lang;
  const done = d.status === "done";
  $("#pDocket").textContent = [d.docket, fmtDate(d.decision_date || d.publication_date)].filter(Boolean).join(" · ");
  $("#pTitle").textContent = (L === "fr" ? a.title_fr : a.title_de) || d.subject || d.docket;
  $("#pDone").hidden = readOnly();
  $("#pDone").textContent = done ? "↺ " + t("reopen") : "✓ " + t("mark_done");
  $("#pDone").onclick = () => setDone(d.slug, !done);
  const overridden = a.score_override !== null && a.score_override !== undefined;
  const score = overridden ? a.score_override : a.ai_score;
  const tabs = ["summary_de", "summary_fr", "text", "history"];
  let html = `
    <div class="section"><h4>${t("relevance")}</h4>
      <div class="bigscore"><span class="n" id="pScoreN">${score ?? "–"}</span><span class="level"><i class="${band(score ?? 0)}" style="width:${score ?? 0}%"></i></span>
        <span class="muted">${t("score_ai")}: ${a.ai_score ?? "–"}${overridden ? ` · ${t("score_human")}: ${a.score_override} (${esc(a.override_by)}, ${esc(fmtTime(a.override_at))})` : ""}</span>
        ${readOnly() ? "" : `<button class="btn" id="scoreBtn">✎ ${t("adjust_score")}</button>`}
        ${overridden && !readOnly() ? `<button class="btn small" id="revertBtn">${t("revert")}</button>` : ""}</div>
      ${done && d.status_by ? `<p class="muted">${esc(t("done_by", d.status_by, fmtTime(d.status_at)))}</p>` : ""}</div>
    <div class="section"><h4>${t("why")}</h4><p>${esc(L === "fr" ? a.explanation_fr : a.explanation_de)}</p>
      <div class="tags">${a.suva_party ? `<span class="tag">${t("suva_party")}</span>` : ""}${tagsOf(a).map((g) => `<span class="tag">#${esc(g.label)}</span>`).join("")}</div></div>
    <div class="section"><h4>${t("details")}</h4><div class="kv">
      ${d.decision_date ? `<span class="muted">${t("decided")}</span><span>${esc(fmtDate(d.decision_date))}</span>` : ""}
      ${d.publication_date ? `<span class="muted">${t("published")}</span><span>${esc(fmtDate(d.publication_date))}</span>` : ""}
      ${d.division ? `<span class="muted">${t("division")}</span><span>${esc(d.division)}</span>` : ""}
      ${d.url ? `<span class="muted">${t("original")}</span><span><a href="${esc(d.url)}" target="_blank" rel="noopener">${t("open_bger")} ↗</a></span>` : ""}
    </div></div>
    <div class="tabs">${tabs.map((k) => `<button data-tab="${k}" class="${state.tab === k ? "on" : ""}">${t(k)}${k === "history" && d.history.length ? ` (${d.history.length})` : ""}</button>`).join("")}</div>
    <div class="section" id="tabBody">`;

  if (state.tab.startsWith("summary_")) {
    const lang = state.tab.slice(-2);
    const s = d.summaries[lang];
    if (!s) {
      html += `<p class="muted">${t("no_summary")}</p>`;
      if (d.text && !readOnly()) html += `<button class="btn primary" id="genBtn">${t("generate")}</button>`;
    } else if (state.editing) {
      html += `<textarea class="summary-edit" id="sumEdit">${esc(s.text)}</textarea>
        <div class="row"><button class="btn" id="cancelEdit">${t("cancel")}</button><button class="btn primary" id="saveEdit">${t("save")}</button></div>`;
    } else {
      const meta = s.edited_by ? `<span class="edited">✎ ${t("edited_by")} ${esc(s.edited_by)} · ${esc(fmtTime(s.edited_at))}</span>`
        : s.model === "suva-human-example" ? `<span class="tag">${t("human_example")}</span>` : `<span class="tag">${t("ai")} · ${esc(s.model)}</span>`;
      html += `<div class="sum-head"><div class="c-sub">${meta}</div>${readOnly() ? "" : `<button class="btn primary" id="editBtn">✎ ${t("edit_summary")}</button>`}</div>
        <div class="summary">${linkCitations(s.text)}</div>
        ${s.edited_by && s.ai_text ? `<div class="row"><button class="btn small" id="toggleAi">${state.showAi ? t("hide_ai") : t("show_ai")}</button></div>` : ""}
        ${state.showAi && s.ai_text ? `<div class="ai-orig">${linkCitations(s.ai_text)}</div>` : ""}`;
    }
  } else if (state.tab === "text") {
    // formatted original (cleaned server-side, see scraper._html_clean); plain text as fallback
    html += d.html ? `<div class="original-html" id="origHtml">${d.html}</div>`
      : d.text ? `<div class="original">${renderOriginal(d.text)}</div>` : `<p class="muted">${t("no_text")}</p>`;
  } else {
    const label = (h) => (h.field === "status" ? `${t("h_status")}: ${t("st_" + h.old_value)} → ${t("st_" + h.new_value)}`
      : t("h_" + h.field.replace("_score", "")) + (h.field.includes("score") ? `: ${esc(h.old_value)} → ${esc(h.new_value)}` : ""));
    html += d.history.length
      ? `<ul class="history">${d.history.map((h) => `<li><b>${esc(h.editor)}</b> · ${esc(fmtTime(h.at))} · ${label(h)}</li>`).join("")}</ul>`
      : `<p class="muted">${t("no_history")}</p>`;
  }
  html += `</div>`;
  $("#pBody").innerHTML = html;

  $("#pBody").querySelectorAll("[data-tab]").forEach((b) => (b.onclick = () => { state.tab = b.dataset.tab; state.editing = false; renderPanel(); }));
  $("#pBody").querySelectorAll(".cite").forEach((el) => (el.onclick = (e) => { e.preventDefault(); state.tab = "text"; state.pendingErw = el.dataset.erw; renderPanel(); }));
  if (state.tab === "text" && d.html) anchorHtml($("#origHtml"));
  if (state.tab === "text" && state.pendingErw) {
    const num = state.pendingErw; state.pendingErw = null;
    let el = null; for (let n = num; n && !el; n = n.includes(".") ? n.slice(0, n.lastIndexOf(".")) : "") el = document.getElementById("erw-" + n);
    if (el) { el.scrollIntoView({ behavior: "smooth", block: "center" }); el.classList.add("flash"); setTimeout(() => el.classList.remove("flash"), 2200); }
    else toast(t("cite_missing"));
  }
  const on = (id, fn) => { const el = document.getElementById(id); if (el) el.onclick = fn; };
  on("editBtn", async () => { if (await requireName()) { state.editing = true; renderPanel(); } });
  on("scoreBtn", () => editScore(d.slug, $("#pScoreN")));
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

/* ---------- add a ruling manually ---------- */
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

/* ---------- wiring ---------- */
function init() {
  renderChrome();
  document.querySelectorAll("[data-lang]").forEach((b) => (b.onclick = () => {
    state.lang = b.dataset.lang; store.set("suva.lang", state.lang);
    if (state.tab?.startsWith("summary_")) state.tab = "summary_" + state.lang;
    renderChrome(); renderTagFilter(); renderList(); if (state.open) renderPanel();
  }));
  document.querySelectorAll("#scope [data-scope]").forEach((b) => (b.onclick = () => { state.scope = b.dataset.scope; store.set("lex.scope", state.scope); renderChrome(); renderList(); }));
  $("#sortBy").onchange = (e) => {
    state.sort = e.target.value; state.dir = state.sort === "title" || state.sort === "docket" ? "asc" : "desc";
    store.set("lex.sort", state.sort); store.set("lex.dir", state.dir); renderChrome(); renderList();
  };
  document.querySelectorAll("#mhead [data-sort]").forEach((b) => (b.onclick = () => {
    if (state.sort === b.dataset.sort) state.dir = state.dir === "desc" ? "asc" : "desc";
    else { state.sort = b.dataset.sort; state.dir = state.sort === "title" ? "asc" : "desc"; }
    store.set("lex.sort", state.sort); store.set("lex.dir", state.dir); renderChrome(); renderList();
  }));
  // a failed save must never be silent (e.g. missing/wrong editor key on the hosted server)
  window.addEventListener("unhandledrejection", (e) => { toast(`${t("failed_action")}: ${errText(e.reason)}`); });
  $("#sortDir").onclick = () => { state.dir = state.dir === "desc" ? "asc" : "desc"; store.set("lex.dir", state.dir); renderChrome(); renderList(); };
  $("#minScore").oninput = (e) => { state.minScore = parseInt(e.target.value, 10); store.set("lex.min", String(state.minScore)); $("#minScoreOut").textContent = state.minScore; renderList(); };
  $("#tagFilter").onchange = (e) => { state.tag = e.target.value; renderList(); };
  $("#search").oninput = renderList;
  const menu = $("#menu"), menuBtn = $("#menuBtn");
  const setMenu = (open) => { menu.hidden = !open; menuBtn.setAttribute("aria-expanded", String(open)); };
  menuBtn.onclick = (e) => { e.stopPropagation(); setMenu(menu.hidden); };
  document.addEventListener("click", (e) => { if (!menu.hidden && !e.target.closest(".menu-wrap")) setMenu(false); });
  document.querySelectorAll("#whyLines [data-lines]").forEach((b) => (b.onclick = (e) => { e.stopPropagation(); store.set("lex.whyLines", b.dataset.lines); renderChrome(); }));
  $("#editorBtn").onclick = () => { setMenu(false); askEditor(); };
  $("#addBtn").onclick = () => {
    setMenu(false);
    const dlg = $("#addDlg"); $("#addInput").value = "";
    dlg.onclose = () => { const v = $("#addInput").value.trim(); if (dlg.returnValue === "ok" && v) startAdd(v); };
    dlg.showModal();
  };
  $("#closePanel").onclick = closePanel;
  $("#rows").addEventListener("click", (e) => {
    const tr = e.target.closest("[data-slug]"); if (!tr) return;
    const act = e.target.closest("[data-act]");
    if (act) { e.stopPropagation(); setDone(tr.dataset.slug, act.dataset.act === "done"); return; }
    const sc = e.target.closest("[data-score]");
    if (sc && !readOnly()) { e.stopPropagation(); editScore(tr.dataset.slug, sc); return; }
    openPanel(tr.dataset.slug);
  });
  // keyboard like Mail: ↑/↓ move, Esc closes, E marks done / reopens
  document.addEventListener("keydown", (e) => {
    if (document.querySelector("dialog[open]") || /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName)) return;
    if (e.key === "Escape" && state.open) closePanel();
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      const rows = visible(); if (!rows.length) return;
      const i = rows.findIndex((c) => c.slug === state.open);
      const n = e.key === "ArrowDown" ? Math.min(rows.length - 1, i + 1) : Math.max(0, i - 1);
      e.preventDefault(); openPanel(rows[i < 0 ? 0 : n].slug);
    }
    if ((e.key === "e" || e.key === "E") && state.open && !readOnly()) {
      const c = state.cards.find((x) => x.slug === state.open); if (c) setDone(c.slug, !isDone(c));
    }
  });
  api("/api/status").then((s) => { state.status = s; renderChrome(); renderList(); }).catch(() => {});
  load();
}
init();
