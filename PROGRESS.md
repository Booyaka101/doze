# Doze build ledger

Started 2026-10-20 for DEV HF26 Week 3, October 19-25.

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
