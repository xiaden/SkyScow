# Stage 3: Reader Testing

## Contents
- [Overview](#overview)
- [Approach A: Sub-Agent Testing](#approach-a-sub-agent-testing)
- [Approach B: Manual Testing (No Sub-Agents)](#approach-b-manual-testing-no-sub-agents)
- [Exit Condition](#exit-condition)
- [Final Review](#final-review)

---

**Goal:** Test the document with a fresh Claude instance (no context bleed) to verify it works for readers. This catches blind spots — things that make sense to the authors but confuse others.

## Overview

Explain to the user that testing will now verify whether the document actually works for readers. This catches assumptions and gaps that are invisible to the people who wrote it.

Use the approach that matches your capabilities:

## Approach A: Sub-Agent Testing

Follow these steps when you have access to sub-agents.

### Step 1: Predict Reader Questions

Announce you'll predict what questions readers might ask when trying to discover this document.

Generate 5-10 questions that readers would realistically ask.

### Step 2: Test with Sub-Agent

Announce that these questions will be tested with a fresh Claude instance (no context from this conversation).

For each question, invoke a sub-agent with just the document content and the question.

Summarize what Reader Claude got right/wrong for each question.

### Step 3: Run Additional Checks

Announce additional checks will be performed.

Invoke a sub-agent to check for ambiguity, false assumptions, and contradictions.

Summarize any issues found.

### Step 4: Report and Fix

If issues found: Report that Reader Claude struggled with specific issues. List the specific issues. Indicate you'll fix these gaps.

Loop back to refinement for problematic sections.

---

## Approach B: Manual Testing (No Sub-Agents)

The user will need to do the testing manually.

### Step 1: Predict Reader Questions

Ask what questions people might ask when trying to discover this document. What would they type into Claude?

Generate 5-10 questions that readers would realistically ask.

### Step 2: Setup Testing

Provide testing instructions:

1. Open a fresh Claude conversation
2. Paste or share the document content (if using a shared doc platform with connectors enabled, provide the link)
3. Ask Reader Claude the generated questions

For each question, instruct Reader Claude to provide:
- The answer
- Whether anything was ambiguous or unclear
- What knowledge/context the doc assumes is already known

Check if Reader Claude gives correct answers or misinterprets anything.

### Step 3: Additional Checks

Also ask Reader Claude:
- "What in this doc might be ambiguous or unclear to readers?"
- "What knowledge or context does this doc assume readers already have?"
- "Are there any internal contradictions or inconsistencies?"

### Step 4: Iterate Based on Results

Ask what Reader Claude got wrong or struggled with. Indicate you'll fix those gaps.

Loop back to refinement for any problematic sections.

---

## Exit Condition

When Reader Claude consistently answers questions correctly and doesn't surface new gaps or ambiguities, the doc is ready.

## Final Review

When Reader Testing passes, announce the doc has passed. Before wrapping up:

1. Recommend they do a final read-through themselves — they own this document and are responsible for its quality
2. Suggest double-checking any facts, links, or technical details
3. Ask them to verify it achieves the impact they wanted

Ask if they want one more review, or if the work is done.

**If user wants a final review, provide it. Otherwise:** Announce the document is complete. Provide final tips:

- Consider linking this conversation in an appendix so readers can see how the doc was developed
- Use appendices to provide depth without bloating the main doc
- Update the doc as feedback is received from real readers
