"""Deterministic, serialized controller core for Change DAG construction.

    The controller is deliberately ephemeral: ``DAG.json`` and the derived frontier are
    its only inputs. Review/admission state lives in this object; the plugin boundary
    owns the awaited native child lifetime because a Python tool process cannot span it.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

from . import change_dag_control as control

DecisionKind = Literal[
    "review_required",
    "admit_worker",
    "child_active",
    "stale_checkpoint",
    "complete",
    "busy",
    "blocked",
]
ReviewRouteKind = Literal[
    "advance",
    "exact_work_fixer",
    "semantic_repair",
    "stop_escalate",
    "stop_review_required",
]
ReviewOutcomeKind = Literal[
    "PASS",
    "EXACT_WORK_DEFECT",
    "SEMANTIC_DEFECT",
    "GRAPH_DEFECT",
    "AUTHORITY_ISSUE",
    "BLOCKED",
]


@dataclass(frozen=True)
class ControllerDecision:
    """A typed, side-effect-free description of the next controller action."""

    kind: DecisionKind
    checkpoint_identity: str | None
    route: ReviewRouteKind | None = None
    node_id: str | None = None
    branch_claim: dict[str, Any] | None = None
    message: str | None = None


@dataclass(frozen=True)
class ReviewOutcome:
    """Read-only reviewer evidence bound to one exact DAG/frontier identity."""

    kind: ReviewOutcomeKind
    checkpoint_identity: str
    message: str | None = None


def route_review_outcome(kind: ReviewOutcomeKind) -> ReviewRouteKind:
    """Select an opaque handoff from typed reviewer evidence."""
    return {
        "PASS": "advance",
        "EXACT_WORK_DEFECT": "exact_work_fixer",
        "SEMANTIC_DEFECT": "semantic_repair",
        "GRAPH_DEFECT": "semantic_repair",
        "AUTHORITY_ISSUE": "stop_escalate",
        "BLOCKED": "stop_review_required",
    }[kind]


@dataclass(frozen=True)
class ControllerState:
    """Ephemeral controller workflow state; never persisted to the DAG bundle."""

    slug: str
    checkpoint_identity: str
    dag_identity: str
    review_accepted: bool = False
    child_active: bool = False


class ConstructionController:
    """Own one serialized construction attachment for one DAG slug.

    ``attach`` takes a short-lived construction flock for atomic inspection and
    review gating. The native plugin adapter separately serializes the awaited child
    prompt within its live plugin process. No task registry or recovery ledger is
    needed: a lost process releases the kernel flock, and a new attachment starts
    conservatively at review.
    """

    def __init__(self, workspace_root: Path, state: ControllerState, lock_fd: int):
        self.workspace_root = Path(workspace_root)
        self.state = state
        self._lock_fd: int | None = lock_fd
        self._closed = False

    @classmethod
    def attach(cls, workspace_root: Path, slug: str) -> "ConstructionController | ControllerDecision":
        """Attach to current DAG identity, or return a deterministic busy decision."""
        root = Path(workspace_root)
        try:
            current = control.inspect_current_state(root, slug)
        except (FileNotFoundError, OSError, ValueError) as exc:
            return ControllerDecision("blocked", None, route="stop_escalate", message=f"current DAG unavailable or invalid: {exc}")
        acquired, lock_fd = control.acquire_construction_lock(root, slug)
        if not acquired or lock_fd is None:
            return ControllerDecision("busy", current["checkpoint_identity"], message="construction lock is held")
        return cls(
            root,
            ControllerState(
                slug=slug,
                checkpoint_identity=secrets.token_urlsafe(24),
                dag_identity=current["checkpoint_identity"],
            ),
            lock_fd,
        )

    @property
    def lock_fd(self) -> int | None:
        """Return the live flock descriptor for an external-child handoff."""
        return self._lock_fd

    def _current(self) -> dict[str, Any]:
        return control.inspect_current_state(self.workspace_root, self.state.slug)

    def _checkpoint(self, current: dict[str, Any]) -> ControllerDecision | None:
        identity = current["checkpoint_identity"]
        if identity != self.state.dag_identity:
            return ControllerDecision(
                "stale_checkpoint",
                identity,
                message="current DAG identity differs from the controller checkpoint",
            )
        return None

    @staticmethod
    def _frontier_node(frontier: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
        payload = frontier.get("frontier")
        if not isinstance(payload, dict):
            return None, None
        candidates: list[tuple[int, str, dict[str, Any]]] = []
        for branch in payload.get("branches", []):
            if not isinstance(branch, dict):
                continue
            claim = branch.get("branch_claim")
            if not isinstance(claim, dict):
                continue
            nodes = claim.get("nodes")
            if not isinstance(nodes, list):
                continue
            for node_id in nodes:
                if isinstance(node_id, str) and node_id.startswith("N") and node_id[1:].isdigit():
                    candidates.append((int(node_id[1:]), node_id, claim))
        if not candidates:
            return None, None
        _, node_id, claim = min(candidates)
        return node_id, claim

    def _closed_decision(self) -> ControllerDecision | None:
        if self._closed:
            return ControllerDecision("blocked", None, route="stop_escalate", message="controller attachment is closed")
        return None

    def next_action(self) -> ControllerDecision:
        """Derive the next action from current DAG data, without mutating it."""
        closed = self._closed_decision()
        if closed is not None:
            return closed
        try:
            current = self._current()
        except (FileNotFoundError, OSError, ValueError) as exc:
            return ControllerDecision("blocked", None, route="stop_escalate", message=f"current DAG unavailable or invalid: {exc}")
        stale = self._checkpoint(current)
        if stale is not None:
            return stale
        if self.state.child_active:
            return ControllerDecision("child_active", self.state.checkpoint_identity, message="worker admission is already active")
        if not self.state.review_accepted:
            return ControllerDecision("review_required", self.state.checkpoint_identity)
        frontier = current["frontier"]
        if frontier.get("resolved") is True:
            return ControllerDecision("complete", self.state.checkpoint_identity, route="advance")
        node_id, claim = self._frontier_node(frontier)
        if node_id is None:
            return ControllerDecision("complete", self.state.checkpoint_identity, route="advance", message="no authorable frontier")
        return ControllerDecision("admit_worker", self.state.checkpoint_identity, route="advance", node_id=node_id, branch_claim=claim)

    def submit_review(self, review: ReviewOutcome) -> ControllerDecision:
        """Consume reviewer evidence without interpreting its semantic content.

        Only a PASS can admit work. Every other typed outcome remains external
        evidence for the owning author/controller; this service merely keeps the
        frontier closed. A verdict is never persisted and cannot mutate the DAG.
        """
        closed = self._closed_decision()
        if closed is not None:
            return closed
        try:
            current = self._current()
        except (FileNotFoundError, OSError, ValueError) as exc:
            return ControllerDecision("blocked", None, route="stop_escalate", message=f"current DAG unavailable or invalid: {exc}")
        if current["checkpoint_identity"] != self.state.dag_identity or review.checkpoint_identity not in {current["checkpoint_identity"], self.state.checkpoint_identity}:
            return ControllerDecision("stale_checkpoint", current["checkpoint_identity"], message="review identity is stale")
        if review.kind not in ("PASS", "EXACT_WORK_DEFECT", "SEMANTIC_DEFECT", "GRAPH_DEFECT", "AUTHORITY_ISSUE", "BLOCKED"):
            raise ValueError(f"unknown review outcome: {review.kind!r}")
        route = route_review_outcome(review.kind)
        if review.kind != "PASS":
            self.state = replace(self.state, review_accepted=False)
            return ControllerDecision("review_required", self.state.checkpoint_identity, route=route, message=review.message or review.kind)
        self.state = replace(self.state, review_accepted=True)
        return self.next_action()

    def accept_review(self, checkpoint_identity: str) -> ControllerDecision:
        """Compatibility shorthand for submitting a typed PASS outcome."""
        return self.submit_review(ReviewOutcome("PASS", checkpoint_identity))

    def accept_dag_review(self, checkpoint_identity: str) -> ControllerDecision:
        """Accept a PASS bound to the deterministic current DAG checkpoint."""
        if self._closed:
            return self._closed_decision() or ControllerDecision("blocked", None, route="stop_escalate")
        try:
            current = self._current()
        except (FileNotFoundError, OSError, ValueError) as exc:
            return ControllerDecision("blocked", None, route="stop_escalate", message=f"current DAG unavailable or invalid: {exc}")
        if checkpoint_identity != current["checkpoint_identity"]:
            return ControllerDecision("stale_checkpoint", current["checkpoint_identity"], message="review identity is stale")
        self.state = replace(self.state, review_accepted=True, checkpoint_identity=checkpoint_identity, dag_identity=current["checkpoint_identity"])
        return self.next_action()

    def admit_worker(self, checkpoint_identity: str | None = None) -> ControllerDecision:
        """Atomically reserve one worker admission in this serialized core."""
        action = self.next_action()
        if checkpoint_identity is not None and checkpoint_identity != self.state.checkpoint_identity:
            return ControllerDecision("stale_checkpoint", action.checkpoint_identity, message="admission checkpoint is stale")
        if action.kind != "admit_worker":
            return action
        self.state = replace(self.state, child_active=True)
        return action

    def complete_child(self) -> ControllerDecision:
        """Release the in-memory admission only after the external child exits."""
        if not self.state.child_active:
            return self.next_action()
        try:
            current = self._current()
        except (FileNotFoundError, OSError, ValueError) as exc:
            return ControllerDecision("blocked", None, route="stop_escalate", message=f"current DAG unavailable or invalid: {exc}")
        stale = self._checkpoint(current)
        if stale is not None:
            self.state = replace(
                self.state,
                child_active=False,
                checkpoint_identity=secrets.token_urlsafe(24),
                dag_identity=current["checkpoint_identity"],
                review_accepted=False,
            )
            return stale
        # A completed worker always closes the reviewed frontier. Even when the
        # worker made no DAG change, advancement requires one fresh review for
        # this completed serialized work unit.
        self.state = replace(self.state, child_active=False, review_accepted=False)
        return self.next_action()

    def close(self) -> None:
        """Release construction ownership; safe to call repeatedly."""
        if self._lock_fd is None:
            self._closed = True
            return
        if self.state.child_active:
            raise RuntimeError("cannot release construction lock while a worker is admitted")
        control.release_lock(self._lock_fd)
        self._lock_fd = None
        self._closed = True

    def __enter__(self) -> "ConstructionController":
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.close()
