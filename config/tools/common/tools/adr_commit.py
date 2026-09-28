"""Tool implementation for adr_commit — write an approved ADR to disk."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from ..helpers.adr_md import (
    ADR,
    DRAFTS_DIR,
    _unescape_literal_newlines,
    adr_number_from_token,
    adr_status_dir,
    find_adr_in_status_dir,
    find_adr_number,
    generate_adr,
    iter_adr_records,
    make_adr_filename,
    next_adr_number,
    parse_adr,
    parse_adr_metadata,
    supersede_adr_record,
    today_iso,
    validate_source_log,
    validate_status,
)
from ..helpers.governance_index import (
    GovernanceIndexError,
    rebuild_governance_indexes,
)

_STANDARD_SECTION_NAMES: frozenset[str] = frozenset(
    {"Context", "Decision", "Consequences", "References"}
)

_MAX_RETRIES = 3


def _withdraw_published_adr(
    target_path: Path, supersession_edits: list[tuple[Path, str, Path]]
) -> None:
    """Best-effort reversal of a published ADR and its supersession moves."""
    for source, original_text, destination in reversed(supersession_edits):
        with contextlib.suppress(OSError):
            destination.unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            source.write_text(original_text, encoding="utf-8")
    with contextlib.suppress(OSError):
        target_path.unlink(missing_ok=True)


def adr_commit(
    title: str = "",
    status: str = "",
    tags: list[str] | None = None,
    context: str = "",
    decision: str = "",
    consequences: str = "",
    references: str = "",
    source_log: str = "",
    extra_sections: list[dict[str, str]] | None = None,
    supersedes: list[str] | None = None,
    draft_id: str = "",
    *,
    workspace_root: Path,
) -> dict[str, Any]:
    """Write an approved ADR to disk atomically.

    Performs full validation (defense in depth) and writes with retry-on-collision.
    Returns {"path": "...", "number": N, "title": "...", "markdown": "...", ...} on success.
    Returns {"error": "...", "message": "..."} on failure.
    """
    if supersedes is None:
        supersedes = []
    if tags is None:
        tags = []

    # Load from staging draft if draft_id provided
    _draft_file: Path | None = None
    if draft_id:
        _draft_file = workspace_root / DRAFTS_DIR / f"DRAFT-{draft_id}.md"
        if not _draft_file.exists():
            return {
                "error": "draft_not_found",
                "message": (
                    f"No draft found for '{draft_id}'. "
                    "Run adr_suggest first to create a staging draft."
                ),
            }
        try:
            _parsed = parse_adr(_draft_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            return {"error": "draft_parse_error", "message": str(e)}

        # Use draft fields as defaults; explicit non-empty params override
        if not title.strip():
            title = _parsed.title
        if not status.strip():
            status = _parsed.status
        if not tags:
            tags = _parsed.tags
        if not context.strip():
            context = _parsed.sections.get("Context", "")
        if not decision.strip():
            decision = _parsed.sections.get("Decision", "")
        if not consequences.strip():
            consequences = _parsed.sections.get("Consequences", "")
        if not references.strip():
            references = _parsed.sections.get("References", "")
        if not source_log.strip() and _parsed.source_log:
            source_log = _parsed.source_log
        if not supersedes and _parsed.supersedes:
            supersedes = _parsed.supersedes
        if extra_sections is None:
            _extra = [
                {"heading": h, "content": c}
                for h, c in _parsed.sections.items()
                if h not in _STANDARD_SECTION_NAMES
            ]
            if _extra:
                extra_sections = _extra

    # Validate inputs (defense in depth — same checks as adr_suggest)
    if not title.strip():
        return {"error": "invalid_title", "message": "Title cannot be empty"}

    status_err = validate_status(status)
    if status_err:
        return {"error": "invalid_status", "message": status_err}

    if not tags:
        return {"error": "invalid_tags", "message": "At least one tag is required"}

    if not context.strip():
        return {"error": "invalid_section", "message": "Context section cannot be empty"}
    if not decision.strip():
        return {"error": "invalid_section", "message": "Decision section cannot be empty"}
    if not consequences.strip():
        return {"error": "invalid_section", "message": "Consequences section cannot be empty"}

    if source_log:
        sl_err = validate_source_log(source_log)
        if sl_err:
            return {"error": "invalid_source_log", "message": sl_err}

    # Unescape literal newlines from MCP transport
    context = _unescape_literal_newlines(context)
    decision = _unescape_literal_newlines(decision)
    consequences = _unescape_literal_newlines(consequences)
    references = _unescape_literal_newlines(references)

    if extra_sections:
        extra_sections = [
            {
                "heading": es.get("heading", ""),
                "content": _unescape_literal_newlines(es.get("content", "")),
            }
            for es in extra_sections
        ]

    # Build sections dict preserving order
    sections: dict[str, str] = {
        "Context": context,
        "Decision": decision,
        "Consequences": consequences,
    }

    # Add extra sections
    if extra_sections:
        for es in extra_sections:
            heading = es.get("heading", "")
            content = es.get("content", "")
            if heading.strip() and content.strip():
                sections[heading] = content

    # References last
    if references.strip():
        sections["References"] = references

    # Check for source_log duplicates in existing ADRs
    source_log_warning: str | None = None
    if source_log:
        for adr_file in iter_adr_records(workspace_root):
            try:
                content = adr_file.read_text(encoding="utf-8")
                meta = parse_adr_metadata(content)
                existing_sl = meta.get("source_log")
                if existing_sl and existing_sl == source_log:
                    existing_num = meta.get("number", "?")
                    source_log_warning = (
                        f"source_log '{source_log}' is also used by "
                        f"ADR-{existing_num:03d}. Consider using a unique log reference."
                    )
                    break
            except (OSError, ValueError):
                continue

    # Resolve and pre-validate supersession targets before any write. A bad
    # reference must fail the commit without leaving a partially published ADR.
    supersede_numbers: list[int] = []
    for token in supersedes:
        target_number = adr_number_from_token(token)
        if target_number is None:
            return {
                "error": "invalid_supersedes",
                "message": (
                    f"Unrecognized ADR identifier in supersedes: '{token}' "
                    "(expected e.g. 'ADR-007')"
                ),
            }
        if target_number in supersede_numbers:
            continue
        if find_adr_number(workspace_root, target_number) is None:
            return {
                "error": "supersedes_not_found",
                "message": (
                    f"Cannot supersede ADR-{target_number:03d}: "
                    "no committed ADR with that ID"
                ),
            }
        accepted_copy = find_adr_in_status_dir(workspace_root, "Accepted", target_number)
        superseded_copy = find_adr_in_status_dir(
            workspace_root, "Superseded", target_number
        )
        if accepted_copy is not None and superseded_copy is not None:
            return {
                "error": "supersedes_conflict",
                "message": (
                    f"ADR-{target_number:03d} has both an accepted and a superseded "
                    "copy; resolve the duplicate before committing"
                ),
            }
        supersede_numbers.append(target_number)

    # Committed ADRs live under the workspace-local governance skill, in the
    # directory for their status. "Proposed" has no committed directory.
    try:
        target_dir = adr_status_dir(workspace_root, status)
    except ValueError as exc:
        return {"error": "uncommittable_status", "message": str(exc)}
    target_dir.mkdir(parents=True, exist_ok=True)

    for _attempt in range(_MAX_RETRIES):
        number = next_adr_number(workspace_root)
        filename = make_adr_filename(number, title)
        target_path = target_dir / filename

        adr = ADR(
            number=number,
            title=title.strip(),
            status=status,
            date=today_iso(),
            tags=[t.strip() for t in tags if t.strip()],
            source_log=source_log or None,
            supersedes=supersedes,
            sections=sections,
        )

        markdown = generate_adr(adr)

        try:
            # Atomic create — fails if file exists (exclusive mode)
            with open(target_path, "x", encoding="utf-8") as f:
                f.write(markdown)
            rel_path = str(target_path.relative_to(workspace_root)).replace("\\", "/")

            result: dict[str, Any] = {
                "path": rel_path,
                "number": number,
                "title": adr.title,
                "markdown": markdown,
            }

            # Content quality warning
            word_count = len(" ".join([context, decision, consequences]).split())
            if word_count < 100:
                result["content_warning"] = (
                    f"ADR has only {word_count} words across body sections "
                    f"(minimum recommended: 100). Consider expanding before accepting."
                )

            if source_log_warning:
                result["source_log_warning"] = source_log_warning

            # Apply the declared supersession transition. Targets were
            # pre-validated above; a target already outside accepted/ needs no
            # move because it is already non-governing.
            supersession_edits: list[tuple[Path, str, Path]] = []
            superseded_moves: list[dict[str, Any]] = []
            try:
                for target_number in supersede_numbers:
                    source = find_adr_in_status_dir(
                        workspace_root, "Accepted", target_number
                    )
                    if source is None:
                        continue
                    original_text = source.read_text(encoding="utf-8")
                    new_path = supersede_adr_record(workspace_root, target_number)
                    supersession_edits.append((source, original_text, new_path))
                    superseded_moves.append(
                        {
                            "number": target_number,
                            "from": str(source.relative_to(workspace_root)).replace(
                                "\\", "/"
                            ),
                            "to": str(new_path.relative_to(workspace_root)).replace(
                                "\\", "/"
                            ),
                        }
                    )
            except OSError as exc:
                _withdraw_published_adr(target_path, supersession_edits)
                return {
                    "error": "supersession_failed",
                    "message": str(exc),
                }

            # Regenerate the governing index from the reference corpus. Fail
            # closed: withdraw the just-published record (and reverse any
            # supersession moves) rather than leave a knowingly stale index.
            try:
                index_summary = rebuild_governance_indexes(workspace_root)
            except GovernanceIndexError as exc:
                _withdraw_published_adr(target_path, supersession_edits)
                return {
                    "error": "index_rebuild_failed",
                    "message": str(exc),
                }

            if superseded_moves:
                result["superseded"] = superseded_moves
            result["index"] = index_summary

            # Remove the staging draft now that the ADR is committed
            if _draft_file is not None:
                with contextlib.suppress(OSError):
                    _draft_file.unlink(missing_ok=True)

            import json as _json_
            return {
                "output": _json_.dumps(result),
                "title": "Commit ADR",
                "metadata": {"target": f"{number}: {adr.title}"},
            }
        except FileExistsError:
            continue

    return {
        "error": "collision",
        "message": f"Failed to create ADR after {_MAX_RETRIES} retries due to numbering collision",
    }


if __name__ == "__main__":
    import json
    import sys
    args = json.loads(sys.stdin.read())
    result = adr_commit(
        title=args.get("title", ""),
        status=args.get("status", ""),
        tags=args.get("tags"),
        context=args.get("context", ""),
        decision=args.get("decision", ""),
        consequences=args.get("consequences", ""),
        references=args.get("references", ""),
        source_log=args.get("source_log", ""),
        extra_sections=args.get("extra_sections"),
        supersedes=args.get("supersedes"),
        draft_id=args.get("draft_id", ""),
        workspace_root=Path(args["workspace_root"]),
    )
    print(json.dumps(result))
