"""Standalone demo page for the AI pipeline -- calls /process directly,
same FastAPI app, same origin (no CORS issues). Explicitly NOT part of
the real app's FE->BE->AI data flow (see CLAUDE.md) -- a presentation
tool for HCLTech/supervisor demos, kept isolated in its own module so
it's obviously separable from the real service surface (main.py just
mounts this one route)."""

DEMO_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TCO DMS &mdash; AI Pipeline Demo</title>
<style>
  :root {
    --bg: #0f1720;
    --panel: #16212c;
    --panel-2: #1c2933;
    --border: #26343f;
    --text: #e7edf2;
    --text-dim: #93a4b0;
    --accent: #4fb0ff;
    --accent-dim: #2c6f9e;
    --ok: #34c98a;
    --warn: #e0b64f;
    --bad: #e2685f;
    --radius: 8px;
    --radius-sm: 4px;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, "Segoe UI", Inter, Roboto, sans-serif;
    min-height: 100vh;
  }
  header {
    padding: 24px 32px 16px;
    border-bottom: 1px solid var(--border);
  }
  header h1 {
    margin: 0 0 4px;
    font-size: 20px;
    font-weight: 600;
    letter-spacing: -0.01em;
  }
  header p {
    margin: 0;
    color: var(--text-dim);
    font-size: 13px;
  }
  main {
    max-width: 1080px;
    margin: 0 auto;
    padding: 32px;
    display: grid;
    grid-template-columns: 360px 1fr;
    gap: 24px;
  }
  @media (max-width: 800px) {
    main { grid-template-columns: 1fr; }
  }
  .panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
  }
  .panel h2 {
    margin: 0 0 14px;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-dim);
  }
  #dropzone {
    border: 2px dashed var(--border);
    border-radius: var(--radius);
    padding: 32px 16px;
    text-align: center;
    cursor: pointer;
    transition: border-color 160ms ease-out, background 160ms ease-out;
  }
  #dropzone:hover, #dropzone.drag {
    border-color: var(--accent);
    background: rgba(79, 176, 255, 0.06);
  }
  #dropzone svg { opacity: 0.6; margin-bottom: 8px; }
  #dropzone .hint { font-size: 12px; color: var(--text-dim); margin-top: 4px; }
  #filename { font-size: 13px; margin-top: 10px; color: var(--accent); word-break: break-all; }
  input[type="file"] { display: none; }
  label.field {
    display: block;
    font-size: 12px;
    color: var(--text-dim);
    margin: 16px 0 6px;
  }
  input[type="number"] {
    width: 100%;
    background: var(--panel-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 8px 10px;
    color: var(--text);
    font-size: 13px;
  }
  button {
    width: 100%;
    margin-top: 18px;
    padding: 10px 16px;
    border: none;
    border-radius: var(--radius-sm);
    background: var(--accent);
    color: #06141d;
    font-weight: 600;
    font-size: 13px;
    cursor: pointer;
    transition: background 160ms ease-out, transform 160ms ease-out;
  }
  button:hover:not(:disabled) { background: #6cbdff; }
  button:active:not(:disabled) { transform: scale(0.98); }
  button:disabled { opacity: 0.5; cursor: default; }
  #status { margin-top: 12px; font-size: 12px; color: var(--text-dim); min-height: 16px; }

  .badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
  }
  .badge.ok { background: rgba(52, 201, 138, 0.15); color: var(--ok); }
  .badge.warn { background: rgba(224, 182, 79, 0.15); color: var(--warn); }
  .badge.bad { background: rgba(226, 104, 95, 0.15); color: var(--bad); }
  .badge.neutral { background: rgba(147, 164, 176, 0.15); color: var(--text-dim); }

  #results { display: none; flex-direction: column; gap: 16px; }
  #results.show { display: flex; }
  .row-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  #imgwrap { position: relative; max-width: 100%; border-radius: var(--radius-sm); overflow: hidden; border: 1px solid var(--border); }
  #imgwrap img, #imgwrap canvas { display: block; width: 100%; height: auto; }
  #imgwrap canvas { position: absolute; top: 0; left: 0; }

  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  table td { padding: 7px 8px; border-bottom: 1px solid var(--border); vertical-align: top; }
  table td.k { color: var(--text-dim); width: 40%; white-space: nowrap; }
  table td.v { font-weight: 500; word-break: break-word; }
  .empty-note { color: var(--text-dim); font-size: 12px; font-style: italic; }

  .checks { display: grid; gap: 8px; margin-top: 10px; }
  .check { display: flex; justify-content: space-between; align-items: center; background: var(--panel-2); border-radius: var(--radius-sm); padding: 8px 12px; font-size: 12px; }
  .check .name { color: var(--text-dim); }
  .check .val { font-weight: 600; }

  details { margin-top: 4px; }
  summary { cursor: pointer; font-size: 12px; color: var(--text-dim); }
  pre { background: var(--panel-2); border-radius: var(--radius-sm); padding: 12px; font-size: 11px; overflow: auto; max-height: 320px; color: var(--text-dim); }

  #placeholder { color: var(--text-dim); font-size: 13px; text-align: center; padding: 60px 20px; }
</style>
</head>
<body>

<header>
  <h1>TCO DMS &mdash; AI Pipeline Demo</h1>
  <p>HCL Capstone (OENG1183) &middot; standalone demo, calls the AI service directly &mdash; not part of the production FE&rarr;BE&rarr;AI flow</p>
</header>

<main>
  <section class="panel">
    <h2>Upload document</h2>
    <div id="dropzone">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 3v12m0-12l-4 4m4-4l4 4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2"/></svg>
      <div>Click or drag a file here</div>
      <div class="hint">PDF, DOCX, PNG, JPG, CSV</div>
      <div id="filename"></div>
    </div>
    <input type="file" id="fileInput" accept=".pdf,.docx,.png,.jpg,.jpeg,.csv">

    <label class="field">Proposed monthly repayment (optional, AUD)</label>
    <input type="number" id="repayment" placeholder="e.g. 1200">

    <button id="submitBtn" disabled>Run AI pipeline</button>
    <div id="status"></div>
  </section>

  <section class="panel">
    <h2>Results</h2>
    <div id="placeholder">Upload a document to see extraction, redaction, and readiness results.</div>
    <div id="results">
      <div>
        <div class="row-head">
          <span id="pathBadge" class="badge neutral">&mdash;</span>
          <span id="errorBadge" class="badge bad" style="display:none">Error</span>
        </div>
        <div id="imgwrap" style="display:none">
          <img id="previewImg">
          <canvas id="overlay"></canvas>
        </div>
      </div>

      <div>
        <h2 style="margin-bottom:8px">Extracted fields</h2>
        <table id="fieldsTable"></table>
      </div>

      <div id="readinessBlock" style="display:none">
        <h2 style="margin-bottom:8px" id="readinessTitle">Readiness</h2>
        <span id="verdictBadge" class="badge neutral">&mdash;</span>
        <div class="checks" id="checksList"></div>
      </div>

      <details>
        <summary>Raw JSON response</summary>
        <pre id="rawJson"></pre>
      </details>
    </div>
  </section>
</main>

<script>
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const filenameEl = document.getElementById('filename');
const submitBtn = document.getElementById('submitBtn');
const statusEl = document.getElementById('status');
const placeholder = document.getElementById('placeholder');
const resultsEl = document.getElementById('results');

let selectedFile = null;

dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag'));
dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('drag');
  if (e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => { if (fileInput.files.length) setFile(fileInput.files[0]); });

function setFile(f) {
  selectedFile = f;
  filenameEl.textContent = f.name;
  submitBtn.disabled = false;
}

function fmtKey(k) {
  return k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function fmtVal(v) {
  if (v === null || v === undefined || v === '') return null;
  if (Array.isArray(v)) return v.length ? v.join(', ') : null;
  if (typeof v === 'number') return v.toLocaleString(undefined, {maximumFractionDigits: 2});
  return String(v);
}

function verdictClass(verdict) {
  if (verdict === 'READY') return 'ok';
  if (verdict === 'NOT_READY') return 'bad';
  if (verdict === 'INSUFFICIENT_DATA') return 'warn';
  return 'neutral';
}

function renderChecks(checks) {
  const list = document.getElementById('checksList');
  list.innerHTML = '';
  for (const [name, c] of Object.entries(checks || {})) {
    const row = document.createElement('div');
    row.className = 'check';
    const passIcon = c.pass === true ? '✓' : c.pass === false ? '✗' : '?';
    const passColor = c.pass === true ? 'var(--ok)' : c.pass === false ? 'var(--bad)' : 'var(--text-dim)';
    const valTxt = c.value === null || c.value === undefined ? 'n/a' : (typeof c.value === 'number' ? c.value.toFixed(3) : c.value);
    row.innerHTML = `<span class="name">${fmtKey(name)} (threshold ${c.threshold})</span><span class="val" style="color:${passColor}">${passIcon} ${valTxt}</span>`;
    list.appendChild(row);
  }
}

function drawRedaction(items) {
  const img = document.getElementById('previewImg');
  const canvas = document.getElementById('overlay');
  const draw = () => {
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#e2685f';
    ctx.fillStyle = 'rgba(226, 104, 95, 0.25)';
    ctx.lineWidth = Math.max(2, canvas.width * 0.003);
    for (const box of items) {
      const x = box.x_pct * canvas.width;
      const y = box.y_pct * canvas.height;
      const w = box.w_pct * canvas.width;
      const h = box.h_pct * canvas.height;
      ctx.fillRect(x, y, w, h);
      ctx.strokeRect(x, y, w, h);
    }
  };
  if (img.complete) draw(); else img.onload = draw;
}

async function runPipeline() {
  submitBtn.disabled = true;
  statusEl.textContent = 'Processing... (first run loads OCR models, can take 1-2 min)';
  placeholder.style.display = 'none';
  resultsEl.classList.add('show');

  const form = new FormData();
  form.append('file', selectedFile);
  form.append('include_preview', 'true');
  const repayment = document.getElementById('repayment').value;
  if (repayment) form.append('proposed_monthly_repayment', repayment);

  try {
    const res = await fetch('/process', { method: 'POST', body: form });
    const data = await res.json();
    statusEl.textContent = 'Done.';
    renderResults(data);
  } catch (err) {
    statusEl.textContent = 'Request failed: ' + err.message;
  } finally {
    submitBtn.disabled = false;
  }
}

function renderResults(data) {
  document.getElementById('rawJson').textContent = JSON.stringify(data, null, 2);

  const pathBadge = document.getElementById('pathBadge');
  pathBadge.textContent = data.processing_path || 'unknown path';
  pathBadge.className = 'badge ' + (data.processing_path === 'ocr' ? 'warn' : 'ok');

  const errorBadge = document.getElementById('errorBadge');
  errorBadge.style.display = data.error ? 'inline-block' : 'none';
  if (data.error) errorBadge.textContent = data.error;

  // Image preview + redaction overlay -- must show the ENHANCED image
  // (post deskew/autocrop) the AI actually computed boxes against, not the
  // raw upload. Autocrop alone can shrink dimensions 20%+, so overlaying
  // percentage boxes on the untouched original looks badly misaligned.
  const imgwrap = document.getElementById('imgwrap');
  if (data.preview_image_base64) {
    imgwrap.style.display = 'block';
    const img = document.getElementById('previewImg');
    img.src = 'data:image/png;base64,' + data.preview_image_base64;
    if (data.redaction && data.redaction.type === 'boxes') {
      drawRedaction(data.redaction.items || []);
    }
  } else {
    imgwrap.style.display = 'none';
  }

  // Fields table
  const table = document.getElementById('fieldsTable');
  table.innerHTML = '';
  const fields = data.fields || {};
  const entries = Object.entries(fields).filter(([k, v]) => fmtVal(v) !== null);
  if (!entries.length) {
    table.innerHTML = '<tr><td class="empty-note">No fields extracted.</td></tr>';
  } else {
    for (const [k, v] of entries) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td class="k">${fmtKey(k)}</td><td class="v">${fmtVal(v)}</td>`;
      table.appendChild(tr);
    }
  }

  // Readiness (loan or balance-sheet, whichever is present)
  const readinessBlock = document.getElementById('readinessBlock');
  const readiness = data.loan_readiness || data.balance_sheet_readiness;
  const readinessKind = data.loan_readiness ? 'Loan readiness' : (data.balance_sheet_readiness ? 'Balance-sheet readiness' : null);
  if (readiness) {
    readinessBlock.style.display = 'block';
    document.getElementById('readinessTitle').textContent = readinessKind;
    const vb = document.getElementById('verdictBadge');
    vb.textContent = readiness.verdict;
    vb.className = 'badge ' + verdictClass(readiness.verdict);
    renderChecks(readiness.checks);
  } else {
    readinessBlock.style.display = 'none';
  }
}

submitBtn.addEventListener('click', runPipeline);
</script>
</body>
</html>
"""
