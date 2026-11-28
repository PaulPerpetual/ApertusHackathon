/* Urteilsradar: one macOS-style list of rulings (Neu · Alle · Erledigt), sortable columns, filters,
   detail pane, human score overrides and summary edits with simple name attribution. */
const I18N = {
  de: {
    month_all: "Alle Monate", m04: "April 2026", m05: "Mai 2026", m06: "Juni 2026",
    pub_label: "nach Suva-Publikation (≈ +33 Tage)", pub_hint: "Monat nach geschätzter Publikation der Suva-Zusammenfassung: Entscheiddatum + 33 Tage (Median der Suva-Seiten 2025/26, Spanne 17–76 Tage). Ohne Häkchen: Entscheiddatum.",
    hitlist_btn: "Trefferliste", info_btn: "Info", info_close: "Verstanden",
    app_title: "Urteilsradar", search: "Suchen", scope_new: "Neu", scope_all: "Alle", scope_done: "Erledigt", scope_rejected: "Nicht relevant", scope_border: "Grenzfälle", border: "Grenzfall", border_hint: "Apertus ist unsicher, ob diese Urteile für die Suva relevant sind.", border_hint1: "Apertus ist unsicher, eine Juristin sollte es ansehen.", promote: "Bestätigen", promoted: "Als relevant bestätigt",
    min_relevance: "Relevanz ab", sort_by: "Sortieren nach", asc: "Aufsteigend", desc: "Absteigend", keyword: "Schlagwort", all_keywords: "Alle Schlagworte", remove: "Entfernen", filter: "Filter", period: "Zeitraum", keywords: "Schlagworte", show: "Anzeigen", show_done: "Erledigte", show_rejected: "Nicht relevante", reset_all: "Zurücksetzen", chip_min: (n) => `Relevanz ab ${n}`, chip_pub: "nach Publikation", chip_done: "+ Erledigte", chip_rej: "+ Nicht relevante",
    preview_lines: "Begründung in der Liste", all_lines: "alle", col_relevance: "Relevanz", col_ruling: "Urteil", col_title: "Titel", col_docket: "Nummer", col_date: "Entscheiddatum", col_tags: "Schlagworte", col_edited: "Bearbeitet",
    n_shown: (n, t) => `${n} von ${t}`, empty_new: "Keine neuen Urteile über dieser Relevanzschwelle.", empty: "Keine Urteile gefunden.",
    add: "Urteil zusammenfassen", add_title: "Weiteres Urteil zusammenfassen", add_hint: "Geschäftsnummer (z.B. 8C_145/2025) oder Link von bger.ch",
    start: "Zusammenfassen", cancel: "Abbrechen", who: "Wer bearbeitet?", who_hint: "Ihr Name wird bei Änderungen angezeigt. Keine Anmeldung nötig.",
    name: "Name", key: "Editor-Schlüssel (nur für den Server)", editor_set: (n) => n ? `Name: ${n} …` : "Name festlegen …",
    model: "Modell", mock: "Mock (kein LLM)", read_only: "Nur lesen",
    mark_done: "Freigeben", reopen: "Freigabe zurückziehen", done_by: (n, at) => `Freigegeben von ${n}, ${at}`, approved: "Freigegeben", v_before: "Vorher", v_after: "Nachher", v_restore: "Diese Fassung wiederherstellen", v_show: "Fassungen ansehen", v_restored: "Fassung wiederhergestellt (im Verlauf protokolliert)", expand: "Gross anzeigen", shrink: "Seitlich anzeigen", moved_done: "Freigegeben (weiter unter «Alle»)", moved_new: "Wieder geöffnet", reject: "Nicht relevant", moved_rejected: "Als nicht relevant aus der Liste genommen", rejected_by: (n, at) => `Als nicht relevant markiert von ${n}, ${at}`, restore: "Wieder aufnehmen",
    relevance: "Relevanz", manual: "manuell", score_ai: "KI-Score", score_human: "Manuell", revert: "KI-Score wiederherstellen", edit_score: "Klicken zum Ändern",
    why: "Begründung", details: "Details", decided: "Entscheid", published: "Publiziert", division: "Abteilung", original: "Originalurteil", open_bger: "Auf bger.ch öffnen",
    summary_de: "Zusammenfassung DE", summary_fr: "Résumé FR", text: "Urteilstext", history: "Verlauf",
    edit: "Bearbeiten", subject_hint: "Gegenstand laut Bundesgericht", subject: "Gegenstand", add_tag: "Schlagwort hinzufügen …", h_tags: "Schlagworte geändert", notes: "Notizen", no_notes: "Noch keine Notizen.", note_ph: "Notiz für das Team …", add_note: "Notiz hinzufügen", delete: "Löschen", h_note: "Notiz hinzugefügt", h_note_deleted: "Notiz gelöscht", h_explanation_de: "Begründung DE bearbeitet", h_explanation_fr: "Begründung FR bearbeitet", save: "Speichern", show_ai: "KI-Original anzeigen", hide_ai: "KI-Original ausblenden", edited_by: "bearbeitet von", ai: "KI",
    no_summary: "Noch keine Zusammenfassung.", generate: "Jetzt zusammenfassen", no_text: "Volltext nicht verfügbar.", no_history: "Keine manuellen Änderungen.",
    h_score: "Score geändert", h_revert: "Score zurückgesetzt", h_summary_de: "Zusammenfassung DE bearbeitet", h_summary_fr: "Résumé FR bearbeitet", h_status: "Status",
    st_new: "neu", st_done: "freigegeben", st_rejected: "nicht relevant", saved: "Gespeichert", failed_action: "Nicht gespeichert", err_key: "Editor-Schlüssel fehlt oder ist falsch (⋯ → Name/Schlüssel)", queued: "Wird verarbeitet …", done: "Fertig", failed: "Fehler",
    suva_party: "Suva Partei", human_example: "Suva-Originalzusammenfassung", demo: "Demo",
    cite_missing: "Erwägung im Volltext nicht gefunden", cite_hint: "Zur Erwägung im Urteilstext springen",
  },
  fr: {
    month_all: "Tous les mois", m04: "avril 2026", m05: "mai 2026", m06: "juin 2026",
    pub_label: "selon publication Suva (≈ +33 jours)", pub_hint: "Mois selon la publication estimée du résumé Suva: date de décision + 33 jours (médiane des pages Suva 2025/26, 17–76 jours). Sans coche: date de décision.",
    hitlist_btn: "Liste des résultats", info_btn: "Info", info_close: "Compris",
    app_title: "Radar des arrêts", search: "Rechercher", scope_new: "Nouveaux", scope_all: "Tous", scope_done: "Traités", scope_rejected: "Non pertinents", scope_border: "Cas limites", border: "Cas limite", border_hint: "Apertus n’est pas sûr que ces arrêts soient pertinents pour la Suva.", border_hint1: "Apertus n’est pas sûr, un juriste devrait l’examiner.", promote: "Confirmer", promoted: "Confirmé comme pertinent",
    min_relevance: "Pertinence dès", sort_by: "Trier par", asc: "Croissant", desc: "Décroissant", keyword: "Mot-clé", all_keywords: "Tous les mots-clés", remove: "Retirer", filter: "Filtre", period: "Période", keywords: "Mots-clés", show: "Afficher", show_done: "Traités", show_rejected: "Non pertinents", reset_all: "Réinitialiser", chip_min: (n) => `Pertinence dès ${n}`, chip_pub: "selon publication", chip_done: "+ traités", chip_rej: "+ non pertinents",
    preview_lines: "Justification dans la liste", all_lines: "tout", col_relevance: "Pertinence", col_ruling: "Arrêt", col_title: "Titre", col_docket: "Numéro", col_date: "Date de l\u2019arrêt", col_tags: "Mots-clés", col_edited: "Modifié",
    n_shown: (n, t) => `${n} sur ${t}`, empty_new: "Aucun nouvel arrêt au-dessus de ce seuil.", empty: "Aucun arrêt trouvé.",
    add: "Résumer un arrêt", add_title: "Résumer un autre arrêt", add_hint: "Numéro de dossier (p.ex. 8C_145/2025) ou lien bger.ch",
    start: "Résumer", cancel: "Annuler", who: "Qui modifie ?", who_hint: "Votre nom s'affiche lors des modifications. Pas d'inscription.",
    name: "Nom", key: "Clé d'éditeur (serveur uniquement)", editor_set: (n) => n ? `Nom : ${n} …` : "Définir le nom …",
    model: "Modèle", mock: "Fictif (sans LLM)", read_only: "Lecture seule",
    mark_done: "Valider", reopen: "Retirer la validation", done_by: (n, at) => `Validé par ${n}, ${at}`, approved: "Validé", v_before: "Avant", v_after: "Après", v_restore: "Restaurer cette version", v_show: "voir les versions", v_restored: "Version restaurée (consignée dans l’historique)", expand: "Agrandir", shrink: "Afficher sur le côté", moved_done: "Validé (toujours sous « Tous »)", moved_new: "Rouvert", reject: "Non pertinent", moved_rejected: "Retiré de la liste comme non pertinent", rejected_by: (n, at) => `Marqué non pertinent par ${n}, ${at}`, restore: "Réintégrer",
    relevance: "Pertinence", manual: "manuel", score_ai: "Score IA", score_human: "Manuel", revert: "Rétablir le score IA", edit_score: "Cliquer pour modifier",
    why: "Justification", details: "Détails", decided: "Décision", published: "Publié", division: "Cour", original: "Arrêt original", open_bger: "Ouvrir sur bger.ch",
    summary_de: "Zusammenfassung DE", summary_fr: "Résumé FR", text: "Texte de l'arrêt", history: "Historique",
    edit: "Modifier", subject_hint: "Objet selon le Tribunal fédéral", subject: "Objet", add_tag: "Ajouter un mot-clé …", h_tags: "Mots-clés modifiés", notes: "Notes", no_notes: "Pas encore de notes.", note_ph: "Note pour l\u2019équipe …", add_note: "Ajouter une note", delete: "Supprimer", h_note: "Note ajoutée", h_note_deleted: "Note supprimée", h_explanation_de: "Justification DE modifiée", h_explanation_fr: "Justification FR modifiée", save: "Enregistrer", show_ai: "Afficher l'original IA", hide_ai: "Masquer l'original IA", edited_by: "modifié par", ai: "IA",
    no_summary: "Pas encore de résumé.", generate: "Résumer maintenant", no_text: "Texte intégral indisponible.", no_history: "Aucune modification manuelle.",
    h_score: "Score modifié", h_revert: "Score rétabli", h_summary_de: "Zusammenfassung DE modifiée", h_summary_fr: "Résumé FR modifié", h_status: "Statut",
    st_new: "nouveau", st_done: "validé", st_rejected: "non pertinent", saved: "Enregistré", failed_action: "Non enregistré", err_key: "Clé d\u2019éditeur manquante ou incorrecte (⋯ → Nom/clé)", queued: "En cours …", done: "Terminé", failed: "Erreur",
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
  minScore: parseInt(store.get("lex.min", "40"), 10), tags: [], cards: [], open: null, tab: null, editing: false, showAi: false, status: null,
};
const $ = (s) => document.querySelector(s);
const t = (k, ...a) => { const v = I18N[state.lang][k]; return typeof v === "function" ? v(...a) : v ?? k; };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const locale = () => (state.lang === "fr" ? "fr-CH" : "de-CH");
const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString(locale(), { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "");
const fmtDate = (d) => (d && /^\d{4}-\d{2}-\d{2}/.test(d) ? new Date(d.slice(0, 10)).toLocaleDateString(locale(), { day: "2-digit", month: "2-digit", year: "numeric" }) : d || "");
const band = (s) => (s >= 70 ? "hi" : s >= 40 ? "mid" : "lo");
const titleOf = (c) => (state.lang === "fr" ? c.title_fr : c.title_de) || c.subject || c.docket;
const BORDER_PREFIX = /^\s*(Grenzfall|Cas limite)\s*[–:-]\s*/i;  // finalize --tiers prefixes the Begründung; the badge says it already
const whyOf = (c) => ((state.lang === "fr" ? c.explanation_fr : c.explanation_de) || "").replace(BORDER_PREFIX, "");
const isDone = (c) => c.status === "done";
const isRejected = (c) => c.status === "rejected";
const isOpen = (c) => !isDone(c) && !isRejected(c);
// "Grenzfälle" (tier 2, pass-4 review, docs/API.md): shown at the bottom of Neu/Alle, like Junk in Mail.
// "Bestätigen" (human score) takes a ruling out; "Nicht relevant" rejects it.
const tierOf = (c) => c.tier ?? c.assessment?.tier;
const isBorder = (c) => tierOf(c) === 2 && (c.score_override ?? c.assessment?.score_override) == null && isOpen(c);
// Erledigt / Nicht relevant are no scopes of their own any more: done rulings stay in "Alle",
// rejected ones come back with the filter "Nicht relevante anzeigen".
const inScopeOf = (c) => (state.scope === "border" ? isBorder(c)
  : isOpen(c) || (state.scope === "all" && isDone(c)) || (state.showRej && isRejected(c)));
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


/* ---------- Info dialog: explains the UI (for every user, DAU-proof) ---------- */
const INFO = {
  de: `<h3>So funktioniert das Urteilsradar</h3>
    <p>Apertus (Swiss AI) sichtet alle Bundesgerichtsurteile vom 1.4.–30.6.2026, wählt die für die Suva relevanten aus,
    ordnet sie nach Wichtigkeit und fasst sie auf Deutsch und Französisch zusammen.</p>
    <h4>Relevanz</h4>
    <p>Der Score (0–100) zeigt, wie wichtig ein Urteil für die Praxis der Suva ist; die Liste ist danach sortiert,
    das wichtigste Urteil steht oben und ist beim Öffnen bereits ausgewählt. Die <b>Begründung</b> sagt in einem Satz,
    welche Rechtsfrage entschieden wurde und warum das für die Suva zählt.</p>
    <h4>Grenzfälle</h4>
    <p>Urteile, bei denen Apertus unsicher ist (oft Invaliden- oder Verfahrensrecht, das auch für die Unfallversicherung
    gelten kann). Sie stehen unter den klar relevanten Urteilen, tragen das gelbe Etikett <b>Grenzfall</b> und sind im Reiter
    „Grenzfälle" gesammelt. Lieber ein Grenzfall zu viel als ein verpasstes Urteil: bitte kurz prüfen.</p>
    <h4>Neu · Freigegeben · Nicht relevant</h4>
    <ul><li><b>Neu</b>: noch nicht bearbeitet.</li>
      <li><b>Freigeben</b>: geprüft und in Ordnung (Taste E). Das Urteil trägt dann «✓ Freigegeben von Name» mit Datum, verschwindet aus «Neu» und bleibt unter «Alle». Gilt für das ganze Team; im Verlauf lässt sich jede frühere Fassung ansehen und wiederherstellen.</li>
      <li><b>Nicht relevant</b>: nimmt das Urteil von der Trefferliste. Über Filter → „Nicht relevante anzeigen" wieder sichtbar und mit einem Klick wiederherstellbar.</li></ul>
    <h4>Bearbeiten</h4>
    <p>„Bearbeiten" im Detailbereich öffnet Score, Begründung und beide Zusammenfassungen zur Korrektur. Jede Änderung wird
    mit Ihrem Namen gespeichert und im Verlauf protokolliert; der ursprüngliche KI-Text bleibt abrufbar.
    Beim ersten Bearbeiten werden Name und Editor-Schlüssel abgefragt.</p>
    <h4>Trefferliste</h4>
    <p>Der Knopf <b>Trefferliste</b> zeigt alle ausgewählten Urteile mit Rang und Kategorie (normal / Grenzfall), zum
    Kopieren oder als CSV. Ihre Entscheide hier wirken sofort dort.</p>
    <h4>Verweise</h4>
    <p>„(E. 4.2)" in einer Zusammenfassung springt direkt zur Erwägung im Originalurteil.</p>`,
  fr: `<h3>Fonctionnement du radar des arrêts</h3>
    <p>Apertus (Swiss AI) examine tous les arrêts du Tribunal fédéral du 1.4 au 30.6.2026, sélectionne ceux qui sont
    pertinents pour la Suva, les classe par importance et les résume en allemand et en français.</p>
    <h4>Pertinence</h4>
    <p>Le score (0–100) indique l'importance d'un arrêt pour la pratique de la Suva; la liste est triée ainsi, l'arrêt le
    plus important figure en tête et est déjà sélectionné à l'ouverture. La <b>justification</b> indique en une phrase la
    question juridique tranchée et pourquoi elle compte pour la Suva.</p>
    <h4>Cas limites</h4>
    <p>Arrêts pour lesquels Apertus hésite (souvent assurance-invalidité ou procédure pouvant aussi valoir pour
    l'assurance-accidents). Ils figurent sous les arrêts clairement pertinents, portent l’étiquette jaune <b>Cas limite</b> et
    sont regroupés dans l'onglet « Cas limites ». Mieux vaut un cas limite de trop qu'un arrêt manqué: merci de vérifier.</p>
    <h4>Nouveau · Validé · Non pertinent</h4>
    <ul><li><b>Nouveau</b>: pas encore traité.</li>
      <li><b>Valider</b>: vérifié et en ordre (touche E). L'arrêt porte alors « ✓ Validé par nom » avec la date, disparaît de « Nouveaux » et reste sous « Tous ». Vaut pour toute l'équipe ; l'historique permet de consulter et de restaurer chaque version antérieure.</li>
      <li><b>Non pertinent</b>: retire l'arrêt de la liste des résultats. Visible via Filtre → « Non pertinents », restaurable en un clic.</li></ul>
    <h4>Modifier</h4>
    <p>« Modifier » dans le panneau de détail permet de corriger le score, la justification et les deux résumés. Chaque
    modification est enregistrée avec votre nom et historisée; le texte original de l'IA reste disponible. Lors de la
    première modification, votre nom et votre clé d'éditeur sont demandés.</p>
    <h4>Liste des résultats</h4>
    <p>Le bouton <b>Liste des résultats</b> affiche tous les arrêts retenus avec rang et catégorie (normal / cas limite), à copier
    ou en CSV. Vos décisions ici s'y appliquent immédiatement.</p>
    <h4>Renvois</h4>
    <p>« (consid. 4.2) » dans un résumé mène directement au considérant de l'arrêt original.</p>`,
};
function openInfo() { $("#infoBody").innerHTML = INFO[state.lang] || INFO.de; $("#infoDlg").showModal(); }

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
  const ms = $("#monthSel");
  if (ms) {
    ms.innerHTML = [["", "month_all"], ["2026-04", "m04"], ["2026-05", "m05"], ["2026-06", "m06"]]
      .map(([v, k]) => `<option value="${v}">${t(k)}</option>`).join("");
    ms.value = state.month;
  }
  if ($("#pubToggle")) { $("#pubToggle").checked = !!state.byPublication; $("#pubLabel").textContent = t("pub_label"); $("#pubLabel").parentElement.title = t("pub_hint"); }
  document.querySelectorAll("[data-i18n]").forEach((el) => (el.textContent = t(el.dataset.i18n)));
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => (el.placeholder = t(el.dataset.i18nPlaceholder)));
  document.querySelectorAll("[data-lang]").forEach((b) => b.classList.toggle("on", b.dataset.lang === state.lang));
  document.querySelectorAll("#scope [data-scope]").forEach((b) => b.classList.toggle("on", b.dataset.scope === state.scope));
  const lines = store.get("lex.whyLines", "4");
  document.documentElement.style.setProperty("--why-lines", lines === "0" ? "999" : lines);
  document.querySelectorAll("#whyLines [data-lines]").forEach((b) => b.classList.toggle("on", b.dataset.lines === lines));
  document.querySelectorAll("#mhead [data-sort]").forEach((b) => { b.classList.toggle("on", b.dataset.sort === state.sort); b.classList.toggle("asc", state.dir === "asc"); });
  $("#editorBtn").textContent = t("editor_set", state.editor);
  $("#addBtn").hidden = readOnly(); $("#editorBtn").hidden = readOnly();
  $("#minScore").value = state.minScore; $("#minScoreOut").textContent = state.minScore;
  if (state.status) $("#modelInfo").textContent = (readOnly() ? t("read_only") + " · " : "") + t("model") + ": " + (state.status.mock ? t("mock") : state.status.model);
  document.title = t("app_title");
}

