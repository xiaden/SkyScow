---
name: doc-coauthoring
description: Guide users through a structured workflow for co-authoring documentation. Use when user wants to write documentation, proposals, technical specs, decision docs, or similar structured content. This workflow helps users efficiently transfer context, refine content through iteration, and verify the doc works for readers. Trigger when user mentions writing docs, creating proposals, drafting specs, or similar documentation tasks.
---

# Doc Co-Authoring Workflow

Guide users through collaborative document creation in three stages: **Context Gathering**, **Refinement & Structure**, and **Reader Testing**. Act as an active guide — be direct, procedural, and focused on document quality.

## When to Use

**Trigger conditions:**

- User mentions writing documentation: "write a doc", "draft a proposal", "create a spec", "write up"
- User mentions specific doc types: "PRD", "design doc", "decision doc", "RFC"
- User seems to be starting a substantial writing task

**Initial offer:** Explain the three stages and their purpose. Ask if they want to try this workflow or prefer to work freeform. If they decline, work freeform.

## Workflow Stages

### Stage 1: Context Gathering

Close the gap between what the user knows and what you know, enabling smart guidance later. Ask meta-context questions, let the user info-dump, then ask clarifying questions to fill gaps.

**Entry condition:** User accepts the workflow.
**Exit condition:** You can reason about edge cases and trade-offs without needing the basics explained.

→ Full instructions: [`references/stage-1-context-gathering.md`](file:///home/opencode/.config/opencode/skills/doc-coauthoring/references/stage-1-context-gathering.md)

### Stage 2: Refinement & Structure

Build the document section by section through brainstorming, curation, drafting, and iterative refinement. Start with the section that has the most unknowns (usually the core decision/approach).

**Entry condition:** Sufficient context gathered. User is ready to draft.
**Exit condition:** All sections drafted, refined, and the complete document reviewed for flow, redundancy, and coherence.

→ Full instructions: [`references/stage-2-refinement.md`](file:///home/opencode/.config/opencode/skills/doc-coauthoring/references/stage-2-refinement.md)

### Stage 3: Reader Testing

Test the document with a fresh Claude instance (no context bleed from the co-authoring session) to catch blind spots — things that make sense to the authors but confuse readers.

**Entry condition:** Document is complete and polished.
**Exit condition:** Reader Claude consistently answers questions correctly without surfacing new gaps or ambiguities.

→ Full instructions: [`references/stage-3-reader-testing.md`](file:///home/opencode/.config/opencode/skills/doc-coauthoring/references/stage-3-reader-testing.md)

## Tips for Effective Guidance

**Tone:** Be direct and procedural. Explain rationale briefly when it affects user behavior. Don't "sell" the approach — just execute it.

**Handling deviations:**
- If user wants to skip a stage: ask if they want to skip and write freeform
- If user seems frustrated: acknowledge the delay and suggest ways to move faster
- Always give the user agency to adjust the process

**Context management:** Proactively ask when context is missing. Don't let gaps accumulate — address them as they surface.

**Artifact management:** Use `create_file` for drafting full sections, `str_replace` for surgical edits. Provide artifact links after every change. Never use artifacts for brainstorming lists — that's just conversation.

**Quality over speed:** Don't rush through stages. Each iteration should make meaningful improvements. The goal is a document that works for readers, not one that was written quickly.

## References

- [`references/stage-1-context-gathering.md`](file:///home/opencode/.config/opencode/skills/doc-coauthoring/references/stage-1-context-gathering.md) — Initial questions, info dumping, integrations, clarifying questions, exit and transition
- [`references/stage-2-refinement.md`](file:///home/opencode/.config/opencode/skills/doc-coauthoring/references/stage-2-refinement.md) — Section ordering, brainstorming, curation, drafting, iterative refinement, quality checking, near-completion review
- [`references/stage-3-reader-testing.md`](file:///home/opencode/.config/opencode/skills/doc-coauthoring/references/stage-3-reader-testing.md) — Reader question prediction, sub-agent testing (or manual testing), additional checks, fix cycles, final review
- Related conventions: See `update-docs/references/cliche-data.md` for placeholder data rules when writing documentation examples.
