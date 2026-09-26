# Logging Patterns

Detailed patterns for common logging scenarios. Each pattern covers when to use it and example code.

## Change DAG Tag Required

Every `log_write` during a fix cycle or Change DAG execution must include the Change DAG slug as a tag:

```python
log_write(
    agent="change-dag-runner",
    category="observation",
    message="Fix revealed deeper issue in query layer",
    tags=["myfeature-change"]  # Mandatory
)
```

This is how QA and managers reconstruct the full execution history.

## Mid-Stream Context Recovery

When picking up a Change DAG mid-execution:

```python
# Get all logs from this work period
log_read(since="<when_dag_execution_started>")

# Get all logs for this specific Change DAG
log_read(tag="<dag_slug>")
```

Both calls are required. The time window alone misses prior sessions; the tag alone misses logs written without the DAG tag.

## Discovery Logging

When you discover something that might help future work:

```python
log_write(
    agent="your-agent-name",
    category="discovery",
    message="Found that X requires Y before Z",
    tags=["module-name", "workflow-name"]
)
```

## Dead-End Logging

When an approach fails:

```python
log_write(
    agent="your-agent-name",
    category="dead-end",
    message="Tried X but it doesn't work because Y",
    tags=["module-name"]
)
```

This prevents future agents (including yourself) from repeating the mistake.
