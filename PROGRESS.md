# Doze build ledger

Started 2026-10-20 for DEV HF26 Week 3, October 19-25.

## Latest completed pass: local publication preflight, October 21

Bounded continuation of entry preparation. No public actions or model calls.
Inspected branch/clean state, six-commit history, tracked inventory, CI, quick-start
instructions and publication gates. No configured remote. Added read-only
tools/audit_publication.py with finite history/text budgets and redacted findings.
Initial index/history scan covered 115 unique text blobs, 896,240 bytes: no selected
credential-pattern matches, home-directory path matches or tracked runtime state.
This is not a comprehensive secret scan or clearance of historical media. One
author/committer identity remains owner-review material; history was not rewritten.

README now explains clean-checkout launch on default port 8741 and distinguishes
the local development demo on port 8743. Extended existing CI matrix with close.js
syntax, recorded-Gemma offline proof and article checks. No application changes.

Verification complete: 120 tests, 119 passed and one symlink-permission skip;
close.js syntax and fourteen article checks passed. An isolated tracked-file copy
also passed original offline proof, recorded-Gemma close proof and article checks.
Generated evidence stayed in the disposable copy, preserving original evidence.
No remote CI or Linux checks claimed. Further repeated backend checks unnecessary.

Next: owner review of article/video, identity and historical media; approve public
repository/media destinations. Then exact-commit remote CI and DEV preview before
explicit publication approval. No pushes, repository creation, uploads, release,
deployment or submission performed. See submission/REVIEW.md for the gate list.

## Latest completed pass: competition review package, October 21

User asked to proceed toward the competition. Scope was editorial/media, not new
app features or publication. Rules checked in the saved official challenge page;
read two current DEV entries for venue context. User testing is optional, not an
eligibility gate. Supersedes earlier wording that put a user trial ahead of entry
preparation. Writing quality is the most heavily weighted criterion.

- Drafted submission/ENTRY.md using official headings, required tags and
  published:false. Approximately 1,405 words including metadata and review note.
  Lead: model produces a reusable mapping; deterministic work outlives inference.
  Includes actual failures, successful fix, fixed witnesses, one-cent hold,
  network-blocked CLI proof, open innovation, limitations and AI-use disclosure.
- Created original cover.svg and rendered cover.png (1000x420). No external art.
- Recorded actual app interactions: evidence/doze-friday-close.mp4, 68.53 seconds,
  H.264, 2160x1620 encoded pixels, 1,936,680 bytes, no audio. Synthetic exports and
  recorded Gemma mapping disclosed throughout. 62 sampled frames with actual
  elapsed timing; encoded at 15 fps, not claimed as 15-fps source recording.
- Seven assertions passed during capture: origin, witnesses, blocked messy close,
  source records, exact next-week reuse asleep, reviewed clean packet available,
  and year outcomes. No downloads to user folders or model calls during capture.
- First capture completed the app flow but stopped before encoding at an overly
  strict frame-count threshold. One bounded corrected capture delivered the MP4.
  Frames isolated in ignored .doze/close-capture-* folders. No further takes needed.
- Inspected original cover and six MP4 frames via submission/demo-contact-sheet.jpg.
  FFprobe verified codec, duration, dimensions and bytes. No unrelated desktop
  windows captured. Demo captions are an explicitly editorial overlay, not fake UI.
- Added DEMO.md and REVIEW.md with asset manifest, claim sources and approval gates.
- tools/check_entry.py: 14 local evidence comparisons passed; publication_ready
  deliberately false. tools/record_close_demo.mjs reproduces the local capture.
  No app code changed, so the settled 120-test backend pass was not rerun.

Remaining: owner reviews article/video, approves public repository and media
destination; read-only publication review, exact-commit CI, replace two PUBLIC_*
URL placeholders, DEV preview and explicit final post approval. No repository
created, push, release, deployment, upload or public submission. Do not claim this
review package has been submitted or guarantees a win. No more verification loops
needed on this completed pass. Keep model inference asleep on the existing demo.

## Latest completed pass: grounded Gemma teaching, October 21

Supersedes the earlier unresolved-teaching notes below. User authorized continuing.
Bounded scope: at most three distinct synthetic local calls and two verification
passes. Completed; no more model calls or verification loops needed this pass.

- Found successful mapping schema absent from model-visible prompt although passed
  as Ollama format grammar. Added schema grounding and per-role actual-header enums,
  decimal-mark constraint and bounded name. Shared compiler and refusal branch
  unchanged. Official reference: docs.ollama.com/capabilities/structured-outputs.
