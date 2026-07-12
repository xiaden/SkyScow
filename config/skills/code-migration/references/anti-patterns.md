# Anti-Patterns

Code examples for each anti-pattern.

## Deprecation Warnings

```python
# ❌ Wrong - deprecation is procrastination
import warnings
warnings.warn("Use path_comp instead", DeprecationWarning)
```

## Keeping It Around "Just In Case"

```python
# ❌ Wrong - dead code that looks alive
def old_path_builder(path: str) -> str:
    """DEPRECATED: Use path_comp.build_library_path_from_input()"""
    ...
```

Delete it. Git remembers.

## TODO: Remove After Migration

```python
# ❌ Wrong - TODOs are lies
# TODO: Remove this once all callers use the new API
def legacy_function():
    ...
```

Remove it now. The migration isn't done until it's gone.

## Wrapper For Compatibility

```python
# ❌ Wrong - shims become permanent
def get_path(path: str) -> str:
    """Compatibility wrapper."""
    return path_comp.build_library_path_from_input(path).absolute
```

Update the callers directly. Shims become permanent.
