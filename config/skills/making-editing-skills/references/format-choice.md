# Format Choice: Tables, Lists, and Prose

Guidance on choosing the right structural format for skill content, backed by recent context-engineering research.

## The Heuristic

| Data shape | Use | Why |
|------------|-----|-----|
| Relational / comparative (trigger→action, field→description) | **Table** | Models localize information faster when rows = objects and columns = properties |
| Sequential / procedural (steps, ordered instructions) | **Bullet list** | Order carries meaning; lists eliminate connective prose and increase token density |
| Narrative explanation (rationale, context, "why") | **Prose paragraph** | Some ideas need sentences; just keep them short |

## Evidence

### Tables for relational data

Tabular representation gives roughly **+40% accuracy** over text/JSON/graphs for analytical queries on object-property data (He et al., arXiv:2412.17189). Tables improve the model's ability to localize relevant information — column headers act as semantic labels, and the grid structure forces clean boundaries between data points. Markdown pipe tables are also ~2× more token-efficient than equivalent HTML tables (BulkMD, 2026).

### Lists for classification and procedures

Bullet points **consistently outperform plain descriptions** for classification and selection tasks across 9 domains (arXiv:2503.06926). The likely cause: LLM pretraining corpora are rich in bulleted formats (GitHub READMEs, Stack Overflow, documentation). Bullets also have higher token density than tables (3.7 vs 3.2 chars/token) since they eliminate column-separator overhead for non-tabular data.

### The limits of format optimization

A large-scale study of 9,649 experiments across 11 models found that **format choice did not significantly affect aggregate accuracy** (chi-squared=2.45, p=0.484; McMillan, arXiv:2602.05447, Feb 2026). Model capability dwarfs format effects — a 21 percentage point gap between frontier and open-source models. Format sensitivities exist at the individual model level, but the practical takeaway is: match format to data shape, then invest in model capability and context structure, not format micro-optimization.

### What matters more than format

More recent work (April–July 2026) emphasizes **context structure** over format:

- **File-based authority** outperforms verbal instructions by a ~60pp quality gap — write your standards in a file, don't embed them in prompts (arXiv:2604.04258)
- **Triple-placement** of format instructions (system prompt + before task + compressed at end) prevents format drift in long contexts (PromptEval, June 2026)
- **Explicit delimiters** between instruction, context, and data regions reduce ambiguity (multiple vendor guides, 2026)

## A note on scope

This guidance covers **content structure for instructional text** — skill files, documentation, agent prompts. For **data serialization formats** (encoding large repeated payloads for evidence-heavy production workflows), a different ranking applies: lossless evidence aliases → TOON tables → CSV/TSV → XML sections → YAML → JSON. See MightyBot's [structured prompt format ranking](https://mightybot.ai/blog/best-structured-prompt-formats-for-llms/) (May 2026) for that domain.

## References

- He et al., "Table Serialization Formats and LLM Comprehension," arXiv:2412.17189
- "Effect of Selection Format on LLM Performance," arXiv:2503.06926
- McMillan, "Structured Context Engineering for File-Native Agentic Systems," arXiv:2602.05447 (Feb 2026)
- "Context Engineering: A Methodology for Structured Human-AI Collaboration," arXiv:2604.04258 (Apr 2026)
- Kryvolapov, "Prompt Engineering Techniques for LLMs" (Feb 2026) — tables-vs-lists heuristic
- PromptEval, "How to Specify Output Format in AI Prompts" (June 2026) — triple-placement method
