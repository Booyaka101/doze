// Final browser regression using already-learned rules. Starts no model jobs.
import { writeFile } from 'node:fs/promises';
if (!process.env.DOZE_CDP_DRIVER) throw new Error('Set DOZE_CDP_DRIVER to the cdp-chrome driver URL.');
const { connectByUrl } = await import(process.env.DOZE_CDP_DRIVER);
const base = process.env.DOZE_URL || 'http://127.0.0.1:8742';
const c = await connectByUrl(new URL(base).host);
const check = (ok, message) => { if (!ok) throw new Error(message); };
const until = async expr => {
  for (let i = 0; i < 100; i++) { if (await c.evaluate(expr)) return; await c.sleep(100); }
  throw new Error('Timeout: ' + expr);
};
try {
  await c.send('Page.bringToFront');
  await c.navigate(base, 500);
  await until('typeof state!=="undefined" && !!state');
  await c.evaluate('(async()=>{await api("inference",{enabled:false})})()');
  await c.navigate(base, 500);
  await until('typeof state!=="undefined" && !!state && !state.inference_enabled');
  await c.evaluate('choose(state.recipes.find(r=>r.certificate?.certified))');
  await c.clickSelector('#rehearse');
  await until('document.querySelector("#busy").hidden && !document.querySelector("#preview").hidden');
  await c.clickSelector('#approve');
  check(await c.evaluate('!document.querySelector("#execute").disabled'), 'Saved contract should permit approval');
  await c.evaluate('document.querySelector("#probe-cases").value+="\\nnew-note.txt → HOLD";document.querySelector("#probe-cases").dispatchEvent(new Event("input",{bubbles:true}))');
  check(await c.evaluate('document.querySelector("#execute").disabled && document.querySelector("#preview").hidden'), 'Editing examples must invalidate approval');
  await c.clickSelector('#rehearse');
  await until('document.querySelector("#busy").hidden');
  check(await c.evaluate('document.querySelector("#toast").innerText.includes("unsaved")'), 'Rehearsal must reject unsaved examples');
  const oldId = await c.evaluate('selected.id');
  await c.clickSelector('#probe');
  await until('document.querySelector("#busy").hidden');
  check(await c.evaluate(`selected.id!==${JSON.stringify(oldId)} && selected.certificate.certified`), 'Saving contract needs a passing new version');
  const gate = await c.evaluate('(async()=>{try{await api("compile",{prompt:"Please sort screenshots",model:"gemma4:12b-it-qat",examples:teachingCases()});return false}catch(e){return e.message.includes("asleep")}})()');
  check(gate, 'Updated server inference gate must reject valid teaching requests');
  await c.clickSelector('#rehearse');
  await until('document.querySelector("#busy").hidden && !document.querySelector("#preview").hidden');
  await c.clickSelector('#approve');
  await c.clickSelector('#execute');
  await until('document.querySelector("#busy").hidden && !document.querySelector("#receipts").hidden');
  await c.clickSelector('#receipts-list .receipt .primary');
  await until('document.querySelector("#busy").hidden');
  check(await c.evaluate('document.querySelector("#receipts-list .receipt").innerText.includes("UNDONE")'), 'Updated certified run and undo must pass');
  await c.clickSelector('[data-tab="studio"]');
  await c.evaluate('window.scrollTo(0,0)');
  const report = { model_calls: 0, unsaved_edit_invalidated_approval: true,
    unsaved_rehearsal_blocked: true, save_created_new_version: true,
    valid_compile_request_rejected_while_asleep: true, certified_run_and_undo: true };
  await writeFile('evidence/teaching-regression.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} finally { await c.close(); }
process.exit(0);
