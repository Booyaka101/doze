// Synthetic browser proof. One model call only when DOZE_LIVE_TEACH=1.
import { writeFile } from 'node:fs/promises';
if (!process.env.DOZE_CDP_DRIVER) throw new Error('Set DOZE_CDP_DRIVER to the bundled driver URL.');
const { connectByUrl } = await import(process.env.DOZE_CDP_DRIVER);
const base = process.env.DOZE_URL || 'http://127.0.0.1:8743';
const c = await connectByUrl(new URL(base).host);
const check = (ok, message) => { if (!ok) throw new Error(message); };
const until = async (expr, attempts = 100) => {
  for (let i = 0; i < attempts; i++) { if (await c.evaluate(expr)) return; await c.sleep(200); }
  throw new Error('Timeout: ' + expr);
};
const idle = () => until('!busy');
const capture = async name => writeFile('evidence/' + name, Buffer.from(await c.screenshot(), 'base64'));
try {
  await c.send('Page.bringToFront');
  await c.navigate(base, 700);
  await until('typeof inspected!=="undefined" && !!inspected && !!session');
  if (process.env.DOZE_LIVE_TEACH === '1') {
    check(await c.evaluate('session.inference_enabled'), 'Start live run with inference enabled');
    await until('document.querySelector("#close-model").value.startsWith("gemma")');
    await c.clickSelector('#headers-approved');
    await c.clickSelector('#teach');
    await until('!busy', 900);
    check(await c.evaluate('!!closeProfile'), 'Teaching did not produce a mapping. Inspect the visible error; do not automatically retry.');
  } else {
    await c.clickSelector('#sample-mapping'); await until('!!closeProfile && !busy');
  }
  const learned = await c.evaluate('({profile:closeProfile,description:document.querySelector("#learned-info").textContent,origin:document.querySelector("#mapping-origin").textContent})');
  if (await c.evaluate('session.inference_enabled')) { await c.clickSelector('#sleep'); await idle(); }
  const blocked = await c.evaluate('(async()=>{try{await request("close/teach",{payment_headers:inspected.payments.headers,bank_headers:inspected.bank.headers,headers_approved:true,model:"gemma4:12b-it-qat"});return false}catch(e){return e.message.includes("asleep")}})()');
  check(blocked, 'Server must block teaching while asleep');
  await c.clickSelector('#mapping-approved'); await c.clickSelector('#reconcile'); await until('!!closeReport && !busy');
  const messy = await c.evaluate('closeReport');
  check(!messy.ready && messy.exceptions === 3, 'Messy week must block clean handoff');
  check(await c.evaluate('document.querySelector("#download-packet").disabled'), 'Exception download must be disabled');
  await c.evaluate('document.querySelector("#results").scrollIntoView()'); await capture('12-close-exceptions.png');
  await c.clickSelector('[data-scenario="penny"]'); await idle();
  await c.clickSelector('#mapping-approved'); await c.clickSelector('#reconcile'); await until('!!closeReport && !busy');
  check(await c.evaluate('!closeReport.ready && closeReport.settlements.some(s=>s.difference==="-0.01")'), 'One cent must be blocking');
  await c.clickSelector('#next-week'); await idle();
  await c.clickSelector('#mapping-approved'); await c.clickSelector('#reconcile'); await until('!!closeReport && !busy');
  const clean = await c.evaluate('closeReport'); check(clean.ready && clean.matched === 4, 'Next week must reuse mapping');
  const packet = await c.evaluate('(async()=>{const b=await request("close/packet",{...inputs,profile:closeProfile,mapping_approved:true,report_approved:true,approved_sha256:closeReport.sha256});return {size:b.size,type:b.type,signature:Array.from(new Uint8Array(await b.arrayBuffer()).slice(0,2))}})()');
  check(packet.size > 1000 && packet.signature.join() === '80,75', 'Approved ZIP must download');
  await c.clickSelector('#report-approved');
  check(await c.evaluate('!document.querySelector("#download-packet").disabled'), 'Reviewed clean report should unlock download');
  await c.evaluate('window.scrollTo(0,0)'); await capture('13-close-learned.png');
  await c.evaluate('document.querySelector("#results").scrollIntoView()'); await capture('14-close-clean.png');
  await c.clickSelector('[data-scenario="drift"]'); await idle();
  await c.clickSelector('#mapping-approved'); await c.clickSelector('#reconcile'); await idle();
  check(await c.evaluate('!closeReport && document.querySelector("#close-toast").textContent.includes("Schema drift")'), 'Drift must stop reconciliation');
  await c.clickSelector('[data-scenario="clean"]'); await idle();
  await c.clickSelector('#mapping-approved'); await c.clickSelector('#reconcile'); await until('!!closeReport && !busy');
  await c.send('Emulation.setDeviceMetricsOverride', {width:390,height:844,deviceScaleFactor:1,mobile:true});
  await c.evaluate('window.scrollTo(0,0)'); await c.sleep(300);
  const mobile = await c.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})');
  check(mobile.scroll <= mobile.width, 'Mobile must not overflow'); await capture('15-close-mobile.png');
  await c.send('Emulation.clearDeviceMetricsOverride');
  const evidence = {synthetic:true, learned, messy, clean, packet, inference_blocked:blocked, penny_blocked:true, schema_drift_blocked:true, mobile, recurring_model_calls:0};
  await writeFile('evidence/close-smoke.json', JSON.stringify(evidence,null,2));
  console.log(JSON.stringify({origin:learned.origin,messy_exceptions:messy.exceptions,next_week_matched:clean.matched,packet,inference_blocked:blocked,mobile},null,2));
} finally { await c.close(); }
process.exit(0);
