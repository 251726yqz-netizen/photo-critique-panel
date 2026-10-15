# Implementation ledger — photo-critique-panel

Date: 2026-10-14 (Asia/Tokyo)

Spec: the user-approved 22-member panel plan in this conversation.

## Decisions

- Create the standalone skill package in the user-specified workspace. No existing repository or branch is required; do not initialize or publish a GitHub repository automatically.
- Research summaries are original Chinese paraphrases. References distinguish fact, supported idea, and application inference. Source pages are not reproduced wholesale.
- Source publication dates and retrieval dates are separate; an undated faculty page does not establish a dated appointment event.
- Validation uses Python 3 standard library and structured JSON sidecars so CI does not need paid models or live web services.
- Behavioral runs are recorded separately from deterministic validation. Never describe structural tests as evidence of model behavior.

## Tasks

- [x] Baseline behavioral test without the new skill.
- [x] Research and author 22 sourced profiles.
- [x] Implement skill workflows, admissions reference and report examples.
- [x] Implement and test structural validator; package metadata and maintenance docs.
- [x] Run behavioral tests with the skill and fresh review.
- [x] Final validation and local package delivery.

## Evidence at delivery

Research: 62 source records / 50 substantive records, with explicit reading limits; each seat has at least two substantive materials. Ten photographers have separate public reproduction viewing logs. Professor source-depth corrections were independently re-read.

Initial synthetic tests and real-photography paired runs are preserved as raw responses. The baseline already passed several boundary checks; no fabricated failure or improvement claim was used. Additional admissions / unreadable-file checks are separate, not paired causal comparisons. The exact inherited host model preset was unavailable to the evaluators and is recorded as such.

25 deterministic regression tests and the official skill frontmatter check pass. Copying the package into a temporary skills directory succeeds; editing one profile leaves the other 21 hashes unchanged. See [validation ledger](validation.md) and [behavior assessment](../tests/results/assessment.md). Full books, physical prints, real applicant outcome prediction and cross-model reliability are outside the evidence established here.

## Research deepening — 0.2.0, 2026-10-15

All 22 profiles received new substantive material: 31 additions, 93 source records / 81 substantive records total. New F/I/R IDs are mapped in research/deepening-2026-10-15/change-map.json. Independent source and claim review caught one project-attribution error, now corrected. Four exact-input cases covering 22 seats were run against preserved 0.1.0 and updated 0.2.0; raw outputs, manifests and human assessment are saved. 25 regression tests, package validator and official skill check pass. The original 0.1.0 archive is retained; the deepened release is separately packaged.
