/* ─── PAC · Python Accounting · Frontend JS ─────────────────────────────── */

const API = {
  generate: '/api/generate',
  entries:  '/api/entries',
  delete:   (id) => `/api/entries/${id}`,
  clear:    '/api/entries/clear',
};

/* ─── State ─────────────────────────────────────────────────────────────── */
let totalEntries = 0;

/* ─── DOM refs ──────────────────────────────────────────────────────────── */
const $  = (id) => document.getElementById(id);
const input       = $('transactionInput');
const generateBtn = $('generateBtn');
const clearBtn    = $('clearBtn');
const copyBtn     = $('copyBtn');
const outputSec   = $('outputSection');
const outputBody  = $('outputBody');
const entriesList = $('entriesList');
const statCount   = $('statCount');
const statTotal   = $('statTotal');
const clearAllBtn = $('clearAllBtn');

/* ─── Toast system ──────────────────────────────────────────────────────── */
function toast(msg, type = 'info', duration = 3000) {
  const icons = { success: '✓', error: '✕', info: '◆' };
  const tc = $('toastContainer');
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span class="toast-icon">${icons[type]}</span><span>${msg}</span>`;
  tc.appendChild(t);
  requestAnimationFrame(() => { requestAnimationFrame(() => { t.classList.add('show'); }); });
  setTimeout(() => {
    t.classList.remove('show');
    setTimeout(() => t.remove(), 400);
  }, duration);
}

/* ─── Format currency ────────────────────────────────────────────────────── */
function fmtAmount(n) {
  return '₹' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

/* ─── Format timestamp ───────────────────────────────────────────────────── */
function fmtTime(ts) {
  if (!ts) return 'now';
  const d = new Date(ts.replace(' ', 'T') + 'Z');
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
}

/* ─── Render output ─────────────────────────────────────────────────────── */
function renderOutput(data) {
  if (!data.success) {
    outputBody.innerHTML = `
      <div class="error-state">
        <span style="font-size:18px">⚠</span>
        <div>
          <div style="font-weight:600;margin-bottom:4px">Parse Error</div>
          <div style="opacity:.7">${data.error}</div>
        </div>
      </div>
    `;
    outputSec.classList.add('visible');
    return;
  }

  const now = new Date().toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric'
  });

  outputBody.innerHTML = `
    <div class="journal-display">
      <div class="journal-date-row">
        <span>Journal Entry</span>
        <span>${now}</span>
      </div>
      <table class="journal-table">
        <thead>
          <tr>
            <th>Particulars</th>
            <th style="text-align:center">L.F.</th>
            <th>Debit (₹)</th>
            <th>Credit (₹)</th>
          </tr>
        </thead>
        <tbody>
          <tr class="debit-row">
            <td>${data.debit.account} A/c <span class="dr-tag">Dr</span></td>
            <td style="text-align:center;color:var(--text-muted);font-size:12px">—</td>
            <td class="amount-col">${fmtAmount(data.debit.amount)}</td>
            <td></td>
          </tr>
          <tr class="credit-row">
            <td>To ${data.credit.account} A/c</td>
            <td style="text-align:center;color:var(--text-muted);font-size:12px">—</td>
            <td></td>
            <td class="amount-col">${fmtAmount(data.credit.amount)}</td>
          </tr>
        </tbody>
      </table>
      <div class="narration-row">
        (${data.narration})
      </div>
      <div class="rule-badge">
        ◈ ${data.rule_applied}
      </div>
    </div>
  `;

  outputSec.classList.add('visible');
}

/* ─── Generate entry ─────────────────────────────────────────────────────── */
async function generateEntry() {
  const tx = input.value.trim();
  if (!tx) { toast('Please enter a transaction.', 'error'); input.focus(); return; }

  generateBtn.classList.add('loading');
  outputSec.classList.remove('visible');

  try {
    const res = await fetch(API.generate, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transaction: tx }),
    });
    const data = await res.json();
    renderOutput(data);
    if (data.success) {
      toast('Journal entry generated!', 'success');
      loadEntries();
    } else {
      toast(data.error || 'Failed to generate entry.', 'error');
    }
  } catch (e) {
    toast('Network error. Is Flask running?', 'error');
  } finally {
    generateBtn.classList.remove('loading');
  }
}

/* ─── Copy output ─────────────────────────────────────────────────────────── */
function copyOutput() {
  const text = outputBody.innerText;
  if (!text) { toast('Nothing to copy.', 'error'); return; }
  navigator.clipboard.writeText(text).then(() => {
    toast('Copied to clipboard!', 'success');
  });
}

/* ─── Load recent entries ───────────────────────────────────────────────── */
async function loadEntries() {
  try {
    const res = await fetch(API.entries + '?limit=20');
    const data = await res.json();
    renderEntries(data);
  } catch(e) { /* silent */ }
}

function renderEntries(entries) {
  totalEntries = entries.length;
  statCount.textContent = totalEntries;

  if (!entries.length) {
    entriesList.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">◌</div>
        No entries yet.<br>Generate your first one!
      </div>
    `;
    statTotal.textContent = '₹0';
    return;
  }

  const total = entries.reduce((s, e) => s + (e.amount || 0), 0);
  statTotal.textContent = fmtAmount(total);

  entriesList.innerHTML = entries.map(e => `
    <div class="entry-item" data-id="${e.id}">
      <button class="entry-delete" onclick="deleteEntry(${e.id}, event)" title="Delete">✕</button>
      <div class="entry-tx">${escHtml(e.transaction_text)}</div>
      <div class="entry-accounts">
        <div class="entry-debit">${escHtml(e.debit_account)} A/c Dr</div>
        <div class="entry-credit">To ${escHtml(e.credit_account)} A/c</div>
      </div>
      <div class="entry-meta">
        <span class="entry-amount">${fmtAmount(e.amount)}</span>
        <span class="entry-time">${fmtTime(e.created_at)}</span>
      </div>
    </div>
  `).join('');
}

/* ─── Delete entry ───────────────────────────────────────────────────────── */
async function deleteEntry(id, evt) {
  evt.stopPropagation();
  try {
    const res = await fetch(API.delete(id), { method: 'DELETE' });
    const data = await res.json();
    if (data.success) { toast('Entry deleted.', 'info'); loadEntries(); }
  } catch(e) { toast('Could not delete entry.', 'error'); }
}

/* ─── Clear all ──────────────────────────────────────────────────────────── */
async function clearAll() {
  if (!confirm('Delete all journal entries?')) return;
  try {
    await fetch(API.clear, { method: 'POST' });
    toast('All entries cleared.', 'info');
    loadEntries();
  } catch(e) { toast('Could not clear entries.', 'error'); }
}

/* ─── Escape HTML ─────────────────────────────────────────────────────────── */
function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ─── Keyboard shortcuts ─────────────────────────────────────────────────── */
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    generateEntry();
  }
});

/* ─── Wire buttons ───────────────────────────────────────────────────────── */
generateBtn.addEventListener('click', generateEntry);
clearBtn.addEventListener('click', () => {
  input.value = '';
  outputSec.classList.remove('visible');
  input.focus();
});
copyBtn.addEventListener('click', copyOutput);
clearAllBtn.addEventListener('click', clearAll);

/* ─── Init ───────────────────────────────────────────────────────────────── */
window.deleteEntry = deleteEntry; // expose for inline onclick
loadEntries();
input.focus();
