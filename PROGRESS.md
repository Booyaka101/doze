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