- Three live Gemma cases, no retries: explained studio mapping succeeded (4.85s,
  exact roles, 8/8 witnesses); different vocabulary succeeded; explicitly unknown
  meanings refused. This supports the combined fix, not a proven individual cause
  or universal reliability claim. Raw results: close-grounded-teaching.json.
- Bundled exact recorded output and provenance in doze/close_recorded.json, tested
  against actual live evidence. UI replay explicitly labels RECORDED GEMMA RESULT,
  distinguishes historical call from current zero-call replay and works asleep.
- Actual recorded model output passed browser witness suite, 52 synthetic weeks
  (41 clean, 11 held, 19 exceptions), wrong mapping 1/8, forged proof rejection,
  actual workflow import revalidation, reviewed 4,344-byte ZIP, manual alternate
  schema and 390px no-overflow check. No new inference during these checks.
- Twelve fresh CLI subprocess checks passed with socket creation blocked using
  that model's workflow. Input changes reject old review hash; outputs preserved.
- Evidence names end in -gemma to preserve prior manual baselines: workflow smoke,
  tested workflow, synthetic year, offline proof and screenshots 16-19.
- Final suite: 120 tests run, 119 passed, one Windows symlink-permission skip.
  JavaScript syntax passed. Earlier refusal records are retained honestly.
- Runtime: restarted only our identified 8743 process, current PID 37992 in
  .doze/close-server.pid. Original 8741/8742 processes preserved. Inference asleep;
  demo shows recorded Gemma workflow and synthetic year at http://127.0.0.1:8743.
- Remaining: explicitly approved real user trial and measured human effort;
  competition writing, public code/demo and submission need owner approval.
  Nothing published, pushed, purchased or connected to real financial records.

## Decision
Compile natural-language file chores into constrained, reusable local recipes.
The local model proposes rules, never shell commands. Deterministic preview,
explicit approval, hash-bound execution, journalled undo. No scheduler.

## Research completed
- Read current official challenge page: new projects within window, open AI at core.
- Generic local AI file organizers already offer sorting, preview and undo.
- Differentiator: compile once, rehearse, export, reuse with zero model calls.
- Ollama available locally. Installed Gemma 4 12B, Qwen and DeepSeek.
- No model running at initial check. No downloads or paid endpoints needed.

## Scope and budget
One implementation pass, then two bounded verification/fix passes. Target 45 minutes.
MVP: Python standard library server, original browser UI, safe recipe engine,
local Ollama compiler, synthetic demo, automated tests, README and demo assets.
No publishing, real inbox access, schedules, external writes or paid services.

## Completed
- Original Python standard-library server and UI, constrained recipe engine.
- Local Gemma compilation tested live. First compile was too broad; added
  near-miss lab and stronger compiler instructions. Corrected output verified.
- 44 tests: 43 passed, 1 Windows symlink-permission skip. No failed tests.
- Browser end-to-end: compile, 9/9 probes, close inference gate (400 rejection
  verified), rehearse and run five files, fresh five-file batch, checked undo.
- Desktop and 390px mobile screenshots saved. No horizontal mobile overflow.
- Browser resource hosts: only 127.0.0.1:8741. No unrelated services stopped.
- README includes honest limitations, architecture, measured evidence and entry checklist.
- CI prepared, not run remotely. No remote repository, deployment or submission.

## Final bounded checks
- Network-forbidden proof passed on saved live Gemma output: two five-file batches,
  114.02ms / 110.35ms preview + run observations. Both checked undos restored hashes.
- Captioned 35-second MP4 assembled from verified screenshots, explicitly labelled
  edited captures rather than a live recording. Not uploaded.
- Browser smoke script syntax checked after making the driver URL configurable.
- Staged diff whitespace check and Python compilation passed. MP4 verified as
  H.264, 1280x1080, approximately 35 seconds. Local checkpoint commit follows.
- No unresolved implementation blocker. Remaining entry work is editorial review,
  approved publication and a public demo/video URL. No further research pass needed.

## Local runtime
- Server PID is recorded in .doze/server.pid. Stop only after verifying its command line.
- UI: http://127.0.0.1:8741. Sample files only. Inference gate left asleep after smoke test.
- Evidence: evidence/browser-smoke.json and screenshots 01-06.
- Existing Chrome tab is the local Doze app. Shared Ollama was not stopped.

## Publication boundary
Owner approval needed for exact outward-facing article, public repository and
video upload/deployment. Challenge deadline October 25 at 11:59 PM PDT.
No guarantee of winning; this is a verified prototype, not a complete entry.

