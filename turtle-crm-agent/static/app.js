/* ── State ── */
let allFields = [];   // flat array of field objects with id, attribute, touch_point, value, …

/* ── DOM refs ── */
const extractBtn    = document.getElementById("extractBtn");
const transcript    = document.getElementById("transcript");
const clientId      = document.getElementById("clientId");
const statusBar     = document.getElementById("statusBar");
const resultsArea   = document.getElementById("resultsArea");
const searchBox     = document.getElementById("searchBox");
const categoryFilter = document.getElementById("categoryFilter");
const hideNull      = document.getElementById("hideNull");
const statPill      = document.getElementById("statPill");

/* ── Extract ── */
extractBtn.addEventListener("click", async () => {
  const text = transcript.value.trim();
  if (!text) { setStatus("Paste a transcript first.", true); return; }

  setStatus("Extracting… this may take 30–90 seconds.", false);
  extractBtn.disabled = true;
  showSpinner();

  try {
    const res = await fetch("/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        client_id: clientId.value.trim() || "manual_input",
        transcript: text,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      setStatus("Error: " + (data.error || res.statusText), true);
      showPlaceholder("Extraction failed. Check server logs.");
      return;
    }

    // Flatten fields object → array
    allFields = Object.entries(data.fields).map(([id, f]) => ({ id, ...f }));

    buildCategoryFilter();
    renderResults();
    setStatus(
      `Done in ${data.duration_seconds}s — ${allFields.filter(f => f.value !== null).length} fields extracted out of ${allFields.length}.`,
      false
    );
  } catch (err) {
    setStatus("Network error: " + err.message, true);
    showPlaceholder("Could not reach the server.");
  } finally {
    extractBtn.disabled = false;
  }
});

/* ── Live filters ── */
searchBox.addEventListener("input", renderResults);
categoryFilter.addEventListener("change", renderResults);
hideNull.addEventListener("change", renderResults);

/* ── Render ── */
function renderResults() {
  if (!allFields.length) return;

  const query    = searchBox.value.toLowerCase();
  const category = categoryFilter.value;
  const onlyFilled = hideNull.checked;

  const filtered = allFields.filter(f => {
    if (onlyFilled && f.value === null) return false;
    if (category && f.touch_point !== category) return false;
    if (query) {
      const haystack = [f.id, f.attribute, f.touch_point, JSON.stringify(f.value), f.source]
        .join(" ").toLowerCase();
      if (!haystack.includes(query)) return false;
    }
    return true;
  });

  // Group by touch_point
  const groups = {};
  for (const f of filtered) {
    const tp = f.touch_point || "Other";
    if (!groups[tp]) groups[tp] = [];
    groups[tp].push(f);
  }

  const filled = filtered.filter(f => f.value !== null).length;
  statPill.textContent = `${filled} extracted / ${filtered.length} shown`;

  if (!filtered.length) {
    resultsArea.innerHTML = `<div class="placeholder"><span>No fields match your filters.</span></div>`;
    return;
  }

  resultsArea.innerHTML = Object.entries(groups).map(([tp, fields]) => `
    <div>
      <div class="group-label">${tp}</div>
      <div class="group-cards">
        ${fields.map(renderCard).join("")}
      </div>
    </div>
  `).join("");
}

function renderCard(f) {
  const confClass = `conf-${f.confidence_level || "not_extracted"}`;
  const confLabel = f.confidence_level || "not_extracted";
  const valueStr  = formatValue(f.value);
  const isNull    = f.value === null;

  return `
    <div class="card">
      <div class="card-top">
        <div>
          <div class="card-id">#${f.id}</div>
        </div>
        <div class="card-attr">${escHtml(f.attribute || "")}</div>
        <div class="conf-badge ${confClass}">${confLabel.replace("_", " ")}</div>
      </div>
      <div class="card-value ${isNull ? "null-value" : ""}">${isNull ? "—" : escHtml(valueStr)}</div>
      ${f.source ? `<div class="card-source">${escHtml(f.source)}</div>` : ""}
    </div>
  `;
}

function formatValue(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "object") return JSON.stringify(v, null, 2);
  if (Array.isArray(v)) return v.join("\n");
  return String(v);
}

function escHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/* ── Category filter ── */
function buildCategoryFilter() {
  const categories = [...new Set(allFields.map(f => f.touch_point).filter(Boolean))];
  categoryFilter.innerHTML = `<option value="">All categories</option>` +
    categories.map(c => `<option value="${escHtml(c)}">${escHtml(c)}</option>`).join("");
}

/* ── UI helpers ── */
function setStatus(msg, isError) {
  statusBar.textContent = msg;
  statusBar.className = "status-bar" + (isError ? " error" : "");
}

function showSpinner() {
  resultsArea.innerHTML = `
    <div class="placeholder">
      <div class="spinner"></div>
      <span>Running extraction pipeline…</span>
    </div>`;
}

function showPlaceholder(msg) {
  resultsArea.innerHTML = `<div class="placeholder"><span>${escHtml(msg)}</span></div>`;
}
