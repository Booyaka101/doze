// One optional live model call. Every later operation uses deterministic code.
import { writeFile, readFile, access } from 'node:fs/promises';
if (!process.env.DOZE_CDP_DRIVER) throw new Error('Set DOZE_CDP_DRIVER to the bundled cdp-chrome driver URL.');
const { connectByUrl } = await import(process.env.DOZE_CDP_DRIVER);
const base = process.env.DOZE_URL || 'http://127.0.0.1:8743';
const c = await connectByUrl(new URL(base).host);
const check = (value, message) => { if (!value) throw new Error(message); };
const until = async (expr, attempts = 100) => {
  for (let i = 0; i < attempts; i++) { if (await c.evaluate(expr)) return; await c.sleep(200); }
  throw new Error('Timeout: ' + expr);
};
const idle = () => until('!busy');
const recorded = process.env.DOZE_MAPPING_SOURCE === 'recorded';
const outputPath = name => 'evidence/' + (recorded ? name.replace(/(\.[^.]+)$/, '-gemma$1') : name);
const capture = async name => writeFile(outputPath(name), Buffer.from(await c.screenshot(), 'base64'));
let live, source;
try {
  await c.send('Page.bringToFront'); await c.navigate(base, 600);
  await until('typeof inspected!=="undefined" && !!inspected && !!session');
  if (process.env.DOZE_LIVE_TEACH === '1') {
    let alreadyRecorded = false;
    try { await access('evidence/close-explained-teaching.json'); alreadyRecorded = true; } catch {}
    check(!alreadyRecorded, 'A teaching attempt is already recorded. Do not automatically repeat it.');
    if (!await c.evaluate('session.inference_enabled')) { await c.clickSelector('#sleep'); await idle(); }
    await until('byId("close-model").value.startsWith("gemma")');
    await c.clickSelector('#demo-explanation');
    check(await c.evaluate('!byId("headers-approved").checked'), 'New explanation needs renewed consent');
    await c.clickSelector('#headers-approved'); await c.clickSelector('#teach');
    await until('!busy && !!teachingEvidence', 900);
    live = await c.evaluate('teachingEvidence');
    await writeFile('evidence/close-explained-teaching.json', JSON.stringify(live, null, 2));
    check(live.result?.profile, 'Teaching refused or failed. Evidence saved. No automatic retry.');
    await writeFile('evidence/close-learned-profile.json', JSON.stringify(live.result.profile, null, 2));
    source = 'live Gemma mapping';
  } else if (recorded) {
    await c.clickSelector('#recorded-mapping'); await until('!!closeProfile && !busy');
    check(await c.evaluate('byId("mapping-origin").textContent === "RECORDED GEMMA RESULT" && byId("learned-info").textContent.includes("No model call")'), 'Recorded lesson must not imply a fresh teaching call');
    source = 'recorded Gemma output from close-grounded-teaching.json, no new inference';
  } else if (process.env.DOZE_MAPPING_SOURCE === 'sample') {
    await c.clickSelector('#sample-mapping'); await until('!!closeProfile && !busy');
    source = 'hand-written sample, not AI output';
  } else {
    const profile = JSON.parse(await readFile('evidence/close-learned-profile.json', 'utf8'));
    await c.evaluate(`showProfile({profile:${JSON.stringify(profile)},provenance:{source:"Recorded live Gemma mapping, revalidated below. No new inference."}})`);
    source = 'recorded live Gemma mapping';
  }
  await c.clickSelector('#test-mapping'); await idle();
  check(await c.evaluate('benchReport?.passed===8 && !!closeWorkflow'), 'Learned mapping must pass all eight witnesses');
  const learnedWorkflow = await c.evaluate('closeWorkflow');
  await writeFile(outputPath('close-tested-workflow.json'), JSON.stringify(learnedWorkflow, null, 2));
  if (await c.evaluate('session.inference_enabled')) { await c.clickSelector('#sleep'); await idle(); }
  const blocked = await c.evaluate('(async()=>{try{await request("close/teach",{headers_approved:true,payment_headers:inspected.payments.headers,bank_headers:inspected.bank.headers,model:"gemma4:12b-it-qat"});return false}catch(e){return e.message.includes("asleep")}})()');
  check(blocked, 'Server must reject teaching while asleep');
  await c.clickSelector('#run-year'); await until('!!yearReport && !busy');
  const year = await c.evaluate('yearReport');
  check(year.clean_weeks===41 && year.held_weeks===11 && year.exceptions===19 && year.model_calls===0, 'Year replay outcomes must match fixed truth');
  await writeFile(outputPath('close-synthetic-year.json'), JSON.stringify(year, null, 2));
  await c.evaluate('byId("proof-panel").scrollIntoView()'); await capture('16-close-witnesses-year.png');
  await c.clickSelector('.week-cell.held');
  check(await c.evaluate('byId("year-detail").textContent.includes("Handoff blocked")'), 'Held week must explain its verdict');
  await c.clickSelector('#mapping-approved'); await c.clickSelector('#reconcile'); await until('!!closeReport && !busy');
  check(await c.evaluate('!closeReport.ready && closeReport.exceptions===3'), 'Learned workflow must retain exception behavior');
  await c.evaluate('byId("map-payments-gross").value="Processor fee";byId("map-payments-gross").dispatchEvent(new Event("change"));byId("map-payments-fee").value="Customer paid";byId("map-payments-fee").dispatchEvent(new Event("change"))');
  check(await c.evaluate('!benchReport && !closeReport && byId("reconcile").disabled && byId("export-workflow").disabled'), 'Edit must invalidate report, tests and approval');
  const forgedBlocked = await c.evaluate('(async()=>{try{const raw=JSON.parse(JSON.stringify(profilePayload()));raw.proof={passed:999,total:999};await request("close/reconcile",{...inputs,profile:raw,mapping_approved:true});return false}catch(e){return e.message.includes("Workflow blocked")}})()');
  check(forgedBlocked, 'Server must recheck tests rather than trust forged proof');
  await c.clickSelector('#test-mapping'); await idle();
  const failed = await c.evaluate('benchReport');
  check(failed.passed<failed.total, 'Semantically swapped mapping must fail');
  await c.evaluate('byId("proof-panel").scrollIntoView()'); await capture('17-close-wrong-mapping.png');
  // Exercise the actual JSON import event. The API must rebuild the proof.
  const imported = structuredClone(learnedWorkflow); imported.proof = {passed:999,total:999};
  await c.evaluate(`(()=>{const transfer=new DataTransfer();transfer.items.add(new File([${JSON.stringify(JSON.stringify(imported))}],"workflow.json",{type:"application/json"}));byId("import-mapping").files=transfer.files;byId("import-mapping").dispatchEvent(new Event("change"))})()`);
  await idle();
  check(await c.evaluate('benchReport?.passed===8 && benchReport.total===8 && closeWorkflow?.proof.passed===8'), 'Actual import must recompute proof');
  await c.clickSelector('[data-scenario="clean"]'); await idle();
  await c.clickSelector('#mapping-approved'); await c.clickSelector('#reconcile'); await until('!!closeReport && !busy');
  check(await c.evaluate('closeReport.ready && closeReport.matched===4'), 'Imported workflow must reconcile clean exports');
  const packet = await c.evaluate('(async()=>{const blob=await request("close/packet",{...inputs,profile:profilePayload(),mapping_approved:true,report_approved:true,approved_sha256:closeReport.sha256});return {bytes:blob.size,signature:Array.from(new Uint8Array(await blob.arrayBuffer()).slice(0,2))}})()');
  check(packet.signature.join() === '80,75', 'Workflow handoff must be a ZIP');
  // Exercise the manual path with a genuinely different header vocabulary.
  const manualRoles = {payments:{id:'charge_id',batch:'payout_ref',gross:'gross_amount',fee:'fee_amount',currency:'currency'},bank:{id:'entry_id',batch:'payout_ref',amount:'net_amount',currency:'currency'}};
  await c.evaluate(String.raw`(()=>{const headers={payments:${JSON.stringify(Object.values(manualRoles.payments))},bank:${JSON.stringify(Object.values(manualRoles.bank))}};for(const side of ['payments','bank']){const input=byId(side+'-csv');const lines=input.value.split('\n');lines[0]=headers[side].join(',');input.value=lines.join('\n');input.dispatchEvent(new Event('input'));}})()`);
  await c.evaluate('byId("source-details").open=true');
  await c.clickSelector('#inspect'); await until('!!inspected && !busy'); await c.clickSelector('#manual-mapping');
  check(await c.evaluate('!mappingComplete() && byId("reconcile").disabled'), 'Manual draft must not silently choose roles');
  await c.evaluate(`(()=>{for(const [side,roles] of Object.entries(${JSON.stringify(manualRoles)})){for(const [role,column] of Object.entries(roles)){const select=byId('map-'+side+'-'+role);select.value=column;select.dispatchEvent(new Event('change'));}}})()`);
  await c.clickSelector('#mapping-approved'); await c.clickSelector('#reconcile'); await until('!!closeReport && !busy');
  check(await c.evaluate('closeReport.ready && !session.inference_enabled && !closeWorkflow'), 'Explicitly mapped custom schemas must work without inference');
  await c.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await c.evaluate('byId("proof-panel").scrollIntoView()'); await c.sleep(300);
  const mobile = await c.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})');
  check(mobile.width===mobile.scroll,'Mobile proof panel must not overflow'); await capture('18-close-workflow-mobile.png');
  await c.send('Emulation.clearDeviceMetricsOverride');
  await c.clickSelector('[data-scenario="clean"]'); await idle();
  // Leave the demo showing the verified mapping and its honest source label.
  const checked = await c.evaluate(`request('close/profile',{profile:${JSON.stringify(learnedWorkflow)}})`);
  const provenance = recorded ? JSON.parse(await readFile('doze/close_recorded.json', 'utf8')).provenance : live?.result?.provenance || {source};
  await c.evaluate(`showProfile({profile:${JSON.stringify(checked)},provenance:${JSON.stringify(provenance)}});showYear(${JSON.stringify(year)});window.scrollTo(0,0)`);
  await capture('19-close-workflow-studio.png');
  const evidence = {synthetic:true,mapping_source:source,live_model_call_this_run:!!live,profile_sha256:learnedWorkflow.profile.sha256,
    witnesses_passed:8,wrong_mapping_passed:failed.passed,wrong_mapping_total:failed.total,forged_proof_blocked:forgedBlocked,
    edits_invalidate_approval:true,actual_import_rechecked:true,custom_schema_manually_reconciled:true,inference_blocked:blocked,year,packet,mobile,recurring_model_calls:0};
  await writeFile(outputPath('close-workflow-smoke.json'),JSON.stringify(evidence,null,2));
  console.log(JSON.stringify({witnesses:8,wrong_mapping_passed:failed.passed,forged_proof_blocked:forgedBlocked,year:{clean:year.clean_weeks,held:year.held_weeks,exceptions:year.exceptions,seconds:year.seconds},packet,mobile},null,2));
} finally { await c.close(); }
process.exit(0);