## Next-level pass, October 20

User requested a stronger contender after an honest critique of the first prototype.
Scope: one implementation pass and two verification passes. Branch:
`feat/teaching-contracts`. No other agents, real user files or publication involved.

### Implemented
- Labelled examples are part of compilation, not optional after-the-fact decoration.
- Durable immutable teaching contracts. Every destination needs a positive example,
  at least one HOLD is required and all examples must pass before engine execution.
- Direct API approval cannot bypass a failed contract. Bare old recipes need examples
  before running; existing receipt undo remains available.
- Explicit one-call model repair with previous rules and deterministic feedback.
- Portable recipe-and-example bundles. Import recomputes results instead of trusting
  an exported certificate. SHA-256 recipe and example identities travel in receipts.
- Unsaved examples or JSON changes invalidate approval and block rehearsal.
- Fixed 30-day synthetic replay uses actual journalling and byte checks in an isolated
  temporary workspace. Last batch undo is verified. No visible workspace changes.
- Recorded first-model mistake is reconstructed and visibly labelled for replay.
- Updated teaching interface, explanatory story, README and captioned demo.

### Verification complete
- 63 tests: 62 passed, 1 Windows symlink-permission skip. No failed tests.
- Live browser: recorded mistake 8/9, direct execution 400, one actual Gemma repair
  9/9, inference gate closed, 30 synthetic days / 360 files / 150 moves / 210 held.
- Replay all file hashes checked; last undo verified. Runtime observed 7.231s.
- Certified visible sample run and undo passed, mobile 390px had no overflow.
- Final browser regression on restarted current server: zero model calls; unsaved
  edit invalidates approval; unsaved rehearsal blocked; contract save creates new
  version; valid compile request rejected while asleep; approved run and undo pass.
- Network-forbidden proof passed on live repaired recipe: two five-file batches
  plus checked undo. Observed preview + run 117.69ms / 119.06ms, not human savings.
- Evidence: teaching-smoke.json, teaching-live-repair.json, thirty-mornings.json,
  teaching-regression.json, screenshots 07-11, doze-teaching-walkthrough.mp4.
- MP4 is explicitly labelled edited still captures, not live screen recording.

### Runtime and handover
- Revised app: http://127.0.0.1:8742, state `.doze/next`, PID file
  `.doze/next-server.pid`. Original 8741 process left untouched.
- Revised inference gate left asleep. Wake through UI only if another model call
  is wanted. Shared Ollama not stopped. All source changes are on the feature branch.
- Remaining honest gap: real user trial and measured human effort, not more synthetic
  claims. Still filename/extension/size rules, not semantic document understanding.
- No public repository, deployed site, uploaded video, community post or entry.
- Bounded pass finished. Do not rerun live model work merely to polish evidence.

## Friday Close pass, October 20

Branch: `feat/friday-close`. One implementation and two verification passes.
The stronger use case is recurring payment-export / bank-export reconciliation.
No real records, account access, purchases, posting or publication.

### Implemented and checked
- New primary workspace at `/`, original certified file studio at `/files`.
- CSV inspection, header-only teaching consent, editable/importable mappings,
  schema-bound profiles, exact decimal arithmetic and explicit exceptions.
- Duplicate IDs quarantine all occurrences and block affected batches. Missing,
  ambiguous, orphan, mixed-currency and one-cent mismatches cannot produce a
  clean packet. Header drift stops the whole calculation.
- Source-record drilldown, per-currency totals, incomplete-total warnings and
  human-reviewed ZIP evidence bound to input/profile/report hashes. Sources are
  not edited or included in the ZIP. Spreadsheet formula payloads are escaped.
- Shared local inference boundary extracted; file-compiler request and output
  regression test included. Existing certified execution/undo tests retained.
- Final suite: 95 tests, 94 passed, one Windows symlink-permission skip. No
  failures. JavaScript syntax and diff whitespace checks passed.
- Browser verified twice with the explicitly labelled hand-written mapping:
  messy week has three exceptions; one-cent case blocked; next week four exact
  matches; approved ZIP response 2,211 bytes; server teaching rejected asleep;
  drift stopped; 390px layout has no horizontal overflow. Zero recurring calls.
- 52 synthetic weeks tested with network access forbidden. No real time-saving
  claim or complete-bookkeeping claim. Agreement cannot reveal omissions from
  both source exports. Supported inputs and limitations documented in README.
- Screenshots 12-15 and `evidence/close-smoke.json` record this new workspace.

