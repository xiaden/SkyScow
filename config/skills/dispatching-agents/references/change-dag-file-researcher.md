# Change-DAG-File-Researcher

A read-only repository researcher that lets a Worker collapse expensive repository discovery into a disposable context.

## When to Dispatch

- Dispatch only from Change-DAG-Worker, never from Nyx, Change-DAG-Author, or another researcher.
- Dispatch only when repository discovery is becoming expensive or unclear at the Worker's boundary, or the Worker needs caller/dependency/scope orientation it cannot cheaply obtain locally.

**Do NOT dispatch:**

- For trivia the Worker can answer from its own scope.
- Without a concrete question.
- To obtain patches or authoring content.
- To make implementation decisions.
- To repair the graph.
- To replace the Worker's own `dag_search` / `dag_grep` / `dag_read` discovery.
- For whole-repository surveys.

## Dispatch Template

Keep the input packet minimal:

```yaml
task:
  type: FILE_QUERY
  slug: "{dag-slug}"
  node_id: "N7"
  question: "one concrete repository-research question"
authority:
  request_context: "artifacts/requests/CTX_....md"
```

## Required behavior

1. Treat `dag_read` / `dag_grep` / `dag_search` at the given `slug` + `node_id` as the authoritative projected lens; the live tree does not reflect accepted lower DAG work.
2. Use `read` / `glob` / `grep` / `aft_*` / `ast_grep_search` as candidate LOCATORS only.
3. Verify every material finding against the node's DAG-projected source (`dag_read`) before asserting it as a fact.
4. Never write source, never mutate the DAG, never add semantic nodes, never author terminal work, never produce patches or patch suggestions.
5. Never spawn another agent.
6. Return a compact answer with the required output shape.

Researchers never call each other.

## Outcomes

| Result | Meaning |
|---|---|
| `ANSWERED` | The concrete repository-research question was answered with verified, projected-source-grounded findings. |
| `NO_MATCH` | No material surface matched the question at the given boundary. |
| `INCONCLUSIVE` | Available verified evidence does not determine one answer; unresolved points are listed without guessing. |
| `BLOCKED` | The input is not a concrete question or required boundary/source context is unavailable. |

## Expected output

```yaml
answer: ...

required_surfaces:
  - path: ...
    reason: ...

related_surfaces:
  - path: ...
    reason: ...

relationships:
  - ...

scope_assessment:
  complete: true
  broad_same_postcondition: false
  suggested_partitions:
    - ...

unresolved:
  - ...
```

Read-only; its findings are orientation evidence for the Worker, never a decision or a patch.