function renderTagFilter() {
  // several keywords combine with OR: a ruling shows if it carries any of them; counts are per keyword over all rulings
  const freq = {}, label = {};
  state.cards.forEach((c) => tagsOf(c).forEach((g) => { label[g.key] = label[g.key] || g.label; }));
  state.cards.forEach((c) => tagsOf(c).forEach((g) => { if (!state.tags.includes(g.key)) freq[g.key] = (freq[g.key] || 0) + 1; }));
  const tags = Object.keys(freq).sort((a, b) => freq[b] - freq[a] || label[a].localeCompare(label[b]));
  $("#tagFilter").innerHTML = `<option value="">${state.tags.length ? t("add_tag") : t("all_keywords")}</option>` +
    tags.map((g) => `<option value="${esc(g)}">${esc(label[g])} (${freq[g]})</option>`).join("");
  $("#tagChips").innerHTML = state.tags.map((k) =>
    `<button class="tag-chip" data-k="${esc(k)}" title="${esc(t("remove"))}">${esc(label[k] || k)} <span aria-hidden="true">×</span></button>`).join("");
  $("#tagChips").querySelectorAll("[data-k]").forEach((b) => (b.onclick = () => {
    state.tags = state.tags.filter((k) => k !== b.dataset.k); renderTagFilter(); renderList();
  }));
}
const hasTags = (c) => !state.tags.length || state.tags.some((k) => (c.tags || []).includes(k));

