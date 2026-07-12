---
description: Run structured evaluation against acceptance criteria
argument-hint: "<evaluation context or criteria>"
---

# Eval Command

Evaluate implementation against acceptance criteria: $ARGUMENTS

## Your Task

Run a structured evaluation to verify the implementation meets requirements.

## Evaluation Framework

### Grader Types

1. **Binary Grader** — Pass/Fail
   - Does it work? Yes/No
   - Good for: feature completion, bug fixes, presence/absence checks

2. **Scalar Grader** — Score 0-100
   - How well does it work?
   - Good for: performance, code quality, user experience quality

3. **Rubric Grader** — Category scores
   - Multiple dimensions evaluated independently
   - Good for: comprehensive review, design quality, multi-faceted features

## Evaluation Process

### Step 1: Define Criteria

Extract or define acceptance criteria from the task or requirements:

```
Acceptance Criteria:
1. [Criterion 1] — [weight: XX%]
2. [Criterion 2] — [weight: XX%]
3. [Criterion 3] — [weight: XX%]
```

### Step 2: Gather Evidence

For each criterion, collect objective evidence:

- **Test results**: Run the relevant test suite
- **Manual verification**: Check the behavior directly
- **Code inspection**: Review the implementation
- **Metrics**: Measure performance, coverage, bundle size

### Step 3: Score Each Criterion

Apply the appropriate grader to each criterion:

- Binary: 0 (fail) or 100 (pass)
- Scalar: 0-100 based on quality
- Rubric: score per category, weight accordingly

### Step 4: Calculate Final Score

```
Final Score = Σ (criterion_score × weight) / total_weight
```

Pass threshold: ≥ 70% or all critical criteria pass.

### Step 5: Report

Produce the evaluation report with evidence and recommendations.

## Evaluation Report

### Overall: PASS / FAIL (Score: X/100)

### Criterion Breakdown

| # | Criterion | Type | Score | Weight | Weighted Score |
|---|-----------|------|-------|--------|----------------|
| 1 | [Name] | Binary | PASS/FAIL | 30% | X |
| 2 | [Name] | Scalar | XX/100 | 40% | X |
| 3 | [Name] | Rubric | XX/100 | 30% | X |

### Evidence

**Criterion 1: [Name]**
- **Test:** [what was tested and how]
- **Result:** [outcome with specific data]
- **Evidence:** [screenshot, log output, file reference]

**Criterion 2: [Name]**
- **Test:** [what was tested and how]
- **Result:** [outcome with specific data]
- **Evidence:** [screenshot, log output, file reference]

### Pass@K Metrics

For non-deterministic or flaky behaviors:

- Run the test K times
- Count how many times it passes
- Report: "Pass@K = X/K" (e.g., "Pass@10 = 8/10")

### Recommendations

If overall score is below threshold or any critical criterion fails:

1. [Highest priority fix with rationale]
2. [Next priority fix with rationale]
3. [Optional improvements]

---

**TIP**: Use `/eval` before marking features complete. Running it early catches issues when they're cheapest to fix.
**TIP**: For flaky tests, use Pass@K metrics to distinguish implementation bugs from test instability.
