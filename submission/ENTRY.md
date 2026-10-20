---
title: "Doze: teach it once. Let the AI sleep."
published: false
tags: devchallenge, hf26challenge, ai, opensource
---

<!-- OWNER REVIEW: replace the two publication placeholders before submitting.
     Nothing in this file authorizes publication or asset uploads. -->

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 3: Slow and Steady](https://dev.to/challenges/hacktoberfest-week3-2026-10-19).*

## What I Built

Doze refuses to close a week that is one cent short. It can do that with inference disabled.

The chore is reconciling payment exports against bank exports. A payment processor calls a column “Payout group.” The bank calls the same reference “Settlement reference.” Customers paid a gross amount, the processor deducted fees, and a net amount reached the bank. Someone has to connect those meanings, check the sums and investigate what does not match.

Doze uses local Gemma to learn the column mapping, then saves it as a small, reviewable JSON artifact. Humans approve what the columns mean. Python does the arithmetic and checks exact settlement references. The model does not read the transaction rows or decide that a discrepancy is probably fine.

The next export does not need another conversation. Reuse the mapping, review the result and leave inference asleep.

That is my interpretation of **Slow and Steady**: do the uncertain translation once, preserve the result, and stop asking a model to repeat a settled job.

## Demo

**[PUBLIC_DEMO_OR_VIDEO_URL]**

The walkthrough uses synthetic exports and a clearly labelled **recorded Gemma result**, not a fresh teaching call. The saved result comes from an actual local inference run; replaying it requires no model.

Watch for three things:

1. **A plausible mapping has to survive tests.** Eight fixed examples include refunds, duplicates, missing transfers, mixed currencies and a one-cent discrepancy. Swap gross and fees and the mapping falls from 8/8 to 1/8.
2. **The bad week stays bad.** The source-record inspector exposes the discrepancy. Unresolved exceptions block a clean handoff.
3. **The model stops being a dependency.** With inference disabled, the same mapping checks 52 generated weeks: 41 clean, 11 held for review, 19 explicit exceptions. Zero model calls during replay.

These are synthetic outcomes, not a year of customer history or a claim of hours saved.

## Code

**[PUBLIC_REPOSITORY_URL]**

MIT-licensed application code. Python standard library backend, plain JavaScript UI and local Ollama inference. Gemma weights are not distributed with the project and retain their own license terms.

The repository includes the model outputs, failed attempts, synthetic fixtures and verification scripts. The latest local test suite ran 120 tests: 119 passed and one Windows symlink-permission test was skipped. Remote CI has not run yet.

## How I Built It

### Teach the vocabulary, not the calculation

Gemma's job is deliberately small. It sees the two header lists, the chosen decimal separator and an explicitly approved explanation of ambiguous columns. It returns either a mapping or a refusal. Each mapped role must use an actual header from the appropriate export.

For example, the human explanation establishes that “Payout group” and “Settlement reference” contain the same shared payout ID. Gemma translates that explanation into this part of the contract:

```json
{
  "payments": { "batch": "Payout group" },
  "bank": { "batch": "Settlement reference" }
}
```

That is an excerpt, not the whole schema. The complete mapping also identifies unique record IDs, gross, fees, bank amount and currency. It contains no generated code, formulas or fuzzy matching instructions.

Could someone fill in those dropdowns manually? Yes. Doze supports that too. The AI contribution is translating an explanation into a reusable proposal, not making simple arithmetic look intelligent. Its output is useful precisely because it can be inspected, corrected and used without the model.

### The model refused twice. The prompt was part of the problem.

The first attempts did not produce a usable mapping. Even after the shared reference was explained, Gemma returned a refusal. Those records are kept in the repository.

The successful schema was passed to Ollama's output-format constraint, but its full structure was absent from the model-visible prompt. The only complete JSON example in the prompt was the refusal.

Following [Ollama's structured-output guidance](https://docs.ollama.com/capabilities/structured-outputs), I added the successful schema to the prompt and constrained each role to the actual header names. I kept the refusal branch and runtime checks.

The bounded check used three different inputs, with no retries: the explained studio schema mapped correctly, a different header vocabulary mapped correctly, and explicitly unknown column meanings still refused. The studio call took 4.85 seconds on this machine and its output passed all eight fixture tests.

That supports the combined fix on these cases. It does not establish broad model accuracy or prove which individual change caused the improvement.

### Save the tests with the work

A valid JSON shape is not proof of correct meaning. Swapping gross and fees can produce perfectly well-formed nonsense.

Doze's studio workflow therefore carries a mapping **and executable witnesses**: synthetic CSVs with fixed expected outcomes. Those expectations are authored separately from the proposed mapping. The model cannot mark itself correct.

Imports do not trust an exported “passed” badge. Doze reruns its installed witness suite. A changed mapping, forged result or rewritten bundled expectation cannot make a failing workflow bundle pass. These fixtures apply to the known studio schema, not arbitrary providers; a plain, human-reviewed mapping remains a separate path without that fixture gate.

### Make the boring part exact

The reconciliation engine uses decimal arithmetic and exact shared settlement references. Duplicate IDs, ambiguous transfers, unsupported or conflicting currencies, malformed rows and changed schemas become explicit problems, not guesses. A one-cent difference is a mismatch.

A clean result is still not permission to export a packet. The user reviews the report, and approval binds its hash to the exact inputs and mapping. Change an input and the old approval no longer applies. A workflow report also binds the witness-suite identity.

The handoff ZIP contains reconciliation CSV, audit JSON, mapping, source hashes and a read-me, plus the tested workflow when used. Selected source CSV contents are not bundled. The source exports are never edited.

### Take the browser out too

The artifact can run through a standard-library CLI:

```sh
python -m doze.close_cli --profile workflow.json --payments payments.csv --bank bank.csv --mapping-approved
```

The browser, web server and Ollama are unnecessary for that step. Packet creation requires the exact report hash from a previous review and a new output filename.

I checked this in fresh Python processes with socket creation blocked. Twelve checks passed, including clean and bad-week verdicts, approved ZIP creation, rejection of stale approval and preservation of existing output files. This is stronger evidence for offline reuse than a sleeping icon alone.

## Why Does Open Innovation Matter?

The open-weight model makes the teaching step local. Header meanings and the user's explanation go to a loopback Ollama service, not a hosted inference endpoint. Doze has no automatic cloud fallback and does not download a model behind the user's back.

The open application code makes the boundary inspectable: what enters inference, what JSON it can return, how money is calculated and what blocks a handoff. Another installed local model can propose the same contract without replacing the execution engine.

Most importantly, the result is not trapped in a chat session. Once a mapping is reviewed, the recurring job needs no inference service at all. A closed API could generate JSON too, but it would require a remote call for teaching. Local open weights let this project avoid that dependency from the start.

There are limits. Matching exports prove agreement between those exports, not completeness: a transaction missing from both is invisible. Doze does not connect to bank accounts, move money, convert currencies, resolve split transfers or give tax advice. There has been no real customer trial, and I have not measured human time saved or energy use.

The practical reduction is specific: stop re-explaining an unchanged export format and stop asking a model to do the same sums. Keep the human review where it matters, on the mapping and the exceptions.

*Built with AI assistance through OpenCode, including implementation, verification tooling and drafting this write-up. Ollama provides the local inference runtime; Gemma provides the open-weight model. The separately installed Chrome automation driver was used for development verification, not shipped as application code.*

## Prize Categories

**Best Use of Gemma:** local `gemma4:12b-it-qat` turns approved column explanations into constrained mappings. Actual model outputs, two earlier refusals and the bounded three-case check are preserved. Its successful mapping is then reused without further inference.