### Important unresolved evidence gap
- One live `gemma4:12b-it-qat` call safely refused the header mapping because it
  did not infer that Payout group and Settlement reference are the shared ID.
  No retry was made. `evidence/close-live-teaching.json` records the refusal.
- Therefore Friday Close AI teaching is implemented but NOT live-demonstrated.
  The browser proof uses a hand-written mapping, not a successful model output.
  Original file-studio teaching/repair evidence remains valid and separate.
- A new regression test initially expected the wrong request key (`chore`);
  corrected to the pre-existing `instructions` key. This was a test expectation
  error, not a compiler behavior change.

### Runtime and next boundary
- http://127.0.0.1:8743, PID 19248 recorded in `.doze/close-server.pid`, state
  `.doze/close`. Inference gate left asleep. Original 8741/8742 preserved.
- No more model calls or research in this bounded pass. Before calling this
  contest-ready, demonstrate reliable AI teaching and conduct a real user trial.
- No public code, submission, deployment or upload. Owner approval still needed.

## Test-bearing workflows and offline runner, October 20

User asked for another substantial improvement. Same `feat/friday-close` branch;
clean starting tree at `43d5b2e`. Budget: one implementation, one bounded live
Gemma call, two verification passes. No delegates, real records or publication.

### Implemented
- Explicit, consent-bound column explanation input. Refusals remain visible.
  No automatic retry. Explanations are user-supplied data, not CSV row extraction.
- Manual arbitrary-header mapping starts with blank roles. Duplicate roles and
  incomplete mapping block reconciliation. Edited CSVs lose the synthetic badge.
- Eight independent, fixed studio witness cases. Gross/fee swap fails 7/8 cases.
- Portable workflows contain profile, actual synthetic CSV witnesses, expected
  results, versioned suite and hashes. Imported pass badges are not trusted.
  Changed profiles and rewritten expectations cannot bypass bundle checks.
- Reconciliation report binds workflow suite identity; packet includes workflow.
  Plain mappings remain a separate human-reviewed, non-fixture-certified path.
- 52-week synthetic replay: 1,248 payments, 193 exact settlements, 41 clean weeks,
  11 held weeks and 19 exceptions. Server requires inference asleep. No scheduler,
  account access, input changes or measured-human-savings claims.
- Standalone `python -m doze.close_cli`: no browser/server/Ollama dependency.
  Explicit mapping approval, exit 2 for exceptions, exact reviewed report hash for
  packet, bounded inputs, exclusive file creation so existing work is preserved.

### Completed verification, do not reopen settled checks
- Final suite: 115 tests run, 114 passed, one Windows symlink-permission skip.
- Browser workflow check: 8/8 correct; 1/8 swapped mapping; forged proof rejected
  through API; actual JSON import recomputed proof; changed mapping invalidated
  tests/report/approval; approved workflow ZIP; sleep gate rejected inference.
- Synthetic year and per-week evidence saved, not a real-user benchmark.
- Cold CLI subprocess proof blocks socket creation. Twelve checks passed:
  clean/penny/messy verdicts and exit codes, approved ZIP, bundled witnesses,
  exact audit hash, existing output preservation, changed-input approval rejection
  and source/profile byte preservation. `evidence/close-offline-proof.json`.
- Targeted manual browser check: new header vocabulary, four exact settlements,
  blank and duplicate roles blocked, edited-origin label correct, 390px no overflow.
- Browser harness needed two corrections in the custom-schema extension: preserve
  escaped newlines in an evaluated template, and open the CSV details before
  clicking its otherwise hidden Inspect button. Targeted check then passed.
- Evidence: close-workflow-smoke.json, close-manual-smoke.json,
  close-synthetic-year.json, close-tested-workflow.json, screenshots 16-19.

### Remaining blocker, explicit rejection of a stronger claim
- The one new Gemma call also refused, returning the literal error `explanation`
  despite explicit shared-ID semantics. Exact approved input/error saved in
  `evidence/close-explained-teaching.json`. No model retry was made.
- Reliable Friday Close AI teaching is still NOT demonstrated. All new workflow,
  year and offline proofs use a hand-written mapping, labelled accordingly.
- The next effort should diagnose this structured-output/refusal route, not add
  more synthetic success claims. A real user trial is still missing. This bounded
  pass is finished; no extra probes or model loops are authorized by this ledger.

### Runtime
- Restarted only our precisely identified 8743 process. Current PID 16780 in
  `.doze/close-server.pid`; original 8741/8742 processes preserved.
- http://127.0.0.1:8743, inference asleep, verified sample workflow and saved year
  shown. Historical replay is visibly synthetic. No public actions taken.
