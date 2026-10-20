// Targeted check of the custom-schema path. No model calls or replay reruns.
import { readFile, writeFile } from 'node:fs/promises';
const { connectByUrl } = await import(process.env.DOZE_CDP_DRIVER);
const base = process.env.DOZE_URL || 'http://127.0.0.1:8743';
const c = await connectByUrl(new URL(base).host);
const check = (value, message) => { if (!value) throw new Error(message); };
const until = async expr => {
  for (let i = 0; i < 100; i++) { if (await c.evaluate(expr)) return; await c.sleep(200); }
  throw new Error('Timeout: ' + expr);
};
try {
  await c.navigate(base, 600); await until('typeof inspected!=="undefined" && !!inspected');
  check(await c.evaluate('!session.inference_enabled'), 'Keep inference asleep');
  await c.clickSelector('[data-scenario="clean"]'); await until('!busy');
  const roles = {payments:{id:'charge_id',batch:'payout_ref',gross:'gross_amount',fee:'fee_amount',currency:'currency'},bank:{id:'entry_id',batch:'payout_ref',amount:'net_amount',currency:'currency'}};
  await c.evaluate(String.raw`(()=>{const headers={payments:${JSON.stringify(Object.values(roles.payments))},bank:${JSON.stringify(Object.values(roles.bank))}};for(const side of ['payments','bank']){const input=byId(side+'-csv');const lines=input.value.split('\n');lines[0]=headers[side].join(',');input.value=lines.join('\n');input.dispatchEvent(new Event('input'));}})()`);
  check(await c.evaluate('byId("source-mode").textContent.includes("EDITED INPUTS")'), 'Edited inputs must not retain a synthetic-origin claim');
  await c.evaluate('byId("source-details").open=true');
  await c.clickSelector('#inspect'); await until('!!inspected && !busy'); await c.clickSelector('#manual-mapping');
  check(await c.evaluate('!mappingComplete() && byId("reconcile").disabled'), 'Draft must not choose roles automatically');
  await c.evaluate(`(()=>{for(const [side,columns] of Object.entries(${JSON.stringify(roles)})){for(const [role,column] of Object.entries(columns)){const select=byId('map-'+side+'-'+role);select.value=column;select.dispatchEvent(new Event('change'));}}})()`);
  await c.clickSelector('#mapping-approved'); await c.clickSelector('#reconcile'); await until('!!closeReport && !busy');
  const report = await c.evaluate('closeReport');
  check(report.ready && report.matched===4,'Reviewed custom schema must reconcile without inference');
  await c.evaluate('byId("map-payments-fee").value="gross_amount";byId("map-payments-fee").dispatchEvent(new Event("change"))');
  check(await c.evaluate('!mappingComplete() && !closeReport && byId("reconcile").disabled'),'Duplicate role assignment must invalidate approval');
  await c.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await c.evaluate('byId("proof-panel").scrollIntoView()'); await c.sleep(200);
  const mobile=await c.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})');
  check(mobile.width===mobile.scroll,'Custom mapping must not overflow mobile');
  await writeFile('evidence/18-close-workflow-mobile.png',Buffer.from(await c.screenshot(),'base64'));
  await c.send('Emulation.clearDeviceMetricsOverride');
  await c.clickSelector('[data-scenario="clean"]'); await until('!busy');
  const workflow=JSON.parse(await readFile('evidence/close-tested-workflow.json','utf8'));
  const year=JSON.parse(await readFile('evidence/close-synthetic-year.json','utf8'));
  await c.evaluate(`showProfile({profile:${JSON.stringify(workflow)},provenance:{source:"hand-written sample, not AI output"}});showYear(${JSON.stringify(year)});window.scrollTo(0,0)`);
  await writeFile('evidence/19-close-workflow-studio.png',Buffer.from(await c.screenshot(),'base64'));
  const evidence={synthetic:true,custom_schema_manually_reconciled:true,blank_roles_blocked:true,duplicate_roles_blocked:true,edited_origin_label_correct:true,model_calls:0,mobile,report};
  await writeFile('evidence/close-manual-smoke.json',JSON.stringify(evidence,null,2));
  console.log(JSON.stringify({matched:report.matched,custom_schema:true,duplicate_roles_blocked:true,mobile,model_calls:0},null,2));
} finally { await c.close(); }
process.exit(0);
