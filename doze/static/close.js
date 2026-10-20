'use strict';
const byId = id => document.getElementById(id);
const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
let session, inputs, inspected, closeProfile, closeWorkflow, closeReport, benchReport, yearReport, teachingEvidence, activeScenario = 'messy', week = 1, busy = false, toastTimer;
const profilePayload = () => closeWorkflow ? { ...closeWorkflow, profile: closeProfile } : closeProfile;
const mappingComplete = () => closeProfile && ['payments', 'bank'].every(side => {
  const values = Object.values(closeProfile.mapping[side]);
  return values.every(value => closeProfile.schemas[side].includes(value)) && new Set(values).size === values.length;
});

function toast(text, error = false) {
  clearTimeout(toastTimer);
  byId('close-toast').textContent = text; byId('close-toast').className = error ? 'error' : ''; byId('close-toast').hidden = false;
  toastTimer = setTimeout(() => { byId('close-toast').hidden = true; }, error ? 14000 : 6500);
}
async function request(path, body) {
  const response = await fetch('/api/' + path, body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Doze-Token': session.token }, body: JSON.stringify(body)
  });
  if (!response.ok) { const error = await response.json(); throw new Error(error.error || 'Local request failed.'); }
  return response.headers.get('Content-Type')?.includes('application/zip') ? response.blob() : response.json();
}
function gates() {
  byId('teach').disabled = busy || !session?.inference_enabled || !inspected || !byId('headers-approved').checked || !byId('close-model').options.length || !byId('close-model').value;
  byId('reconcile').disabled = busy || !mappingComplete() || !inspected || !byId('mapping-approved').checked || (closeWorkflow && (!benchReport || benchReport.passed !== benchReport.total));
  byId('download-packet').disabled = busy || !closeReport?.ready || !byId('report-approved').checked;
  byId('sleep').textContent = session?.inference_enabled ? '◉ AI awake' : '◌ AI asleep / blocked';
  byId('sleep').classList.toggle('asleep', !session?.inference_enabled);
  byId('test-mapping').disabled = busy || !closeProfile;
  byId('export-workflow').disabled = busy || !benchReport || benchReport.passed !== benchReport.total;
  byId('run-year').disabled = busy || !closeProfile || session?.inference_enabled || !benchReport || benchReport.passed !== benchReport.total;
  if (!session?.inference_enabled && !byId('close-model').value && byId('close-model').options.length) byId('close-model').options[0].textContent = 'AI asleep / wake to choose model';
}
async function work(label, action) {
  if (busy) return;
  busy = true; byId('close-busy-label').textContent = label; byId('close-busy').hidden = false;
  const controls = new Map([...document.querySelectorAll('button,select,input,textarea')].map(n => [n, n.disabled]));
  controls.forEach((_, n) => { n.disabled = true; });
  try { await action(); } catch (error) { toast(error.message, true); }
  finally { busy = false; byId('close-busy').hidden = true; controls.forEach((disabled, n) => { if (n.isConnected) n.disabled = disabled; }); gates(); }
}
function invalidate() {
  closeReport = null; byId('results').hidden = true; byId('report-approved').checked = false; gates();
}
function download(name, value, type = 'application/json') {
  const blob = value instanceof Blob ? value : new Blob([typeof value === 'string' ? value : JSON.stringify(value, null, 2)], { type });
  const url = URL.createObjectURL(blob); const link = node('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function currentInputs() { return { payments_csv: byId('payments-csv').value, bank_csv: byId('bank-csv').value }; }
async function inspectInputs() {
  inputs = currentInputs(); inspected = undefined; invalidate();
  byId('headers-approved').checked = false; byId('mapping-approved').checked = false;
  const result = await request('close/inspect', inputs);
  inspected = result; byId('header-preview').replaceChildren();
  for (const side of ['payments', 'bank']) {
    byId(side + '-info').textContent = `${result[side].records} records · ${result[side].headers.length} columns`;
    byId('header-preview').append(node('strong', side === 'payments' ? 'PAYMENT COLUMN NAMES' : 'BANK COLUMN NAMES'), node('div', result[side].headers.join(' · ')));
  }
}
async function loadScenario(scenario, next = false) {
  if (next) week = week === 52 ? 1 : week + 1;
  const data = await request('close/demo', { scenario, week }); activeScenario = scenario;
  byId('source-mode').textContent = `SYNTHETIC / WEEK ${week}`;
  byId('payments-csv').value = data.payments_csv; byId('bank-csv').value = data.bank_csv;
  document.querySelectorAll('[data-scenario]').forEach(b => b.classList.toggle('active', b.dataset.scenario === scenario));
  await inspectInputs();
}
function showProfile(result) {
  closeWorkflow = result.profile.format === 'doze-close-workflow-v1' ? result.profile : null;
  closeProfile = closeWorkflow ? closeWorkflow.profile : result.profile;
  clearProof(); invalidate(); byId('mapping-panel').hidden = false; byId('proof-panel').hidden = false; byId('mapping-approved').checked = false;
  byId('mapping-name').textContent = closeProfile.mapping.name; byId('mapping-fields').replaceChildren();
  byId('decimal-mark').value = closeProfile.mapping.decimal_mark;
  const origin = result.provenance;
  byId('mapping-origin').textContent = origin?.model ? 'LEARNED LOCALLY' : origin?.source?.includes('hand-written') ? 'HAND-WRITTEN SAMPLE' : 'IMPORTED / REVIEW REQUIRED';
  byId('learned-info').hidden = false;
  byId('learned-info').textContent = origin?.model
    ? `Learned by ${origin.model} in ${origin.seconds}s. Only column names and your explicit explanation were sent. Review every role below.`
    : origin?.source || 'Imported mapping. Revalidated locally. Review every role before reuse.';
  for (const side of ['payments', 'bank']) {
    const box = node('div', undefined, 'mapping-side'); box.append(node('h3', side === 'payments' ? 'PAYMENT EXPORT → MEANING' : 'BANK EXPORT → MEANING'));
    for (const [role, column] of Object.entries(closeProfile.mapping[side])) {
      const row = node('div', undefined, 'mapping-field'); const label = node('label', role.toUpperCase());
      const select = node('select'); select.id = `map-${side}-${role}`; label.htmlFor = select.id;
      const placeholder = node('option', 'Choose the column…'); placeholder.value = ''; select.append(placeholder);
      for (const header of closeProfile.schemas[side]) { const option = node('option', header); option.value = header; select.append(option); }
      select.value = column;
      select.onchange = () => { closeProfile.mapping[side][role] = select.value; mappingChanged(); };
      row.append(label, select); box.append(row);
    }
    byId('mapping-fields').append(box);
  }
  if (closeWorkflow) showBench(closeWorkflow.proof);
  gates(); byId('mapping-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function clearProof() {
  benchReport = null; yearReport = null; byId('witness-results').replaceChildren(); byId('year-panel').hidden = true;
}
function mappingChanged() {
  byId('mapping-approved').checked = false; byId('mapping-origin').textContent = 'EDITED / REVIEW REQUIRED';
  byId('learned-info').textContent = 'Mapping edited by you. Earlier model provenance and fixture results do not certify this version.';
  clearProof(); invalidate();
}
function showBench(proof) {
  benchReport = proof; byId('witness-results').replaceChildren();
  for (const check of proof.checks) {
    const card = node('div', `${check.passed ? 'PASS' : 'FAIL'} / ${check.name}`, 'witness' + (check.passed ? '' : ' failed'));
    if (!check.passed) card.append(node('small', 'Expected: ' + JSON.stringify(check.expected)), node('small', 'Observed: ' + JSON.stringify(check.observed)));
    byId('witness-results').append(card);
  }
  gates();
}
function showYear(report) {
  yearReport = report; byId('year-panel').hidden = false; byId('year-stats').replaceChildren(); byId('year-grid').replaceChildren();
  for (const [value, label] of [[report.clean_weeks, 'clean weeks'], [report.held_weeks, 'weeks held for review'], [report.exceptions, 'explicit exceptions'], [report.model_calls, 'model calls']]) {
    const stat = node('div', undefined, 'year-stat'); stat.append(node('strong', value), node('span', label)); byId('year-stats').append(stat);
  }
  for (const item of report.weeks) {
    const button = node('button', String(item.week).padStart(2, '0'), 'week-cell' + (item.ready ? '' : ' held'));
    const description = `Week ${item.week}: ${item.scenario}, ${item.matched} matched, ${item.exceptions} exceptions. ${item.ready ? 'Clean' : 'Handoff blocked'}.`;
    button.title = description; button.setAttribute('aria-label', description);
    button.onclick = () => { byId('year-detail').textContent = description + ' Report SHA-256: ' + item.report_sha256; };
    byId('year-grid').append(button);
  }
  byId('year-detail').textContent = `${report.payments.toLocaleString()} synthetic payments checked in ${report.seconds}s. Not real history or measured human time saved. Choose any week for its verdict.`;
}
function amount(value, currency = '') {
  if (value === null || value === undefined) return '—';
  // Format the already-computed decimal string. Never use binary floats to calculate money.
  const [whole, cents = '00'] = value.split('.');
  return `${currency ? currency + ' ' : ''}${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}.${cents}`;
}
function showSettlement(settlement) {
  const inspector = byId('inspector'); inspector.replaceChildren();
  inspector.append(node('p', 'THE PAPER TRAIL / EXACT SOURCE RECORDS', 'eyebrow'), node('h3', settlement.batch), node('p', settlement.reason));
  inspector.append(node('div', `${amount(settlement.gross)} − ${amount(settlement.fees)} = ${amount(settlement.expected)}\nBank: ${amount(settlement.received)}\nDifference: ${amount(settlement.difference)} ${settlement.currency}`, 'equation'));
  for (const side of ['payments', 'bank']) {
    const records = settlement[side === 'payments' ? 'payment_records' : 'bank_records'];
    const list = node('div', undefined, 'record-list'); list.append(node('p', `${side.toUpperCase()} / DATA RECORDS (header excluded)`));
    for (const number of records) {
      const button = node('button', '#' + number);
      button.onclick = () => {
        const source = inspected[side].rows.find(r => r.record === number);
        inspector.querySelectorAll('.source-row').forEach(n => n.remove());
        inspector.append(node('pre', `${side} data record ${number}\n` + Object.entries(source.values).map(([key, value]) => `${key}: ${value}`).join('\n'), 'source-row'));
      };
      list.append(button);
    }
    inspector.append(list);
  }
  inspector.append(node('p', `Mapping: ${closeReport.profile_sha256.slice(0, 16)}\nPayment source: ${closeReport.source_sha256.payments.slice(0, 16)}\nBank source: ${closeReport.source_sha256.bank.slice(0, 16)}`, 'record-list'));
}
function showReport(report) {
  closeReport = report; byId('results').hidden = false; byId('report-approved').checked = false;
  byId('result-title').textContent = report.ready ? 'These exports reconcile exactly.' : 'Not quite. And we won’t pretend.';
  byId('money-totals').replaceChildren();
  for (const [currency, totals] of Object.entries(report.totals)) {
    for (const [key, label] of [['gross', 'CUSTOMERS PAID'], ['fees', 'PROCESSOR KEPT'], ['net', 'EXPECTED NET']]) {
      const card = node('div', undefined, 'money-stat'); card.append(node('label', label), node('strong', amount(totals[key])), node('small', currency)); byId('money-totals').append(card);
    }
  }
  byId('match-count').textContent = `${report.matched} matched / ${report.exceptions} exceptions`;
  byId('settlement-rows').replaceChildren();
  for (const settlement of report.settlements) {
    const row = node('tr'); const id = node('td'); const button = node('button', settlement.batch); button.onclick = () => showSettlement(settlement); id.append(button);
    const status = node('td'); status.append(node('span', settlement.status.toUpperCase(), 'verdict ' + settlement.status));
    row.append(id, node('td', amount(settlement.expected, settlement.currency)), node('td', amount(settlement.received, settlement.currency)), status);
    byId('settlement-rows').append(row);
  }
  byId('row-issues').replaceChildren();
  if (report.issues.length) byId('row-issues').append(node('p', 'Totals above include valid payment rows only. Quarantined records are excluded. This is not a complete close.'));
  for (const issue of report.issues) byId('row-issues').append(node('p', `${issue.source} record ${issue.record} / ${issue.id || 'no ID'}: ${issue.reason}`));
  const first = report.settlements.find(s => s.status !== 'matched') || report.settlements[0];
  if (first) showSettlement(first);
  byId('handoff-title').textContent = report.ready ? 'Your handoff is ready.' : 'A clean handoff is blocked.';
  byId('handoff-description').textContent = report.ready
    ? 'Four evidence files and a read-me: exact totals, source-record references and input hashes. This proves agreement between these exports, not that all transactions were exported. Check source completeness before relying on the handoff.'
    : 'The engine found unresolved exceptions. It will not export a misleading clean packet. Download the review evidence, check the original sources, then reconcile again.';
  byId('packet-contents').hidden = !report.ready; gates();
  byId('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
document.querySelectorAll('[data-scenario]').forEach(button => {
  button.onclick = () => work('Loading explicitly synthetic inputs…', () => loadScenario(button.dataset.scenario));
});
byId('next-week').onclick = () => work('Adding the next synthetic week. Reusing your mapping, not the model…', () => loadScenario('clean', true));
byId('inspect').onclick = () => work('Parsing the local CSVs. No inference…', inspectInputs);
for (const side of ['payments', 'bank']) {
  byId(side + '-file').onchange = () => work('Reading only the CSV you explicitly selected…', async () => {
    const file = byId(side + '-file').files[0];
    if (!file || file.size > 350000) throw new Error('Choose a UTF-8 CSV smaller than 350 KB.');
    byId(side + '-csv').value = await file.text(); byId('source-mode').textContent = 'YOUR EXPLICITLY SELECTED INPUTS';
    document.querySelectorAll('[data-scenario]').forEach(b => b.classList.remove('active'));
    await inspectInputs();
  });
  byId(side + '-csv').oninput = () => {
    inspected = undefined; byId('headers-approved').checked = false; byId('mapping-approved').checked = false;
    byId('source-mode').textContent = 'EDITED INPUTS / VERIFY ORIGIN';
    document.querySelectorAll('[data-scenario]').forEach(b => b.classList.remove('active')); invalidate();
  };
}
byId('headers-approved').onchange = gates;
byId('mapping-approved').onchange = gates;
byId('report-approved').onchange = gates;
byId('decimal-mark').onchange = () => { if (closeProfile) { closeProfile.mapping.decimal_mark = byId('decimal-mark').value; mappingChanged(); } byId('headers-approved').checked = false; gates(); };
byId('column-explanation').oninput = () => { byId('headers-approved').checked = false; gates(); };
byId('demo-explanation').onclick = () => {
  byId('column-explanation').value = 'In these synthetic exports, payment column "Payout group" and bank column "Settlement reference" contain the same shared payout ID. "Sale reference" identifies each sale; "Bank entry" identifies each bank row, not a payout. "Customer paid" is gross before fees. "Processor fee" is the fee. "Money received" is the bank net. "ISO currency" contains the currency code in each export.';
  byId('headers-approved').checked = false; gates();
};
byId('teach').onclick = () => work('Learning headers with your explicit column explanation. No CSV rows sent…', async () => {
  byId('teaching-status').hidden = true;
  const sent = { payment_headers: inspected.payments.headers, bank_headers: inspected.bank.headers,
    decimal_mark: byId('decimal-mark').value, model: byId('close-model').value, hint: byId('column-explanation').value, headers_approved: byId('headers-approved').checked };
  try {
    const result = await request('close/teach', sent);
    teachingEvidence = { sent, result }; showProfile(result); toast('Mapping learned. Now challenge it with the eight synthetic witnesses.');
  } catch (error) {
    teachingEvidence = { sent, error: error.message }; byId('teaching-status').hidden = false;
    byId('teaching-status').textContent = 'No mapping learned. ' + error.message + ' Explain the column meanings or use a reviewed manual mapping. There is no automatic retry.';
    throw error;
  }
});
byId('sample-mapping').onclick = () => work('Loading a hand-written example, not an AI result…', async () => showProfile(await request('close/sample-profile', {})));
byId('manual-mapping').onclick = () => {
  if (!inspected || busy) return;
  showProfile({ profile: { format: 'doze-close-v1', schemas: { payments: inspected.payments.headers, bank: inspected.bank.headers },
    mapping: { name: 'Manually reviewed export mapping', decimal_mark: byId('decimal-mark').value,
      payments: { id: '', batch: '', gross: '', fee: '', currency: '' }, bank: { id: '', batch: '', amount: '', currency: '' } } },
    provenance: { source: 'Manual mapping draft. Choose every role explicitly. No model was called.' } });
};
byId('import-mapping').onchange = () => work('Validating imported mapping locally…', async () => {
  const file = byId('import-mapping').files[0]; if (!file || file.size > 64000) throw new Error('Choose a mapping or workflow JSON smaller than 64 KB.');
  const validated = await request('close/profile', { profile: JSON.parse(await file.text()) });
  showProfile({ profile: validated }); byId('import-mapping').value = '';
});
byId('export-mapping').onclick = () => work('Validating a portable mapping…', async () => {
  closeProfile = await request('close/profile', { profile: closeProfile }); download('doze-close-profile.json', closeProfile);
});
byId('reconcile').onclick = () => work('Matching exact references and checking every cent. No model call…', async () => {
  const report = await request('close/reconcile', { ...inputs, profile: profilePayload(), mapping_approved: byId('mapping-approved').checked });
  showReport(report);
});
byId('export-review').onclick = () => download('doze-review-evidence.json', closeReport);
byId('download-packet').onclick = () => work('Recomputing the report against the exact approved hashes…', async () => {
  const blob = await request('close/packet', { ...inputs, profile: profilePayload(), mapping_approved: byId('mapping-approved').checked,
    report_approved: byId('report-approved').checked, approved_sha256: closeReport.sha256 });
  download('doze-friday-handoff.zip', blob); toast('Handoff downloaded. Source CSV contents were not included. Your originals were not edited.');
});
byId('test-mapping').onclick = () => work('Checking eight fixed synthetic outcomes. No model call…', async () => {
  showBench(await request('close/bench', { profile: closeProfile }));
  if (benchReport.passed === benchReport.total) closeWorkflow = await request('close/workflow', { profile: closeProfile });
  toast(`${benchReport.passed}/${benchReport.total} studio witnesses passed. ${benchReport.passed === benchReport.total ? 'This mapping can travel with its tests.' : 'Review the failed expectations. No passing workflow will be exported.'}`);
});
byId('export-workflow').onclick = () => work('Rechecking executable witnesses before export…', async () => {
  closeWorkflow = await request('close/workflow', { profile: closeProfile }); download('doze-close-workflow.json', closeWorkflow);
});
byId('run-year').onclick = () => work('Replaying 52 synthetic Fridays. Existing sources are untouched. No inference…', async () => {
  if (session.inference_enabled) throw new Error('Put AI to sleep first.');
  showYear(await request('close/year', { profile: profilePayload() }));
});
byId('export-year').onclick = () => download('doze-synthetic-year.json', yearReport);
byId('sleep').onclick = () => work('Changing Doze’s inference gate, not stopping shared Ollama…', async () => {
  const next = !session.inference_enabled; await request('inference', { enabled: next }); session.inference_enabled = next;
  if (next) await loadModels(); toast(next ? 'Local inference enabled. Teaching still requires explicit header approval.' : 'AI asleep. Server inference is blocked. Existing mappings still reconcile.');
});
async function loadModels() {
  try {
    const result = await request('models'); byId('close-model').replaceChildren();
    for (const model of result.models) { const option = node('option', model); option.value = model; byId('close-model').append(option); }
    const gemma = result.models.find(m => m.startsWith('gemma')); if (gemma) byId('close-model').value = gemma;
  } catch { byId('close-model').replaceChildren(); toast('Ollama is unavailable. Explore with a hand-written mapping or import an existing one.'); }
}
async function init() {
  try { session = await request('state'); await loadScenario('messy'); if (session.inference_enabled) await loadModels(); gates(); }
  catch (error) { toast(error.message, true); }
}
init();
