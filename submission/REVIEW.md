# Doze entry review and publication gate

Status: owner explicitly approved publication on October 22: public repository
Booyaka101/doze with existing history/identity and synthetic demo, then the exact
reviewed article on the signed-in DEV account after remote CI and link checks.
Publication is being prepared; approval alone does not establish submission.
Winning is not guaranteed.

## Assets ready for owner review

- ENTRY.md: template-structured article with required tags and honest AI disclosure.
- cover.svg and cover.png: original cover art. No external art or generated person.
- ../evidence/doze-friday-close.mp4: 68.53-second captioned actual-app walkthrough.
- ../evidence/close-entry-demo.json: capture disclosure, timestamps and assertions.
- demo-contact-sheet.jpg: six actual frames extracted for quick visual review.
- DEMO.md: storyboard, production notes and limitations.

The final candidate uses the approved GitHub repository and its hosted MP4 as
public destinations. Localhost is only a local try-it instruction. Verify those
public links after code publication and before posting the article.

## Editorial decision

Lead with Friday Close, not two separate applications. The original file studio
remains in the repository as background. The differentiator is the test-bearing
artifact that outlives inference, not a general claim that local AI is private.

Read the official Week 3 prompt, template, judging criteria and participation
requirements. Writing quality is weighted most heavily. Real user testing is not
required; the template's Lazy Payoff section is optional. Omitted that section
rather than imply practical usage or measured savings.

Read two current entries for venue context, not as source text or product code:
- https://dev.to/dhanushnehru/standup-sloth-a-local-llm-drafts-your-standup-and-a-citation-check-keeps-it-honest-5h7h
- https://dev.to/rahulrao85/hisaab-gemma-4-reads-my-bank-sms-on-my-phone-and-the-app-has-no-internet-permission-4cp1

These do not establish a ranking or a prediction about the judges.

## Claim audit

| Draft claim | Evidence or implementation |
| --- | --- |
| Two live synthetic mappings succeeded; unknown labels refused | evidence/close-grounded-teaching.json |
| Two earlier refusals retained | evidence/close-live-teaching.json, evidence/close-explained-teaching.json |
| Studio call 4.85 seconds | First case provenance in close-grounded-teaching.json; this machine only |
| Eight fixed studio witnesses; swapped mapping 1/8 | doze/close_workflow.py, evidence/close-workflow-smoke-gemma.json |
| Actual Gemma artifact reused, not manual baseline | doze/close_recorded.json; test_recorded_lesson_matches_actual_live_evidence |
| 52 synthetic weeks, 41 clean, 11 held, 19 exceptions | evidence/close-synthetic-year-gemma.json |
| No inference during that replay | Reconciliation implementation and network-blocked tests; not just a UI label |
| Twelve cold CLI checks, sockets blocked | tools/prove_close.py, evidence/close-offline-proof-gemma.json |
| 120 run, 119 passed, one skipped | Latest completed verification in PROGRESS.md |
| Source hashes and exact approval | doze/close.py, server/API and CLI regression tests |
| MIT application, no distributed weights | LICENSE and tracked application files |
| Real user testing not required | Official template marks The Lazy Payoff optional |

Avoid: production-ready, universally accurate mappings, accountant-approved,
energy savings, hours saved, a real year of transactions, no internet permission,
cryptographic certification, stopping the shared Ollama process, successful remote
CI or a fresh model call in the recorded-result demo.

The existing file-studio MP4s are edited still captures and are not Friday Close
footage. Do not use them to imply a live Friday Close teaching demonstration.

## Before any public action

### Local publication preflight, October 21

- Six reachable commits and 115 unique text blobs checked before this pass's
  changes: no matches for the selected credential patterns, no home-directory
  paths and no tracked runtime-state paths. `tools/audit_publication.py` makes the
  bounded scan repeatable without printing matched secrets or identity values.
  Pattern checks are not a comprehensive security or privacy clearance.
- One distinct author/committer identity is visible in history. Owner must review
  that identity locally before publishing history; it has not been rewritten.
- Historical images/video still need full visual and metadata review before
  public-code approval. The scanner lists binary assets but does not inspect them.
- README now leads with a clean-checkout command and the default port 8741,
  distinguishing this machine's existing port 8743 demo from a public URL.
- CI now includes Friday Close JavaScript syntax, recorded-Gemma offline proof
  and article evidence checks alongside the existing matrix. No guards removed.
- Local suite: 120 tests, 119 passed, one Windows symlink-permission skip.
  Friday Close JavaScript syntax passed. Both offline proofs and all fourteen
  article checks passed in an isolated tracked-file copy without replacing the
  original evidence. This was not a remote CI run or a Linux validation.
- No remote is configured. Public destinations, uploads and the final post remain
  unapproved; this preflight does not authorize any of those actions.

- [x] Owner approves exact article text and AI-use disclosure.
- [x] Owner approves the demo asset and public upload destination.
- [x] Owner approves publishing code and chooses public repository/name.
- [ ] Read-only publication review checks tracked files, history, secrets,
      licensing, evidence contents and reproducible setup. Local state stays out.
- [ ] CI passes on the exact intended publication/release commit. A local test
      pass is not remote CI. Resolve any publication/CI ordering explicitly.
- [x] Replace PUBLIC_REPOSITORY_URL and PUBLIC_DEMO_OR_VIDEO_URL in ENTRY.md.
- [ ] Upload approved cover/screenshots only to the approved destination.
- [ ] Preview article on DEV; verify links, code blocks, media and disclosure.
- [ ] Required tags: devchallenge, hf26challenge. Category: Best Use of Gemma;
      overall consideration is automatic under the official rules.
- [ ] Confirm project/window requirements and deadline: October 25, 2026,
      11:59 PM PDT, from the official rules.
- [x] Obtain explicit approval for the final DEV Publish/Submit action, conditional
      on passing remote CI and public link verification without article changes.

No full agent session export is needed. That optional feature should not expose
private conversation history, local paths, credentials or unrelated work.
