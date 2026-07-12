# Stage 1: Context Gathering

## Contents
- [Initial Questions](#initial-questions)
- [Info Dumping](#info-dumping)
- [During Context Gathering](#during-context-gathering)
- [Clarifying Questions](#clarifying-questions)
- [Exit Condition & Transition](#exit-condition--transition)

---

**Goal:** Close the gap between what the user knows and what you know, enabling smart guidance later.

## Initial Questions

Start by asking the user for meta-context about the document:

1. What type of document is this? (e.g., technical spec, decision doc, proposal)
2. Who's the primary audience?
3. What's the desired impact when someone reads this?
4. Is there a template or specific format to follow?
5. Any other constraints or context to know?

Tell them they can answer in shorthand or dump information however works best for them.

### If user provides a template or mentions a doc type:

- Ask if they have a template document to share
- If they provide a link to a shared document, use the appropriate integration to fetch it
- If they provide a file, read it

### If user mentions editing an existing shared document:

- Use the appropriate integration to read the current state
- Check for images without alt-text
- If images exist without alt-text, explain that when others use Claude to understand the doc, Claude won't be able to see them. Ask if they want alt-text generated. If so, request they paste each image into chat for descriptive alt-text generation.

## Info Dumping

Once initial questions are answered, encourage the user to dump all the context they have. Request information such as:

- Background on the project/problem
- Related team discussions or shared documents
- Why alternative solutions aren't being used
- Organizational context (team dynamics, past incidents, politics)
- Timeline pressures or constraints
- Technical architecture or dependencies
- Stakeholder concerns

Advise them not to worry about organizing it — just get it all out. Offer multiple ways to provide context:

- Info dump stream-of-consciousness
- Point to team channels or threads to read
- Link to shared documents

**If integrations are available** (e.g., Slack, Teams, Google Drive, SharePoint, or other MCP servers), mention that these can be used to pull in context directly.

**If no integrations are detected and in Claude.ai or Claude app:** Suggest they can enable connectors in their Claude settings to allow pulling context from messaging apps and document storage directly.

Tell them you'll ask clarifying questions once they've done their initial dump.

## During Context Gathering

- **If user mentions team channels or shared documents:**
  - If integrations available: Tell them you'll read the content now, then use the appropriate integration
  - If integrations not available: Explain lack of access. Suggest they enable connectors in Claude settings, or paste the relevant content directly.

- **If user mentions entities/projects that are unknown:**
  - Ask if you should search connected tools to learn more
  - Wait for user confirmation before searching

- As user provides context, track what you've learned and what's still unclear

## Clarifying Questions

When the user signals they've done their initial dump (or after substantial context provided), ask clarifying questions to ensure understanding:

Generate 5-10 numbered questions based on gaps in the context.

Tell them they can use shorthand to answer (e.g., "1: yes, 2: see #channel, 3: no because backwards compat"), link to more docs, point to channels to read, or just keep info-dumping. Whatever's most efficient for them.

## Exit Condition & Transition

**Exit condition:** Sufficient context has been gathered when your questions show understanding — when you can ask about edge cases and trade-offs without needing the basics explained.

**Transition:** Ask if there's any more context they want to provide at this stage, or if it's time to move on to drafting the document.

If user wants to add more, let them. When ready, proceed to Stage 2.
