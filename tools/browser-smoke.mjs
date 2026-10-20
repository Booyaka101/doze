// Uses the user's existing Chrome CDP. No account pages or external websites touched.
import { mkdir, writeFile } from 'node:fs/promises';
if (!process.env.DOZE_CDP_DRIVER) throw new Error('Set DOZE_CDP_DRIVER to the cdp-chrome skill driver file URL.');
const { connectByUrl } = await import(process.env.DOZE_CDP_DRIVER);
await mkdir('evidence', { recursive: true });
await fetch('http://127.0.0.1:9222/json/new?http://127.0.0.1:8741', { method: 'PUT' });
const c = await connectByUrl('127.0.0.1:8741');
const check = (value, label) => { if (!value) throw new Error(label); };
const waitFor = async (expression, max = 100) => {
  for (let i = 0; i < max; i++) { if (await c.evaluate(expression)) return; await c.sleep(200); }
  throw new Error('Timed out: ' + expression);
};
const screenshot = async name => writeFile('evidence/' + name + '.png', Buffer.from(await c.screenshot(), 'base64'));
try {
  await c.send('Page.bringToFront');
  await c.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await c.navigate('http://127.0.0.1:8741/files', 1000);
  await waitFor('document.querySelector("#model").value.startsWith("gemma")');
  const errors = [];
  c.on(event => { if (event.method === 'Runtime.exceptionThrown') errors.push(event.params.exceptionDetails.text); });
  await c.clickSelector('#example');
  check(await c.evaluate('document.querySelector("#prompt").value.includes("PNG, JPG and WEBP")'), 'Prompt readback failed');
  await screenshot('01-studio');
  await c.clickSelector('#compile');
  await waitFor('!document.querySelector("#workbench").hidden && document.querySelector("#busy").hidden', 450);
  const provenance = await c.evaluate('document.querySelector("#compile-info").innerText');
  check(provenance.includes('gemma'), 'Live model provenance missing');
  await c.clickSelector('#probe');
  await waitFor('document.querySelector("#probe-results").innerText.includes("checks passed") && document.querySelector("#busy").hidden');
  check(await c.evaluate('document.querySelector("#probe-results").innerText.startsWith("9/9")'), 'Near-miss checks failed');
  await c.evaluate('document.querySelector("#workbench").scrollIntoView({block:"start"})');
  await screenshot('02-recipe-lab');
  await c.clickSelector('#sleep-ai');
  await waitFor('document.querySelector("#model-status").innerText.includes("Inference blocked") && document.querySelector("#busy").hidden');
  check(await c.evaluate('document.querySelector("#compile").disabled'), 'Compile button must be disabled');
  const gate = await c.evaluate(`(async()=>{const s=await(await fetch('/api/state')).json();const r=await fetch('/api/compile',{method:'POST',headers:{'Content-Type':'application/json','X-Doze-Token':s.token},body:JSON.stringify({prompt:'Sort screenshots into Shots',model:'gemma4:12b-it-qat',examples:s.sample_cases})});return {status:r.status,body:await r.json()}})()`);
  check(gate.status === 400 && gate.body.error.includes('asleep'), 'Server inference gate did not reject compilation');
  await c.clickSelector('#rehearse');
  await waitFor('!document.querySelector("#preview").hidden && document.querySelector("#busy").hidden');
  check(await c.evaluate('document.querySelectorAll("#move-list .move").length===5'), 'First rehearsal should have five moves');
  check(await c.evaluate('document.querySelector("#execute").disabled'), 'Approval gate should be closed');
  await screenshot('03-rehearsal');
  await c.clickSelector('#approve');
  check(await c.evaluate('!document.querySelector("#execute").disabled'), 'Approval checkbox did not enable run');
  await c.clickSelector('#execute');
  await waitFor('!document.querySelector("#receipts").hidden && document.querySelector("#busy").hidden');
  check(await c.evaluate('document.querySelector("#receipts-list").innerText.includes("COMPLETED")'), 'Completed receipt missing');
  await screenshot('04-receipt');
  await c.clickSelector('[data-tab="studio"]');
  await c.clickSelector('#next-batch');
  await waitFor('document.querySelector("#busy").hidden');
  await c.clickSelector('#rehearse');
  await waitFor('!document.querySelector("#preview").hidden && document.querySelector("#busy").hidden');
  check(await c.evaluate('document.querySelectorAll("#move-list .move").length===5'), 'New batch should match without inference');
  await c.clickSelector('#approve');
  await c.clickSelector('#execute');
  await waitFor('!document.querySelector("#receipts").hidden && document.querySelector("#busy").hidden');
  check(await c.evaluate('document.querySelectorAll(".receipt").length===2'), 'Second receipt missing');
  await c.clickSelector('#receipts-list .receipt .primary');
  await waitFor('document.querySelector("#busy").hidden');
  check(await c.evaluate('document.querySelector("#receipts-list .receipt").innerText.includes("UNDONE")'), 'Undo receipt missing');
  check(await c.evaluate('document.querySelector("#receipts-list .receipt .primary").disabled'), 'Undone button incorrectly enabled');
  await screenshot('05-undone');
  await c.send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await c.clickSelector('[data-tab="studio"]');
  await c.evaluate('window.scrollTo(0,0)'); await c.sleep(300);
  check(await c.evaluate('document.documentElement.scrollWidth <= 390'), 'Mobile horizontal overflow');
  await screenshot('06-mobile');
  const result = { provenance, inference_gate: gate, near_misses_passed: 9,
    first_batch_moves: 5, repeat_batch_moves: 5, repeat_inference_enabled: false,
    undo_verified: true, mobile_width: 390, mobile_overflow: false, errors,
    resource_hosts: await c.evaluate('Array.from(new Set(performance.getEntriesByType("resource").map(r=>new URL(r.name).host)))') };
  await writeFile('evidence/browser-smoke.json', JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
  await c.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await c.evaluate('window.scrollTo(0,0)');
} finally { await c.close(); }
process.exit(0);