/* tags: DE is the key (filter works across languages); FR label when triage delivered a 1:1 translation */
function tagsOf(c) {
  const de = c.tags || [], fr = c.tags_fr || [];
  return de.map((k, i) => ({ key: k, label: state.lang === "fr" && fr.length === de.length ? fr[i] : k })).filter((g) => g.key !== "Grenzfall");  // shown as badge
}

// The court's own subject line ("Gegenstand"), as published, in the language of the ruling.
const subjectOf = (c) => (c.source === "demo" ? "" : String(c.subject || "").replace(/[\s,;]+$/, ""));

/* ---------- list ---------- */
const SUVA_LAG_DAYS = 33;  // median days from decision to Suva's summary page (Suva's Q4/Q1 list)
function monthOf(c) {  // "YYYY-MM" used by the month filter: decision date, or estimated Suva publication
  const d = c.decision_date || c.publication_date || "";
  if (!state.byPublication || !d) return d.slice(0, 7);
  const x = new Date(d + "T00:00:00Z"); x.setUTCDate(x.getUTCDate() + SUVA_LAG_DAYS);
  return x.toISOString().slice(0, 7);
}
function visible() {
  const q = $("#search").value.trim().toLowerCase();
  const rows = state.cards.filter((c) => {
    if (!inScopeOf(c)) return false;
    if (state.month && !monthOf(c).startsWith(state.month) && c.slug !== state.open) return false;
    if (!isBorder(c) && (c.score ?? 0) < state.minScore && c.slug !== state.open) return false;
    if (!hasTags(c)) return false;
    if (q && ![c.docket, c.title_de, c.title_fr, c.explanation_de, c.explanation_fr, c.subject, ...(c.tags || []), ...(c.tags_fr || [])].join(" ").toLowerCase().includes(q)) return false;
    return true;
  });
  const key = {
    score: (c) => c.score ?? -1, title: (c) => titleOf(c).toLowerCase(), docket: (c) => c.docket,
    date: (c) => c.decision_date || c.publication_date || "", edited: (c) => c.last_edit_at || "",
  }[state.sort];
  const dir = state.dir === "desc" ? -1 : 1;
  rows.sort((a, b) => { const x = key(a), y = key(b); return (x < y ? -1 : x > y ? 1 : 0) * dir || a.docket.localeCompare(b.docket); });
  return [...rows.filter((c) => !isBorder(c)), ...rows.filter(isBorder)];  // Grenzfälle always at the bottom
}

