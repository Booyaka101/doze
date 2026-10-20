// Drives only the local sample app. One bounded real repair, no automatic retries.
import { mkdir, writeFile } from 'node:fs/promises';
if (!process.env.DOZE_CDP_DRIVER) throw new Error('Set DOZE_CDP_DRIVER to the cdp-chrome driver file URL.');
const { connectByUrl } = await import(process.env.DOZE_CDP_DRIVER);
const base = process.env.DOZE_URL || 'http://127.0.0.1:8742';
await mkdir('evidence', { recursive: true });
await fetch('http://127.0.0.1:9222/json/new?' + base, { method: 'PUT' });
const c = await connectByUrl(new URL(base).host);
const check = (v, label) => { if (!v) throw new Error(label); };
const until = async (expr, attempts = 150) => {
  for (let i = 0; i < attempts; i++) { if (await c.evaluate(expr)) return; await c.sleep(200); }
  throw new Error('Timeout: ' + expr);
};
const shot = async name => writeFile(`evidence/${name}.png`, Buffer.from(await c.screenshot(), 'base64'));
const post = async (route, body) => c.evaluate(`(async()=>{const s=await(await fetch('/api/state')).json();const r=await fetch('/api/${route}',{method:'POST',headers:{'Content-Type':'application/json','X-Doze-Token':s.token},body:JSON.stringify(${JSON.stringify(body)})});return {status:r.status,body:await r.json()}})()`);
try {
  await c.send('Page.bringToFront');
  await c.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await c.navigate(base, 1000);
  await until('document.querySelector("#model").value.startsWith("gemma")');
  await c.clickSelector('#example');
  await c.evaluate('document.querySelector(".teaching-board").scrollIntoView({block:"center"})');
  await shot('07-teach-with-examples');
  await c.clickSelector('#load-mistake');
  await until('document.querySelector("#busy").hidden && document.querySelector("#contract-status").innerText.includes("BLOCKED")');
  check(await c.evaluate('document.querySelector("#probe-results").innerText.includes("8/9")'), 'Recorded failure must be 8/9');
  const mistakenId = await c.evaluate('selected.id');
  const badPlan = await post('preview', { recipe_id: mistakenId });
  const blocked = await post('execute', { plan_id: badPlan.body.id, approved: true });
  check(blocked.status === 400 && blocked.body.error.includes('contract blocked'), 'Server must reject failed contract');
  await c.evaluate('document.querySelector("#workbench").scrollIntoView({block:"start"})');
  await shot('08-mistake-blocked');
  check(await c.evaluate('!document.querySelector("#repair").disabled'), 'Repair unavailable while inference enabled');
  await c.clickSelector('#repair');
  await until('document.querySelector("#busy").hidden && document.querySelector("#compile-info").innerText.includes("gemma")', 900);
  check(await c.evaluate('document.querySelector("#contract-status").className==="contract-pass"'), 'The single local repair did not pass');
  const learned = await c.evaluate('({recipe:selected.recipe,examples:selected.examples,certificate:selected.certificate,provenance:document.querySelector("#compile-info").innerText})');
  await writeFile('evidence/teaching-live-repair.json', JSON.stringify(learned, null, 2));
  await shot('09-repaired-contract');
  await c.clickSelector('#sleep-ai');
  await until('document.querySelector("#busy").hidden && document.querySelector("#model-status").innerText.includes("Inference blocked")');
  check(await c.evaluate('document.querySelector("#repair").disabled'), 'Repair must be disabled while asleep');
  const gate = await post('compile', { prompt: 'Please sort my screenshots', model: 'gemma4:12b-it-qat', examples: learned.examples });
  check(gate.status === 400 && gate.body.error.includes('asleep'), 'Inference gate did not reject a direct request');
  await c.clickSelector('#replay');
  await until('document.querySelector("#busy").hidden && document.querySelector("#replay-results").innerText.includes("150 moves")', 600);
  const report = await c.evaluate('replayReport');
  check(report.passed && report.files === 360 && report.all_hashes_verified && report.last_batch_undo_verified, 'Thirty-morning replay failed');
  await writeFile('evidence/thirty-mornings.json', JSON.stringify(report, null, 2));
  await c.evaluate('document.querySelector(".replay-lab").scrollIntoView({block:"center"})');
  await shot('10-thirty-mornings');
  await c.clickSelector('#rehearse');
  await until('document.querySelector("#busy").hidden && !document.querySelector("#preview").hidden');
  check(await c.evaluate('document.querySelector("#execute").disabled'), 'Unapproved run must remain disabled');
  await c.clickSelector('#approve');
  check(await c.evaluate('!document.querySelector("#execute").disabled'), 'Certified, approved run should be enabled');
  await c.clickSelector('#execute');
  await until('document.querySelector("#busy").hidden && !document.querySelector("#receipts").hidden');
  const receipt = await c.evaluate('(async()=>{const s=await(await fetch("/api/state")).json();return s.runs[0]})()');
  check(receipt.status === 'completed' && receipt.plan.certificate.certified, 'Receipt needs passing contract');
  await c.clickSelector('#receipts-list .receipt .primary');
  await until('document.querySelector("#busy").hidden');
  check(await c.evaluate('document.querySelector("#receipts-list .receipt").innerText.includes("UNDONE")'), 'Undo failed');
  await c.send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await c.clickSelector('[data-tab="studio"]');
  await c.evaluate('document.querySelector(".teaching-board").scrollIntoView({block:"start"})'); await c.sleep(200);
  check(await c.evaluate('document.documentElement.scrollWidth<=390'), 'Teaching UI overflows on mobile');
  await shot('11-teaching-mobile');
  const result = { recorded_mistake_passes: 8, contract_cases: 9, direct_execution_rejected: blocked,
    local_repair_attempts: 1, local_repair_passed: true, inference_gate: gate,
    replay: { days: report.days, files: report.files, moves: report.moves, model_calls: report.model_calls, hashes_verified: report.all_hashes_verified },
    certified_run_and_undo_verified: true, mobile_overflow: false };
  await writeFile('evidence/teaching-smoke.json', JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
  await c.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await c.evaluate('window.scrollTo(0,0)');
} finally { await c.close(); }
process.exit(0);
