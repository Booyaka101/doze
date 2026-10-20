'use strict';
const $ = id => document.getElementById(id);
let state, selected, plan, replayReport, locked = false;
let toastTimer;
// The same explicit teaching examples are used before and after compilation.
$('teaching-input').append($('probe-cases'));
function teachingCases() {
  return $('probe-cases').value.split('\n').filter(line => line.trim()).map(line => {
    const parts = line.split(/→|=>/).map(s => s.trim());
    if (parts.length !== 2) throw new Error('Use filename → Folder or filename → HOLD, one per line.');
    const [name, size] = parts[0].split('|').map(s => s.trim());
    return { name, expected: parts[1], ...(size === undefined ? {} : { bytes: Number(size) }) };
  });
}
function exported(saved) { return { format: 'doze-recipe-v1', recipe: saved.recipe, examples: saved.examples }; }
function updateGates() {
  $('execute').disabled = locked || !$('approve').checked || !plan?.moves.length || !selected?.certificate?.certified;
  $('repair').disabled = locked || !state?.inference_enabled || !$('model').value || $('compile').disabled;
}
function assertSavedTeaching() {
  if (JSON.stringify(teachingCases()) !== JSON.stringify(selected.examples)
      || JSON.stringify(JSON.parse($('recipe-json').value)) !== JSON.stringify(selected.recipe)) {
    throw new Error('You have unsaved examples or rule edits. Save the contract or rules before rehearsing.');
  }
}
for (const id of ['probe-cases', 'recipe-json']) $(id).addEventListener('input', () => {
  plan = null; $('preview').hidden = true; $('approve').checked = false;
  if (selected) {
    $('contract-status').className = 'contract-fail';
    $('contract-status').textContent = 'UNSAVED CHANGES · Save your rules or teaching contract before rehearsing again.';
  }
  updateGates();
});
function contractView(saved) {
  const cert = saved.certificate;
  const passed = cert?.cases.filter(c => c.passed).length || 0;
  $('contract-status').className = cert?.certified ? 'contract-pass' : 'contract-fail';
  $('contract-status').textContent = cert?.certified
    ? `READY TO REHEARSE · ${passed}/${cert.cases.length} examples passed · contract ${cert.examples_sha256.slice(0, 12)}`
    : `EXECUTION BLOCKED · ${passed}/${cert?.cases.length || 0} examples passed. ${cert?.missing_destinations.length ? 'Missing examples for: ' + cert.missing_destinations.join(', ') + '. ' : ''}${cert && !cert.has_hold ? 'Add a HOLD example. ' : ''}Correct the rules or your expectations, then save a new version.`;
  $('probe-results').replaceChildren();
  if (cert) {
    $('probe-results').append(el('p', `${passed}/${cert.cases.length} checks passed · 0 model calls`, cert.certified ? 'probe-good' : 'probe-bad'));
    for (const c of cert.cases) {
      const row = el('div', undefined, 'probe-row' + (c.passed ? '' : ' probe-bad'));
      row.append(el('span', c.passed ? '✓' : '✕'), el('span', c.name), el('span', c.actual + (c.passed ? '' : ' (expected ' + c.expected + ')')));
      $('probe-results').append(row);
    }
  }
}
function el(tag, text, cls) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (cls) node.className = cls; return node; }
function notice(message, error = false) { clearTimeout(toastTimer); $('toast').textContent = message; $('toast').className = error ? 'error' : ''; $('toast').hidden = false; toastTimer = setTimeout(() => { $('toast').hidden = true; }, error ? 14000 : 6500); }
async function api(path, body) { const response = await fetch('/api/' + path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Doze-Token': state.token }, body: JSON.stringify(body) }); const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Local request failed.'); return data; }
async function task(label, action) { if (locked) return; locked = true; $('busy-label').textContent = label; $('busy').hidden = false; const buttons = new Map([...document.querySelectorAll('button')].map(b => [b, b.disabled])); buttons.forEach((_, b) => { b.disabled = true; }); try { await action(); } catch (error) { notice(error.message, true); } finally { locked = false; $('busy').hidden = true; buttons.forEach((disabled, b) => { if (b.isConnected) b.disabled = disabled; }); if (state && !state.inference_enabled) $('compile').disabled = true; updateGates(); } }
function tab(name) { for (const page of document.querySelectorAll('.page')) page.hidden = page.id !== name; for (const button of document.querySelectorAll('[data-tab]')) button.classList.toggle('active', button.dataset.tab === name); window.scrollTo({ top: 0, behavior: 'smooth' }); }
for (const b of document.querySelectorAll('[data-tab]')) b.addEventListener('click', () => tab(b.dataset.tab));
function bytes(n) { return n < 1024 ? n + ' B' : (n / 1024).toFixed(1) + ' KB'; }
async function refresh() {
  state = await api('state');
  $('sleep-ai').textContent = state.inference_enabled ? 'Put AI to sleep ↘' : 'Wake local AI ↗';
  if (!state.inference_enabled) { $('model-status').textContent = 'Asleep. Inference blocked.'; $('compile').disabled = true; }
  $('workspace-name').textContent = state.workspace.split(/[\\/]/).pop(); $('workspace-name').title = state.workspace;
  $('mode-label').textContent = state.demo ? 'SAMPLE WORKSPACE' : 'CUSTOM WORKSPACE';
  $('file-count').textContent = state.files.length;
  $('next-batch').hidden = !state.demo;
  $('file-list').replaceChildren();
  for (const file of state.files) { const row = el('div', undefined, 'file' + (file.held ? ' held' : '')); const ext = file.name.split('.').pop().slice(0, 4).toLowerCase(); row.append(el('span', ext.toUpperCase(), 'file-icon ' + ext), el('span', file.name, 'file-name'), el('span', file.held ? 'HELD' : bytes(file.size), 'file-size')); row.title = file.held || file.name; $('file-list').append(row); }
  if (!state.files.length) $('file-list').append(el('p', 'All quiet. Add a fresh batch to try your recipe again.', 'fine'));
  $('recipe-count').textContent = state.recipes.length; $('run-count').textContent = state.runs.length;
  renderShelf(); renderReceipts();
}
function choose(saved, provenance) {
  selected = saved; plan = null; $('preview').hidden = true; $('approve').checked = false; $('workbench').hidden = false; $('probe-results').replaceChildren();
  $('recipe-title').textContent = saved.recipe.name; $('recipe-description').textContent = saved.recipe.description;
  $('recipe-json').value = JSON.stringify(saved.recipe, null, 2); $('rules').replaceChildren();
  if (saved.examples?.length) $('probe-cases').value = saved.examples.map(c => c.name + (c.bytes === undefined ? '' : ' | ' + c.bytes) + ' → ' + c.expected).join('\n');
  contractView(saved);
  replayReport = null; $('replay-results').replaceChildren(); $('export-replay').hidden = true;
  saved.recipe.rules.forEach((rule, i) => { const row = el('div', undefined, 'rule'); const middle = el('div'); middle.append(el('strong', rule.label)); const conditions = Object.entries(rule.when).map(([key, value]) => key.replaceAll('_', ' ') + ': ' + (Array.isArray(value) ? value.join(' or ') : value)).join(' + '); middle.append(el('p', conditions)); row.append(el('span', String(i + 1).padStart(2, '0'), 'rule-number'), middle, el('span', '↳ ' + rule.folder, 'rule-dest')); $('rules').append(row); });
  if (provenance) { $('compile-info').hidden = false; $('compile-info').textContent = `Learned locally with ${provenance.model} in ${provenance.seconds}s. ${provenance.output_tokens ?? '?'} output tokens. The model’s job is done. Review the rules below.`; }
  else $('compile-info').hidden = true;
  tab('studio'); $('workbench').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function download(name, value) { const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' })); const link = el('a'); link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
function renderShelf() { $('recipe-shelf').replaceChildren(); if (!state.recipes.length) $('recipe-shelf').append(el('div', 'Nothing to repeat. Teach your first chore in the studio.', 'empty')); for (const saved of state.recipes) { const card = el('article', undefined, 'shelf-card'); card.append(el('h2', saved.recipe.name), el('p', saved.recipe.description), el('span', saved.certificate?.certified ? 'CONTRACT PASSED · model-free reuse' : 'EXECUTION BLOCKED · teach examples first', 'badge')); const actions = el('div', undefined, 'actions'); const open = el('button', 'Open recipe →', 'primary'); open.onclick = () => choose(saved); const exp = el('button', 'Export recipe + tests ↓', 'secondary'); exp.onclick = () => download('doze-recipe.json', exported(saved)); actions.append(open, exp); card.append(actions); $('recipe-shelf').append(card); } }
function renderReceipts() { $('receipts-list').replaceChildren(); if (!state.runs.length) $('receipts-list').append(el('div', 'Nothing has been moved. That is a perfectly good start.', 'empty')); for (const run of state.runs) { const card = el('article', undefined, 'receipt'); const top = el('div', undefined, 'receipt-top'); top.append(el('h2', run.plan.name), el('span', run.status.toUpperCase(), 'badge status-' + run.status)); card.append(top, el('div', new Date(run.created).toLocaleString() + ' · ' + run.id.slice(0, 12) + ' · 0 model calls', 'receipt-meta')); for (const action of run.actions) { const row = el('div', undefined, 'move'); row.append(el('span', action.source), el('span', run.status === 'undone' ? '←' : '→'), el('span', action.destination)); row.title = 'SHA-256: ' + action.sha256 + ' | ' + action.status; card.append(row); } const actions = el('div', undefined, 'actions'); const undo = el('button', run.status === 'undone' ? 'Restored. Afternoon saved.' : 'Undo these moves ↶', 'primary'); undo.disabled = run.status === 'undone'; undo.onclick = () => task('Checking hashes before undo…', async () => { await api('undo', { run_id: run.id }); await refresh(); notice('Files restored. No edits or existing files overwritten. Empty destination folders are kept.'); }); const exp = el('button', 'Export receipt ↓', 'secondary'); exp.onclick = () => download('doze-receipt-' + run.id.slice(0, 8) + '.json', run); actions.append(undo, exp); card.append(actions); $('receipts-list').append(card); } }
$('example').onclick = () => { $('prompt').value = state.sample_prompt; $('probe-cases').value = state.sample_cases.map(c => c.name + ' → ' + c.expected).join('\n'); $('prompt').focus(); };
$('sleep-ai').onclick = () => task('Changing Doze’s inference gate, not stopping shared Ollama…', async () => { await api('inference', { enabled: !state.inference_enabled }); await refresh(); notice(state.inference_enabled ? 'Local inference enabled. Refresh to reload installed models.' : 'AI asleep. The server now blocks inference. Rehearse and run existing recipes as usual.'); if (state.inference_enabled) window.location.reload(); });
$('compile').onclick = () => task('Learning general rules from your instructions and labelled examples…', async () => { const result = await api('compile', { prompt: $('prompt').value, model: $('model').value, examples: teachingCases() }); await refresh(); choose(result, result.provenance); notice(result.certificate?.certified ? 'Teaching contract passed. Inspect and rehearse before approving.' : 'The model failed your contract. Execution is blocked. Review the counterexamples.', !result.certificate?.certified); });
$('sample').onclick = () => task('Loading a hand-written sample, not an AI result…', async () => { const saved = await api('sample-recipe', {}); await refresh(); choose(saved); notice('Hand-written sample loaded. Local AI compilation is a separate, optional step.'); });
$('export').onclick = () => download('doze-recipe.json', exported(selected));
$('probe').onclick = () => task('Saving a new immutable teaching contract. No inference…', async () => { const saved = await api('certify', { recipe_id: selected.id, cases: teachingCases() }); await refresh(); choose(saved); notice(saved.certificate.certified ? 'Contract passed and saved. A new rehearsal is required.' : 'Contract failed. The server will refuse execution.', !saved.certificate.certified); });
$('repair').onclick = () => task('One local repair attempt using your examples and deterministic failures…', async () => { const result = await api('compile', { prompt: $('prompt').value || 'Repair the previous recipe to satisfy the user labelled examples. Preserve its intended general behavior.', model: $('model').value, previous_id: selected.id, examples: teachingCases() }); await refresh(); choose(result, result.provenance); notice(result.certificate.certified ? 'Repair passed your contract. Inspect the new rules before approval.' : 'Repair still fails. No retry loop was started. Inspect the failing examples.', !result.certificate.certified); });
$('load-mistake').onclick = () => task('Replaying the recorded model mistake. Not new inference…', async () => { const saved = await api('mistake', {}); await refresh(); $('prompt').value = state.sample_prompt; choose(saved); notice('Recorded mistake loaded. screenshot-plan.txt fails. Try Repair, or edit the rules yourself.', true); });
$('replay').onclick = () => task('Actually moving and verifying 30 synthetic batches in an isolated workspace…', async () => {
  replayReport = await api('replay', { recipe_id: selected.id });
  $('replay-results').replaceChildren();
  if (!replayReport.passed) {
    $('replay-results').append(el('p', 'Scenario mismatch. No moves attempted.', 'probe-bad'));
    for (const c of replayReport.mismatches.slice(0, 5)) $('replay-results').append(el('p', `${c.name}: ${c.actual}, expected ${c.expected}`, 'fine'));
  } else {
    $('replay-results').append(el('h3', `${replayReport.moves} moves. Zero inference.`));
    const grid = el('div', undefined, 'day-grid');
    for (const batch of replayReport.batches) { const day = el('span', String(batch.day).padStart(2, '0')); day.title = `Day ${batch.day}: ${batch.moved} journalled moves, 0 model calls`; grid.append(day); }
    $('replay-results').append(grid, el('p', `${replayReport.files} synthetic files · ${replayReport.held} intentionally held · all hashes verified · last batch undo checked · ${replayReport.elapsed_seconds}s`, 'fine'));
  }
  $('export-replay').hidden = false;
});
$('export-replay').onclick = () => download('doze-thirty-mornings.json', replayReport);
$('save-edits').onclick = () => task('Validating rule changes against your teaching examples…', async () => { const saved = await api('recipe', { recipe: JSON.parse($('recipe-json').value), examples: teachingCases() }); await refresh(); choose(saved); notice('New version saved. Rehearse again before running.'); });
$('rehearse').onclick = () => task('Rehearsing locally. No model call…', async () => { assertSavedTeaching(); plan = await api('preview', { recipe_id: selected.id }); $('preview').hidden = false; $('approve').checked = false; $('move-list').replaceChildren(); for (const move of plan.moves) { const row = el('div', undefined, 'move'); row.append(el('span', move.source), el('span', '→'), el('span', move.destination)); row.title = move.rule + ' | SHA-256 ' + move.sha256; $('move-list').append(row); } if (!plan.moves.length) $('move-list').append(el('p', 'No matching files to move. Add a fresh sample batch or adjust the recipe.', 'fine')); const held = el('div', undefined, 'held-group'); held.append(el('strong', plan.held.length + ' left exactly where they are')); for (const file of plan.held) held.append(el('div', file.name + ' · ' + file.reason)); $('held-list').replaceChildren(held); $('preview').scrollIntoView({ behavior: 'smooth', block: 'start' }); });
$('approve').onchange = updateGates;
$('execute').onclick = () => task('Checking the approved hashes and journalling moves…', async () => { if (!$('approve').checked || !plan) throw new Error('Review and approve a rehearsal first.'); await api('execute', { plan_id: plan.id, approved: true }); plan = null; $('approve').checked = false; $('preview').hidden = true; await refresh(); tab('receipts'); notice('Chore done. Zero model calls. Your receipt and Undo are ready.'); });
$('next-batch').onclick = () => task('Adding synthetic sample files only…', async () => { const result = await api('demo', { batch: 'next' }); plan = null; $('preview').hidden = true; $('approve').checked = false; await refresh(); notice(result.added.length ? 'Tomorrow’s sample batch is ready. Rehearse your existing recipe, no model needed.' : 'Tomorrow’s sample batch is already present.'); });
$('import').onchange = () => task('Recomputing imported recipe tests locally, never trusting an imported badge…', async () => { const file = $('import').files[0]; if (!file || file.size > 64000) throw new Error('Choose a recipe JSON file smaller than 64 KB.'); const raw = JSON.parse(await file.text()); const saved = await api('recipe', raw.recipe ? { recipe: raw.recipe, examples: raw.examples } : { recipe: raw }); await refresh(); choose(saved); $('import').value = ''; notice('Imported. Contract recomputed locally. Bare recipes need teaching examples before execution.'); });
async function init() { try { await refresh(); } catch (error) { notice(error.message, true); return; } if (!state.inference_enabled) { $('model').replaceChildren(el('option', 'Inference is blocked by Doze')); return; } try { const result = await api('models'); $('model').replaceChildren(); for (const model of result.models) { const option = el('option', model); option.value = model; $('model').append(option); } const gemma = result.models.find(m => m.startsWith('gemma')); if (gemma) $('model').value = gemma; $('model-status').textContent = result.models.length ? $('model').value : 'No model installed'; $('compile').disabled = !result.models.length; if (!result.models.length) $('model').append(el('option', 'No local model installed')); } catch { $('model').replaceChildren(el('option', 'Ollama offline')); $('model-status').textContent = 'Asleep. Recipes still run.'; $('compile').disabled = true; } $('model').onchange = () => { $('model-status').textContent = $('model').value; }; }
init();