function rowHtml(c) {
  const s = c.score ?? 0;
  const overridden = c.score_override !== null && c.score_override !== undefined;
  const unread = !readSet.has(c.slug) && isOpen(c);
  const tip = `${t("score_ai")}: ${c.ai_score ?? "–"}${overridden ? ` · ${t("score_human")}: ${c.score_override} (${c.override_by || ""})` : ""} · ${t("edit_score")}`;
  const edited = (isDone(c) ? `<span class="ok-badge" title="${esc(t("done_by", c.status_by || "–", fmtTime(c.status_at)))}">✓ ${t("approved")}${c.status_by ? ` · ${esc(c.status_by)}` : ""}</span>` : "")
    + (c.last_editor ? `<span class="edited">✎ ${esc(c.last_editor)} · ${esc(fmtTime(c.last_edit_at))}</span>` : "");
  return `<li data-slug="${esc(c.slug)}" class="mrow ${c.slug === state.open ? "sel" : ""} ${isRejected(c) ? "rejected" : ""} ${isBorder(c) ? "border" : ""} ${unread ? "unread" : ""} ${c.last_editor ? "is-edited" : ""}">
    <div class="m-dot">${unread ? '<span class="dot"></span>' : ""}</div>
    <div class="m-score ${overridden ? "manual" : ""}" data-score title="${esc(tip)}">
      <span class="n">${c.score ?? "–"}</span>
      <span class="level"><i class="${band(s)}" style="width:${s}%"></i></span>
    </div>
    <div class="m-main">
      <div class="m-top"><span class="t">${esc(titleOf(c))}</span><span class="m-date">${esc(fmtDate(c.decision_date || c.publication_date))}</span></div>
      <div class="m-sub">${isBorder(c) ? `<span class="bl-badge">${t("border")}</span> ` : ""}${esc(c.docket)}${c.source === "demo" ? ` · ${t("demo")}` : ""}${subjectOf(c) ? ` · <span class="subj" title="${t("subject_hint")}">${esc(subjectOf(c))}</span>` : ""}</div>
      <p class="why">${fmt(whyOf(c))}</p>
      <div class="m-foot"><div class="tags">${c.suva_party ? `<span class="tag party">${t("suva_party")}</span>` : ""}${tagsOf(c).map((g) => `<span class="tag">#${esc(g.label)}</span>`).join("")}</div>${edited}</div>
    </div>
    <div class="m-act">${readOnly() ? "" : isOpen(c)
      ? `<button class="act" data-act="done" title="${t("mark_done")}">✓</button><button class="act" data-act="rejected" title="${t("reject")}">⊘</button>`
      : `<button class="act" data-act="new" title="${isRejected(c) ? t("restore") : t("reopen")}">↺</button>`}</div>
  </li>`;
}

function renderList() {
  const rows = visible();
  const firstBorder = state.scope === "border" ? -1 : rows.findIndex(isBorder);
  const nBorderRows = rows.filter(isBorder).length;
  $("#rows").innerHTML = rows.map((c, i) => (i === firstBorder
    ? `<li class="sect"><b>${t("scope_border")}</b> <span class="count">${nBorderRows}</span><span class="muted">${t("border_hint")}</span></li>` : "") + rowHtml(c)).join("");
  renderActiveFilters();
  const inScope = state.cards.filter(inScopeOf).length;
  $("#listMeta").textContent = t("n_shown", rows.length, inScope);
  const nNew = state.cards.filter((c) => isOpen(c) && !isBorder(c) && !readSet.has(c.slug) && (c.score ?? 0) >= state.minScore).length;
  $("#cNew").textContent = nNew || ""; $("#cRej").textContent = state.cards.filter(isRejected).length || ""; $("#cBorder").textContent = state.cards.filter(isBorder).length || "";
  $("#empty").hidden = rows.length > 0; $("#empty").textContent = state.scope === "new" ? t("empty_new") : t("empty");
}

/* active filters: chips under the toolbar (click × to drop one) + a count on the Filter button */
function activeFilters() {
  const label = (k) => (tagsOf({ tags: [k], tags_fr: [] })[0] || {}).label || k;
  const tagLabel = {};
  state.cards.forEach((c) => tagsOf(c).forEach((g) => { tagLabel[g.key] = tagLabel[g.key] || g.label; }));
  const f = [];
  if (state.month) f.push({ text: t("m" + state.month.slice(5)) + (state.byPublication ? ` (${t("chip_pub")})` : ""), clear: () => { state.month = ""; store.set("lex.month", ""); } });
  if (state.minScore > 0) f.push({ text: t("chip_min", state.minScore), clear: () => { state.minScore = 0; store.set("lex.min", "0"); } });
  state.tags.forEach((k) => f.push({ text: tagLabel[k] || label(k), clear: () => { state.tags = state.tags.filter((x) => x !== k); } }));
  if (state.showRej) f.push({ text: t("chip_rej"), clear: () => { state.showRej = false; store.set("lex.showRej", "0"); } });
  return f;
}
function renderActiveFilters() {
  const f = activeFilters();
  $("#filterCount").textContent = f.length ? ` · ${f.length}` : "";
  $("#filterBtn").classList.toggle("on", f.length > 0);
  $("#activeFilters").innerHTML = f.map((x, i) => `<button class="tag-chip" data-i="${i}" title="${esc(t("remove"))}">${esc(x.text)} <span aria-hidden="true">×</span></button>`).join("")
    + (isDefault() ? "" : `<button class="linkbtn" data-reset>${esc(t("reset_all"))}</button>`);
  $("#activeFilters").querySelectorAll("[data-i]").forEach((b) => (b.onclick = () => { f[+b.dataset.i].clear(); syncFilters(); }));
  const rb = $("#activeFilters [data-reset]"); if (rb) rb.onclick = resetFilters;
}
function syncFilters() {  // after any filter change: controls in the popover, tag list, chips, list
  renderChrome(); renderTagFilter(); renderList();
  $("#showRej").checked = !!state.showRej;
}
// "Zurücksetzen" = back to the defaults (June 2026, relevance from 40), not to "everything": with no threshold
// the ~2,000 crawled rulings that Apertus never scored would flood the list.
const DEFAULTS = { month: "2026-06", minScore: 40 };
const isDefault = () => state.month === DEFAULTS.month && !state.byPublication && state.minScore === DEFAULTS.minScore && !state.tags.length && !state.showRej;
function resetFilters() {
  state.month = DEFAULTS.month; state.byPublication = false; state.minScore = DEFAULTS.minScore; state.tags = []; state.showRej = false;
  store.set("lex.month", state.month); store.set("lex.byPublication", "0"); store.set("lex.min", String(state.minScore)); store.set("lex.showRej", "0");
  syncFilters();
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
const setDone = (slug, done) => setStatus(slug, done ? "done" : "new");
async function setStatus(slug, status) {
  if (!(await requireName())) return;
  await api(`/api/judgements/${encodeURIComponent(slug)}/status`, { method: "PUT", body: JSON.stringify({ status, editor: state.editor }) });
  toast(t({ done: "moved_done", rejected: "moved_rejected" }[status] || "moved_new"));
  if (status !== "new" && state.scope === "new" && state.open === slug) {
    const rows = visible(); const i = rows.findIndex((c) => c.slug === slug);
    const next = rows[i + 1] || rows[i - 1];
    await load(); next ? openPanel(next.slug) : closePanel();
  } else await load();
}
function markRead(slug) { if (!readSet.has(slug)) { readSet.add(slug); saveRead(); } }

/* ---------- citations: "(Erw. 4.2)" / "(consid. 5.2)" link to the consideration in the original text ---------- */
const CITE_RE = /\b(Erw(?:ägung(?:en)?)?\.?|E\.|consid(?:érants?)?\.?|cons\.|considérants?)\s*(\d+(?:\.\d+)*)/g;
// Model text cleanup for display: single line breaks inside a paragraph (left over from the court's HTML) become
// spaces, blank lines stay paragraph breaks; "Art. 26bis" gets the usual superscript.
function tidy(text) {
  return String(text || "").replace(/\r/g, "").replace(/[ \t]*\n(?!\n)(?<!\n\n)[ \t]*/g, " ").replace(/\n{3,}/g, "\n\n")
    .replace(/ {2,}/g, " ").replace(/([(„'’]) /g, "$1").trim();
}
const SUP_RE = /\b(\d+)(bis|ter|quater|quinquies|sexies)\b/g;
function fmt(text) { return esc(tidy(text)).replace(SUP_RE, "$1<sup>$2</sup>"); }
function linkCitations(text) {
  return fmt(text).replace(CITE_RE, (m, word, num) => `<a href="#" class="cite" data-erw="${num}" title="${t("cite_hint")}">${word} ${num}</a>`);
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

// macOS "square.and.pencil" (the usual edit symbol in Mail, Notes, Finder), drawn inline so it follows the text colour
const EDIT_ICON = `<svg class="ico" viewBox="0 0 16 16" aria-hidden="true"><path d="M7.5 2.5H3.8A1.3 1.3 0 0 0 2.5 3.8v8.4a1.3 1.3 0 0 0 1.3 1.3h8.4a1.3 1.3 0 0 0 1.3-1.3V8.5" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/><path d="M12.2 1.9a1.3 1.3 0 0 1 1.9 1.9L8.4 9.5l-2.5.6.6-2.5z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>`;

/* ---------- detail pane ---------- */
async function openPanel(slug) {
  state.open = slug; state.editing = false; state.draft = {}; state.showAi = false; state.tab = state.tab || "summary_" + state.lang;
  markRead(slug);
  $("#panel").hidden = false; renderList(); await renderPanel();
  const tr = document.querySelector(`#rows [data-slug="${CSS.escape(slug)}"]`); if (tr) tr.scrollIntoView({ block: "nearest" });
}
function closePanel() { setBig(false); state.open = null; $("#panel").hidden = true; renderList(); }
// "Gross anzeigen": the same detail view as a large centred window over the list (Esc / backdrop / ⤡ go back)
function setBig(on) {
  document.body.classList.toggle("panel-big", on); $("#backdrop").hidden = !on;
  const b = $("#pExpand"); if (b) { b.textContent = on ? "⤡" : "⤢"; b.title = t(on ? "shrink" : "expand"); b.setAttribute("aria-label", b.title); }
}

async function renderPanel() {
  const d = await api(`/api/judgements/${encodeURIComponent(state.open)}`);
  const a = d.assessment || {};
  const L = state.lang;
  const done = d.status === "done";
  $("#pDocket").textContent = [d.docket, fmtDate(d.decision_date || d.publication_date)].filter(Boolean).join(" · ");
  $("#pTitle").textContent = (L === "fr" ? a.title_fr : a.title_de) || d.subject || d.docket;
  const E = state.editing && !readOnly();
  const dr = state.draft || (state.draft = {});
  $("#pEdit").hidden = readOnly();
  $("#pEdit").innerHTML = E ? esc(t("save")) : `${EDIT_ICON}<span>${esc(t("edit"))}</span>`;
  $("#pEdit").onclick = E ? () => saveAll(d) : async () => { if (await requireName()) { state.editing = true; state.draft = {}; renderPanel(); } };
  $("#pCancel").hidden = !E; $("#pCancel").textContent = t("cancel");
  $("#pCancel").onclick = () => { state.editing = false; state.draft = {}; renderPanel(); };
  $("#pDone").hidden = readOnly() || E;
  const rejected = d.status === "rejected";
  $("#pDone").textContent = rejected ? "↺ " + t("restore") : done ? "↺ " + t("reopen") : "✓ " + t("mark_done");
  $("#pDone").onclick = () => setStatus(d.slug, done || rejected ? "new" : "done");
  $("#pReject").hidden = readOnly() || E || done || rejected;
  $("#pReject").textContent = "⊘ " + t("reject");
  $("#pReject").onclick = () => setStatus(d.slug, "rejected");
  const overridden = a.score_override !== null && a.score_override !== undefined;
  const score = overridden ? a.score_override : a.ai_score;
  const tabs = ["summary_de", "summary_fr", "notes", "text", "history"];
  const why = L === "fr" ? a.explanation_fr : a.explanation_de;
  const whyEdited = a[`explanation_${L}`] !== a[`explanation_${L}_ai`];
  let html = `
    <div class="section"><h4>${t("relevance")}</h4>
      <div class="bigscore">${E ? `<input type="number" min="0" max="100" class="score-in" id="eScore" value="${esc(dr.score ?? score ?? "")}">`
        : `<span class="n">${score ?? "–"}</span>`}<span class="level"><i class="${band(score ?? 0)}" style="width:${score ?? 0}%"></i></span>
        <span class="muted">${t("score_ai")}: ${a.ai_score ?? "–"}${overridden ? ` · ${t("score_human")}: ${a.score_override} (${esc(a.override_by)}, ${esc(fmtTime(a.override_at))})` : ""}</span>
        ${overridden && !readOnly() ? `<button class="btn small" id="revertBtn">${t("revert")}</button>` : ""}</div>
      ${isBorder(d) ? `<div class="bl-note"><span><b>${t("border")}:</b> ${t("border_hint1")}${(d.tier_reason ?? a.tier_reason) ? ` ${fmt(d.tier_reason ?? a.tier_reason)}` : ""}</span>${readOnly() ? "" : `<button class="btn small" id="promoteBtn">${t("promote")}</button>`}</div>` : ""}
      ${(done || rejected) && d.status_by ? `<p class="${done ? "ok-line" : "muted"}">${done ? "✓ " : ""}${esc(t(done ? "done_by" : "rejected_by", d.status_by, fmtTime(d.status_at)))}</p>` : ""}</div>
    <div class="section"><h4>${t("why")}${whyEdited && a.explanation_edited_by ? ` <span class="edited">✎ ${esc(a.explanation_edited_by)}</span>` : ""}</h4>
      ${E ? `<textarea class="why-edit" id="eWhy">${esc(dr.why ?? why ?? "")}</textarea>` : `<p>${fmt(String(why || "").replace(BORDER_PREFIX, ""))}</p>`}
      ${E ? tagEditor(dr.tags ?? a.tags ?? [])
        : `<div class="tags">${a.suva_party ? `<span class="tag party">${t("suva_party")}</span>` : ""}${tagsOf(a).map((g) => `<span class="tag">#${esc(g.label)}</span>`).join("")}${a.tags_edited ? `<span class="muted small">✎</span>` : ""}</div>`}</div>
    <div class="section"><h4>${t("details")}</h4><div class="kv">
      ${d.decision_date ? `<span class="muted">${t("decided")}</span><span>${esc(fmtDate(d.decision_date))}</span>` : ""}
      ${d.publication_date ? `<span class="muted">${t("published")}</span><span>${esc(fmtDate(d.publication_date))}</span>` : ""}
      ${subjectOf(d) ? `<span class="muted">${t("subject")}</span><span>${esc(subjectOf(d))}</span>` : ""}
      ${d.division ? `<span class="muted">${t("division")}</span><span>${esc(d.division)}</span>` : ""}
      ${d.url ? `<span class="muted">${t("original")}</span><span><a href="${esc(d.url)}" target="_blank" rel="noopener">${t("open_bger")} ↗</a></span>` : ""}
    </div></div>
    <div class="tabs">${tabs.map((k) => `<button data-tab="${k}" class="${state.tab === k ? "on" : ""}">${t(k)}${k === "history" && d.history.length ? ` (${d.history.length})` : ""}${k === "notes" && d.notes?.length ? ` (${d.notes.length})` : ""}</button>`).join("")}</div>
    <div class="section" id="tabBody">`;

  if (state.tab.startsWith("summary_")) {
    const lang = state.tab.slice(-2);
    const s = d.summaries[lang];
    if (!s) {
      html += `<p class="muted">${t("no_summary")}</p>`;
      if (d.text && !readOnly()) html += `<button class="btn primary" id="genBtn">${t("generate")}</button>`;
    } else if (E) {
      html += `<textarea class="summary-edit" id="sumEdit" data-lang="${lang}">${esc(dr["sum_" + lang] ?? s.text)}</textarea>`;
    } else {
      const meta = s.edited_by ? `<span class="edited">✎ ${t("edited_by")} ${esc(s.edited_by)} · ${esc(fmtTime(s.edited_at))}</span>`
        : s.model === "suva-human-example" ? `<span class="tag">${t("human_example")}</span>` : `<span class="tag">${t("ai")} · ${esc(s.model)}</span>`;
      html += `<div class="sum-head"><div class="c-sub">${meta}</div></div>
        <div class="summary">${linkCitations(s.text)}</div>
        ${s.edited_by && s.ai_text ? `<div class="row"><button class="btn small" id="toggleAi">${state.showAi ? t("hide_ai") : t("show_ai")}</button></div>` : ""}
        ${state.showAi && s.ai_text ? `<div class="ai-orig">${linkCitations(s.ai_text)}</div>` : ""}`;
    }
  } else if (state.tab === "notes") {
    html += (d.notes || []).length ? `<ul class="notes">${d.notes.map((n) => `<li><div class="note-meta"><b>${esc(n.editor)}</b> · ${esc(fmtTime(n.at))}
        ${readOnly() ? "" : `<button class="act note-del" data-note="${n.id}" title="${t("delete")}">✕</button>`}</div><div class="note-text">${esc(n.text)}</div></li>`).join("")}</ul>`
      : `<p class="muted">${t("no_notes")}</p>`;
    if (!readOnly()) html += `<textarea class="note-edit" id="noteInput" placeholder="${t("note_ph")}">${esc(dr.note || "")}</textarea>
      <div class="row"><button class="btn primary" id="addNote">${t("add_note")}</button></div>`;
  } else if (state.tab === "text") {
    // formatted original (cleaned server-side, see scraper._html_clean); plain text as fallback
    html += d.html ? `<div class="original-html" id="origHtml">${d.html}</div>`
      : d.text ? `<div class="original">${renderOriginal(d.text)}</div>` : `<p class="muted">${t("no_text")}</p>`;
  } else {
    const label = (h) => (h.field === "status" ? `${t("h_status")}: ${t("st_" + h.old_value)} → ${t("st_" + h.new_value)}`
      : t("h_" + h.field.replace("_score", "")) + (h.field.includes("score") ? `: ${esc(h.old_value)} → ${esc(h.new_value)}` : ""));
    // text changes (summaries, reasons) are versions: open one to see before/after and restore either side
    const textField = (f) => /^(summary|explanation)_(de|fr)$/.test(f);
    const ver = (h, side) => {
      const v = side === "old" ? h.old_value : h.new_value;
      return `<div class="ver"><div class="ver-head"><span class="muted">${t(side === "old" ? "v_before" : "v_after")}</span>
        ${readOnly() || v == null ? "" : `<button class="btn small" data-restore="${h.id}" data-side="${side}">↺ ${t("v_restore")}</button>`}</div>
        <div class="ver-text">${v == null ? `<span class="muted">–</span>` : esc(v)}</div></div>`;
    };
    html += d.history.length
      ? `<ul class="history">${d.history.map((h) => textField(h.field)
          ? `<li><details><summary><b>${esc(h.editor)}</b> · ${esc(fmtTime(h.at))} · ${label(h)} <span class="muted">· ${t("v_show")}</span></summary>
              <div class="ver-pair">${ver(h, "old")}${ver(h, "new")}</div></details></li>`
          : `<li><b>${esc(h.editor)}</b> · ${esc(fmtTime(h.at))} · ${label(h)}</li>`).join("")}</ul>`
      : `<p class="muted">${t("no_history")}</p>`;
  }
  html += `</div>`;
  $("#pBody").innerHTML = html;

  $("#pBody").querySelectorAll("[data-tab]").forEach((b) => (b.onclick = () => { state.tab = b.dataset.tab; renderPanel(); }));
  $("#pBody").querySelectorAll("[data-restore]").forEach((b) => (b.onclick = async () => {
    const h = d.history.find((x) => String(x.id) === b.dataset.restore); if (!h || !(await requireName())) return;
    const text = b.dataset.side === "old" ? h.old_value : h.new_value;
    const [kind, lang] = h.field.split("_");
    try {
      await api(`/api/judgements/${encodeURIComponent(d.slug)}/${kind}/${lang}`, { method: "PUT", body: JSON.stringify({ text, editor: state.editor }) });
      toast(t("v_restored")); await load();
    } catch (e) { toast(`${t("failed_action")}: ${errText(e)}`); }
  }));
  $("#pBody").querySelectorAll(".cite").forEach((el) => (el.onclick = (e) => { e.preventDefault(); state.tab = "text"; state.pendingErw = el.dataset.erw; renderPanel(); }));
  if (state.tab === "text" && d.html) anchorHtml($("#origHtml"));
  if (state.tab === "text" && state.pendingErw) {
    const num = state.pendingErw; state.pendingErw = null;
    let el = null; for (let n = num; n && !el; n = n.includes(".") ? n.slice(0, n.lastIndexOf(".")) : "") el = document.getElementById("erw-" + n);
    if (el) { el.scrollIntoView({ behavior: "smooth", block: "center" }); el.classList.add("flash"); setTimeout(() => el.classList.remove("flash"), 2200); }
    else toast(t("cite_missing"));
  }
  const on = (id, fn) => { const el = document.getElementById(id); if (el) el.onclick = fn; };
  const keep = (id, key) => { const el = document.getElementById(id); if (el) el.oninput = () => (dr[key ?? el.dataset.lang] = el.value); };
  const ti = document.getElementById("tagInput");
  if (ti) {
    const cur = () => dr.tags ?? [...(a.tags || [])];
    const add = () => { const k = tagKey(ti.value); if (k && !cur().includes(k)) { dr.tags = [...cur(), k]; } ti.value = ""; renderPanel(); };
    ti.onkeydown = (e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(); } };
    ti.oninput = () => { if (vocabHas(ti.value)) add(); };   // picked from the suggestion list
    $("#pBody").querySelectorAll("[data-rmtag]").forEach((b) => (b.onclick = () => { dr.tags = cur().filter((x) => x !== b.dataset.rmtag); renderPanel(); }));
  }
  keep("eScore", "score"); keep("eWhy", "why"); keep("noteInput", "note");
  const se = document.getElementById("sumEdit"); if (se) se.oninput = () => (dr["sum_" + se.dataset.lang] = se.value);
  on("addNote", async () => {
    const text = $("#noteInput").value.trim(); if (!text || !(await requireName())) return;
    await api(`/api/judgements/${encodeURIComponent(d.slug)}/notes`, { method: "POST", body: JSON.stringify({ text, editor: state.editor }) });
    dr.note = ""; toast(t("saved")); await load();
  });
  $("#pBody").querySelectorAll(".note-del").forEach((b) => (b.onclick = async () => {
    if (!(await requireName())) return;
    await api(`/api/judgements/${encodeURIComponent(d.slug)}/notes/${b.dataset.note}`, { method: "DELETE", body: JSON.stringify({ editor: state.editor }) });
    await load();
  }));
  on("toggleAi", () => { state.showAi = !state.showAi; renderPanel(); });
  on("revertBtn", async () => {
    if (!(await requireName())) return;
    await api(`/api/judgements/${encodeURIComponent(state.open)}/score`, { method: "DELETE", body: JSON.stringify({ editor: state.editor }) });
    await load();
  });
  on("genBtn", () => startAdd(d.docket));
  on("promoteBtn", async () => {  // "not junk": a human score of at least 60 takes it out of the Grenzfälle
    if (!(await requireName())) return;
    await api(`/api/judgements/${encodeURIComponent(state.open)}/score`, { method: "PUT", body: JSON.stringify({ score: 70, editor: state.editor }) });
    toast(t("promoted")); await load();
  });
}

