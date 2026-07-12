# Stage 2: Refinement & Structure

## Contents
- [Overview](#overview)
- [Section Ordering](#section-ordering)
- [Creating the Scaffold](#creating-the-scaffold)
- [Per-Section Workflow](#per-section-workflow)
- [Quality Checking](#quality-checking)
- [Near Completion](#near-completion)

---

**Goal:** Build the document section by section through brainstorming, curation, and iterative refinement.

## Overview

Explain to the user that the document will be built section by section. For each section:

1. Clarifying questions will be asked about what to include
2. 5-20 options will be brainstormed
3. User will indicate what to keep/remove/combine
4. The section will be drafted
5. It will be refined through surgical edits

Start with whichever section has the most unknowns (usually the core decision/proposal), then work through the rest.

## Section Ordering

If the document structure is clear, ask which section they'd like to start with.

Suggest starting with whichever section has the most unknowns. For decision docs, that's usually the core proposal. For specs, it's typically the technical approach. Summary sections are best left for last.

If user doesn't know what sections they need, suggest 3-5 sections appropriate for the doc type based on the document's purpose and template. Ask if the structure works or if they want to adjust it.

## Creating the Scaffold

Once structure is agreed, create the initial document with placeholder text for all sections.

**If artifacts are available:** Use `create_file` to create an artifact with all section headers and brief placeholder text like "[To be written]". Provide the scaffold link and indicate it's time to fill in each section.

**If no artifacts:** Create a markdown file in the working directory (e.g., `decision-doc.md`, `technical-spec.md`) with all section headers and placeholder text. Confirm the filename and indicate it's time to fill in each section.

## Per-Section Workflow

### Step 1: Clarifying Questions

Announce work will begin on the [SECTION NAME] section. Ask 5-10 clarifying questions about what should be included, generating them based on context and section purpose.

Tell them they can answer in shorthand or just indicate what's important to cover.

### Step 2: Brainstorming

For the [SECTION NAME] section, brainstorm 5-20 things that might be included, depending on the section's complexity. Look for:

- Context shared that might have been forgotten
- Angles or considerations not yet mentioned

Generate 5-20 numbered options. At the end, offer to brainstorm more if they want additional options.

### Step 3: Curation

Ask which points should be kept, removed, or combined. Request brief justifications to help you learn their priorities for the next sections.

Provide examples:
- "Keep 1,4,7,9"
- "Remove 3 (duplicates 1)"
- "Remove 6 (audience already knows this)"
- "Combine 11 and 12"

**If user gives freeform feedback** (e.g., "looks good" or "I like most of it but...") instead of numbered selections, extract their preferences and proceed. Parse what they want kept/removed/changed and apply it.

### Step 4: Gap Check

Based on what they've selected, ask if there's anything important missing for the [SECTION NAME] section.

### Step 5: Drafting

Use `str_replace` to replace the placeholder text for this section with the actual drafted content.

Announce the [SECTION NAME] section will be drafted now based on what they've selected.

**If using artifacts:** After drafting, provide a link to the artifact. Ask them to read through it and indicate what to change, noting that being specific helps you learn for the next sections.

**If using a file (no artifacts):** After drafting, confirm completion. Tell them the section has been drafted in the file and ask them to indicate what to change.

**Key instruction (include when drafting the first section):** Instead of editing the doc directly, ask them to tell you what to change. This helps you learn their style for future sections. For example: "Remove the X bullet — already covered by Y" or "Make the third paragraph more concise."

### Step 6: Iterative Refinement

As user provides feedback:

- Use `str_replace` to make edits (never reprint the whole doc)
- **If using artifacts:** Provide artifact link after each edit
- **If using files:** Just confirm edits are complete
- If user edits the doc directly and asks you to read it: mentally note the changes they made and keep them in mind for future sections (this shows their preferences)

Continue iterating until the user is satisfied with the section.

## Quality Checking

After 3 consecutive iterations with no substantial changes, ask if anything can be removed without losing important information.

When section is done, confirm [SECTION NAME] is complete. Ask if they're ready to move to the next section.

**Repeat for all sections.**

## Near Completion

As you approach completion (80%+ of sections done), announce you'll re-read the entire document and check for:

- Flow and consistency across sections
- Redundancy or contradictions
- Anything that feels like "slop" or generic filler
- Whether every sentence carries weight

Read the entire document and provide feedback.

**When all sections are drafted and refined:** Announce all sections are drafted. Review for overall coherence, flow, and completeness. Provide any final suggestions. Ask if they're ready to move to Reader Testing or want to refine anything else.
