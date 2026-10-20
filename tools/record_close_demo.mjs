// Capture the running local tab at sampled frames and preserve real elapsed time.
// No inference, full-desktop capture, account data, upload or synthetic UI results.
import { mkdir, mkdtemp, writeFile, access } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { resolve } from 'node:path';

if (!process.env.DOZE_CDP_DRIVER) throw new Error('Set DOZE_CDP_DRIVER to the installed cdp-chrome driver URL.');
const { connectByUrl } = await import(process.env.DOZE_CDP_DRIVER);
const base = process.env.DOZE_URL || 'http://127.0.0.1:8743';
if (!['127.0.0.1', 'localhost'].includes(new URL(base).hostname)) throw new Error('Capture is local only.');
const destination = resolve('evidence/doze-friday-close.mp4');
try { await access(destination); throw new Error('Demo exists. Review it before deciding whether to make another take.'); }
catch (error) { if (error.code !== 'ENOENT') throw error; }
await mkdir('.doze', { recursive: true });
const directory = await mkdtemp(resolve('.doze/close-capture-'));
const c = await connectByUrl(new URL(base).host);
const recorder = await connectByUrl(new URL(base).host);
const assert = (value, message) => { if (!value) throw new Error(message); };
const until = async expression => {
  for (let i = 0; i < 100; i++) {
    if (await c.evaluate(expression)) return;
    await c.sleep(150);
  }
  throw new Error('Timed out: ' + expression);
};
const captions = [];
let capturing = false, captureTask, started, ended;
const frames = [];
async function caption(title) {
  captions.push({ seconds: Math.round((Date.now() - started) / 100) / 10, title });
  await c.evaluate(`document.getElementById('demo-caption-title').textContent=${JSON.stringify(title)}`);
}
async function hold(seconds) { await c.sleep(seconds * 1000); }
async function capture() {
  while (capturing) {
    const time = Date.now();
    const name = `frame-${String(frames.length).padStart(5, '0')}.jpg`;
    const image = (await recorder.send('Page.captureScreenshot', { format: 'jpeg', quality: 85 })).data;
    await writeFile(resolve(directory, name), Buffer.from(image, 'base64'));
    frames.push({ time, name });
    await recorder.sleep(Math.max(0, 333 - (Date.now() - time)));
  }
}
try {
  await c.send('Page.bringToFront');
  await c.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1080, deviceScaleFactor: 1, mobile: false });
  await c.navigate(base, 700);
  await until('typeof inspected !== "undefined" && !!inspected && !!session');
  assert(await c.evaluate('!session.inference_enabled'), 'Leave AI asleep. No live teaching is authorized by this recording script.');
  await c.evaluate(`(()=>{
    const bar=document.createElement('div');bar.id='demo-caption';
    bar.style.cssText='position:fixed;z-index:100000;bottom:0;left:0;right:0;padding:20px 44px 24px;background:#302b38;color:#fff;font-family:Segoe UI,sans-serif;border-top:3px solid #b7c69e;pointer-events:none';
    const label=document.createElement('div');label.textContent='FRAME-SAMPLED APP CAPTURE  /  SYNTHETIC EXPORTS  /  RECORDED GEMMA OUTPUT';label.style.cssText='font:11px Consolas,monospace;letter-spacing:1px;color:#cbc2d7;margin-bottom:10px';
    const title=document.createElement('div');title.id='demo-caption-title';title.style.cssText='font-size:23px;font-weight:500';
    bar.append(label,title);document.body.append(bar);document.body.style.paddingBottom='150px';
    window.scrollTo(0,0);
  })()`);
  started = Date.now(); capturing = true; captureTask = capture();
  await caption('Doze: teach the job once. Then let the AI sleep.'); await hold(5);
  await c.clickSelector('#recorded-mapping'); await until('!!closeProfile && !busy');
  assert(await c.evaluate('byId("mapping-origin").textContent === "RECORDED GEMMA RESULT"'), 'Origin disclosure missing.');
  await c.evaluate('byId("learned-info").scrollIntoView({block:"center"})');
  await caption('Saved output from a real local Gemma call. No new inference in this walkthrough.'); await hold(7);
  await c.clickSelector('#test-mapping'); await until('!!benchReport && !busy');
  assert(await c.evaluate('benchReport.passed === 8 && !!closeWorkflow'), 'Witness suite failed.');
  await c.evaluate('byId("proof-panel").scrollIntoView({block:"start"})');
  await caption('Eight fixed studio tests, including refunds, duplicates and the one-cent discrepancy.'); await hold(7);
  await c.clickSelector('#mapping-approved'); await c.clickSelector('#reconcile'); await until('!!closeReport && !busy');
  assert(await c.evaluate('!closeReport.ready && closeReport.exceptions === 3'), 'Messy week must remain blocked.');
  await caption('A messy week stays messy: three exceptions. A clean handoff is blocked.'); await hold(7);
  await c.evaluate('byId("inspector").scrollIntoView({block:"center"})');
  await c.clickSelector('#inspector .record-list button');
  await caption('Follow a discrepancy to the exact source record. The model does not decide the sums.'); await hold(7);
  await c.clickSelector('#next-week'); await until('!busy');
  await c.clickSelector('#mapping-approved'); await c.clickSelector('#reconcile'); await until('!!closeReport && !busy');
  assert(await c.evaluate('closeReport.ready && closeReport.matched === 4 && !session.inference_enabled'), 'Next-week reuse failed.');
  await caption('Next synthetic week. Same mapping. Four exact settlements. Inference still disabled.'); await hold(7);
  await c.clickSelector('#report-approved');
  assert(await c.evaluate('!byId("download-packet").disabled'), 'Reviewed clean packet should be available.');
  await c.evaluate('byId("handoff-title").scrollIntoView({block:"center"})');
  await caption('Review before handoff. Approval binds the exact report; source exports stay unchanged.'); await hold(7);
  await c.clickSelector('#run-year'); await until('!!yearReport && !busy');
  assert(await c.evaluate('yearReport.clean_weeks === 41 && yearReport.held_weeks === 11 && yearReport.model_calls === 0'), 'Replay outcome changed.');
  await c.evaluate('byId("year-panel").scrollIntoView({block:"center"})');
  await caption('52 generated weeks: 41 clean, 11 held for review. Zero model calls during replay.'); await hold(8);
  await c.clickSelector('.week-cell.held');
  await caption('Synthetic evidence, not customer history or measured hours saved.'); await hold(6);
  await c.evaluate('byId("proof-panel").scrollIntoView({block:"start"})');
  await caption('A reusable mapping with tests, not another conversation every Friday.'); await hold(6);
  ended = Date.now(); capturing = false; await captureTask;
  assert(frames.length > 30, 'Not enough frames for the walkthrough.');
  const lines = [];
  for (let i = 0; i < frames.length; i++) {
    const next = frames[i + 1]?.time ?? ended;
    lines.push(`file '${frames[i].name}'`, `duration ${Math.max(0.01, (next - frames[i].time) / 1000).toFixed(3)}`);
  }
  lines.push(`file '${frames.at(-1).name}'`);
  await writeFile(resolve(directory, 'frames.txt'), lines.join('\n') + '\n');
  const encoded = spawnSync('ffmpeg', ['-n', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', resolve(directory, 'frames.txt'),
    '-vf', 'fps=15,format=yuv420p', '-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-movflags', '+faststart', destination], { encoding: 'utf8', timeout: 120000 });
  assert(encoded.status === 0, 'FFmpeg failed: ' + encoded.stderr);
  await writeFile('evidence/close-entry-demo.json', JSON.stringify({
    synthetic: true, capture: 'Actual running local browser tab, sampled frames encoded at 15 fps with real elapsed timing. No speed-up; sampling rate depends on capture latency.',
    source_profile: 'doze/close_recorded.json', model_calls: 0, recording_seconds: (ended - started) / 1000,
    captured_frames: frames.length, viewport: { width: 1440, height: 1080 }, captions,
    checks: ['recorded origin label', 'eight witnesses', 'messy week blocked with three exceptions', 'source record visible', 'next week four exact settlements with inference disabled', 'reviewed clean packet available', 'synthetic year 41 clean and 11 held with zero model calls'],
    output: 'evidence/doze-friday-close.mp4', audio: false, public_upload: false
  }, null, 2) + '\n');
  console.log(JSON.stringify({ output: destination, seconds: (ended - started) / 1000, frames: frames.length, model_calls: 0 }));
} finally {
  capturing = false;
  if (captureTask) await captureTask;
  await c.evaluate('document.getElementById("demo-caption")?.remove();document.body.style.paddingBottom=""').catch(() => {});
  await c.send('Emulation.clearDeviceMetricsOverride').catch(() => {});
  await Promise.all([c.close(), recorder.close()]);
}
process.exit(0);