// Keyword editor: chips with ×, input suggests the fixed Suva list (stored by German label, shown in the UI language).
const vocab = () => state.status?.tag_vocab || [];
const vocabHas = (v) => vocab().some((x) => x.de === v.trim() || x.fr === v.trim());
const tagKey = (v) => { v = v.replace(/^#/, "").trim(); const m = vocab().find((x) => x.de.toLowerCase() === v.toLowerCase() || x.fr.toLowerCase() === v.toLowerCase()); return m ? m.de : v; };
const tagLabel = (k) => { const m = vocab().find((x) => x.de === k); return state.lang === "fr" && m ? m.fr : k; };
function tagEditor(list) {
  return `<div class="tags tag-edit">${list.map((k) => `<span class="tag">#${esc(tagLabel(k))}<button class="rm" data-rmtag="${esc(k)}" title="${t("delete")}">×</button></span>`).join("")}
    <input id="tagInput" list="tagVocab" placeholder="${t("add_tag")}"><datalist id="tagVocab">${vocab().filter((x) => !list.includes(x.de))
      .map((x) => `<option value="${esc(state.lang === "fr" ? x.fr : x.de)}">`).join("")}</datalist></div>`;
}

// One "Bearbeiten" for the whole panel: score, reasoning (current language) and both summaries; saves what changed.
async function saveAll(d) {
  const a = d.assessment || {}, dr = state.draft || {}, L = state.lang, base = `/api/judgements/${encodeURIComponent(d.slug)}`;
  const put = (path, body) => api(base + path, { method: "PUT", body: JSON.stringify({ ...body, editor: state.editor }) });
  const cur = a.score_override ?? a.ai_score;
  try {
    if (dr.score !== undefined && dr.score !== "" && +dr.score !== cur) await put("/score", { score: Math.max(0, Math.min(100, parseInt(dr.score, 10))) });
    if (dr.tags !== undefined && JSON.stringify(dr.tags) !== JSON.stringify(a.tags || [])) await put("/tags", { tags: dr.tags });
    if (dr.why !== undefined && dr.why.trim() !== (a[`explanation_${L}`] || "").trim()) await put(`/explanation/${L}`, { text: dr.why.trim() });
    for (const lang of ["de", "fr"]) {
      const v = dr["sum_" + lang];
      if (v !== undefined && v.trim() !== (d.summaries[lang]?.text || "").trim()) await put(`/summary/${lang}`, { text: v.trim() });
    }
    state.editing = false; state.draft = {}; toast(t("saved"));
  } catch (e) { toast(`${t("failed_action")}: ${errText(e)}`); }
  await load();
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

/* ---------- resizable detail panel (drag the left edge; double-click resets; width kept per browser) ---------- */
function initResizer() {
  const r = $("#resizer"), layout = $("#layout");
  const apply = (w) => layout.style.setProperty("--panel-w", w ? w + "px" : "");
  const clamp = (w) => Math.round(Math.max(340, Math.min(w, layout.clientWidth - 380)));
  const saved = parseInt(store.get("lex.panelW", "0"), 10);
  if (saved) apply(saved);
  r.addEventListener("pointerdown", (e) => {
    e.preventDefault(); r.setPointerCapture(e.pointerId); r.classList.add("drag"); document.body.classList.add("resizing");
    const move = (ev) => apply(clamp(layout.getBoundingClientRect().right - ev.clientX));
    const up = () => {
      r.removeEventListener("pointermove", move); r.removeEventListener("pointerup", up);
      r.classList.remove("drag"); document.body.classList.remove("resizing");
      const w = parseInt(layout.style.getPropertyValue("--panel-w"), 10); if (w) store.set("lex.panelW", String(w));
    };
    r.addEventListener("pointermove", move); r.addEventListener("pointerup", up);
  });
  r.ondblclick = () => { apply(0); store.set("lex.panelW", "0"); };
}

/* ---------- wiring ---------- */
function init() {
  initResizer();
  $("#pExpand").onclick = () => setBig(!document.body.classList.contains("panel-big"));
  $("#backdrop").onclick = () => setBig(false);
  setBig(false);
  state.month = store.get("lex.month", "2026-06");  // default: June 2026 (Suva's top-5 review is about June)
  state.byPublication = store.get("lex.byPublication", "0") === "1";
  state.showRej = store.get("lex.showRej", "0") === "1";
  if (state.scope === "done" || state.scope === "rejected") {  // old scopes: now "Alle" (+ the rejected filter)
    if (state.scope === "rejected") { state.showRej = true; store.set("lex.showRej", "1"); }
    state.scope = "all"; store.set("lex.scope", "all");
  }
  $("#showRej").checked = state.showRej;
  $("#showRej").onchange = (e) => { state.showRej = e.target.checked; store.set("lex.showRej", state.showRej ? "1" : "0"); renderList(); };
  $("#resetFilters").onclick = resetFilters;
  const pop = $("#filterPop"), fb = $("#filterBtn");
  const setPop = (open) => { pop.hidden = !open; fb.setAttribute("aria-expanded", String(open)); };
  fb.onclick = (e) => { e.stopPropagation(); setPop(pop.hidden); };
  // composedPath: a chip removed by its own click is no longer in the DOM, but still in the event path
  document.addEventListener("click", (e) => { if (!pop.hidden && !e.composedPath().some((n) => n === pop || n === fb)) setPop(false); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !pop.hidden) setPop(false); });
  if ($("#pubToggle")) $("#pubToggle").onchange = (e) => { state.byPublication = e.target.checked; store.set("lex.byPublication", state.byPublication ? "1" : "0"); renderList(); };
  if ($("#monthSel")) $("#monthSel").onchange = (e) => { state.month = e.target.value; store.set("lex.month", state.month); renderList(); };
  if ($("#infoBtn")) $("#infoBtn").onclick = openInfo;
  renderChrome();
  document.querySelectorAll("[data-lang]").forEach((b) => (b.onclick = () => {
    state.lang = b.dataset.lang; store.set("suva.lang", state.lang);
    if (state.tab?.startsWith("summary_")) state.tab = "summary_" + state.lang;
    renderChrome(); renderTagFilter(); renderList(); if (state.open) renderPanel();
  }));
  document.querySelectorAll("#scope [data-scope]").forEach((b) => (b.onclick = () => { state.scope = b.dataset.scope; store.set("lex.scope", state.scope); renderChrome(); renderList(); }));
  document.querySelectorAll("#mhead [data-sort]").forEach((b) => (b.onclick = () => {
    if (state.sort === b.dataset.sort) state.dir = state.dir === "desc" ? "asc" : "desc";
    else { state.sort = b.dataset.sort; state.dir = state.sort === "title" ? "asc" : "desc"; }
    store.set("lex.sort", state.sort); store.set("lex.dir", state.dir); renderChrome(); renderList();
  }));
  // a failed save must never be silent (e.g. missing/wrong editor key on the hosted server)
  window.addEventListener("unhandledrejection", (e) => { toast(`${t("failed_action")}: ${errText(e.reason)}`); });
  $("#minScore").oninput = (e) => { state.minScore = parseInt(e.target.value, 10); store.set("lex.min", String(state.minScore)); $("#minScoreOut").textContent = state.minScore; renderList(); };
  $("#tagFilter").onchange = (e) => { const v = e.target.value; if (v && !state.tags.includes(v)) state.tags.push(v); renderTagFilter(); renderList(); };
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
    if (act) { e.stopPropagation(); setStatus(tr.dataset.slug, act.dataset.act); return; }
    const sc = e.target.closest("[data-score]");
    if (sc && !readOnly()) { e.stopPropagation(); editScore(tr.dataset.slug, sc); return; }
    openPanel(tr.dataset.slug);
  });
  // keyboard like Mail: ↑/↓ move, Esc closes, E marks done / reopens
  document.addEventListener("keydown", (e) => {
    if (document.querySelector("dialog[open]") || /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName)) return;
    if (e.key === "Escape" && document.body.classList.contains("panel-big")) { setBig(false); return; }
    if (e.key === "Escape" && state.open) closePanel();
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      const rows = visible(); if (!rows.length) return;
      const i = rows.findIndex((c) => c.slug === state.open);
      const n = e.key === "ArrowDown" ? Math.min(rows.length - 1, i + 1) : Math.max(0, i - 1);
      e.preventDefault(); openPanel(rows[i < 0 ? 0 : n].slug);
    }
    if ((e.key === "e" || e.key === "E") && state.open && !readOnly()) {
      const c = state.cards.find((x) => x.slug === state.open); if (c) setStatus(c.slug, isOpen(c) ? "done" : "new");
    }
  });
  api("/api/status").then((s) => { state.status = s; state.dataVersion = s.data_version; renderChrome(); renderList(); }).catch(() => {});
  load().then(() => {
    /* DAU-Filter (Suva): open the top-ranked ruling right away, or the one requested via ?open=<slug> (Trefferliste link) */
    const want = new URLSearchParams(location.search).get("open");
    const top = visible().filter((c) => !isBorder(c)).sort((a, b) => (b.score ?? -1) - (a.score ?? -1))[0];
    const first = want || (top ? top.slug : null);  // top-ranked ruling of the current month filter
    if (first && !state.open) openPanel(first);
  }).catch(() => {});
  /* Auto-refresh: reload list + open panel when the server's data_version changes (new pipeline data or
     someone else's edit). Paused while editing, while a field has focus, or while the tab is hidden. */
  if (!STATIC) setInterval(async () => {
    if (document.hidden || state.editing) return;
    if (document.activeElement && /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)) return;
    try {
      const s = await api("/api/status");
      if (state.dataVersion && s.data_version && s.data_version !== state.dataVersion) {
        state.status = s; await load(); toast(state.lang === "fr" ? "Données mises à jour" : "Daten aktualisiert");
      }
      state.dataVersion = s.data_version;
    } catch (e) { /* offline for a moment: try again next tick */ }
  }, 30000);
}
init();
