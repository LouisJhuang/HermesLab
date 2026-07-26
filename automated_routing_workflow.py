"""
automated_routing_workflow.py

Implements the task routing rules defined in automated-routing-workflow.md
using the QA criteria and PM acceptance criteria produced by upstream tasks.

This module is intentionally additive: it does not modify kanban state by
itself. Instead it evaluates task evidence/comments and returns the
next recommended action so a real controller can apply it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Optional


class TaskVerdict(str, Enum):
    PASSED = "passed"
    PASSED_WITH_FOLLOWUPS = "passed-with-follow-ups"
    FAILED = "failed"
    BLOCKED = "blocked"
    NOT_TESTED = "not-tested"


class RouteAction(str, Enum):
    ROUTE_TO_QA = "route_to_qa"
    ROUTE_TO_PM = "route_to_pm"
    RETURN_TO_DEV = "return_to_dev"
    COMPLETE = "complete"


class StatusSuggestion(str, Enum):
    QA_READY = "qa-ready"
    PM_READY = "pm-ready"
    ACTIVE_DEVELOPMENT = "active-development"
    COMPLETE = "complete"


@dataclass
class QAVerdictComment:
    """Represents parsed QA verdict evidence from task comments."""

    verdict: TaskVerdict
    tested: List[str] = field(default_factory=list)
    passed: List[str] = field(default_factory=list)
    failed_or_blocked: List[str] = field(default_factory=list)
    next_action: Optional[str] = None


@dataclass
class PMReviewComment:
    """Represents parsed PM review evidence from task comments."""

    decision: str  # Expected: Approved / Rejected / needs-criteria-clarification
    business_alignment: Optional[str] = None
    blockers: Optional[str] = None
    next_step: Optional[str] = None


@dataclass
class TaskRoutingInput:
    """Minimal task evidence needed to decide routing."""

    task_id: str
    assignee: Optional[str] = None
    status: Optional[str] = None
    has_qa_verdict: bool = False
    qa_verdict: Optional[QAVerdictComment] = None
    has_pm_review: bool = False
    pm_review: Optional[PMReviewComment] = None
    has_evidence: bool = False
    evidence_summary: Optional[str] = None


def _qa_routes_forward(verdict: TaskVerdict) -> bool:
    return verdict in {TaskVerdict.PASSED, TaskVerdict.PASSED_WITH_FOLLOWUPS}


def route_task(task: TaskRoutingInput) -> tuple[RouteAction, StatusSuggestion, str]:
    """
    Decide next routing action for a task based on available evidence.

    Returns:
      (next_action, suggested_status, reason)

    Rules:
      - If QA verdict is failed/blocked/not-tested -> return_to_dev
      - If QA passed/passed-with-followups -> route_to_pm
      - If PM review indicates Approved -> complete
      - If PM review indicates Rejected/clarification -> return_to_dev
      - If evidence is missing -> route_to_qa with blocked status
    """

    if not task.has_evidence or not task.evidence_summary:
        return (
            RouteAction.ROUTE_TO_QA,
            StatusSuggestion.QA_READY,
            "Missing verification evidence before QA can start.",
        )

    if not task.has_qa_verdict or task.qa_verdict is None:
        return (
            RouteAction.ROUTE_TO_QA,
            StatusSuggestion.QA_READY,
            "Task is development-complete and QA verdict is not yet recorded.",
        )

    qa = task.qa_verdict.verdict

    if not _qa_routes_forward(qa):
        return (
            RouteAction.RETURN_TO_DEV,
            StatusSuggestion.ACTIVE_DEVELOPMENT,
            f"QA verdict is {qa.value}; stop forward routing until rework is ready.",
        )

    if not task.has_pm_review or task.pm_review is None:
        return (
            RouteAction.ROUTE_TO_PM,
            StatusSuggestion.PM_READY,
            "QA passed; route to PM acceptance review.",
        )

    pm = task.pm_review
    normalized_decision = (pm.decision or "").strip().lower()

    if normalized_decision == "approved":
        return (
            RouteAction.COMPLETE,
            StatusSuggestion.COMPLETE,
            "PM acceptance complete; finalize task.",
        )

    return (
        RouteAction.RETURN_TO_DEV,
        StatusSuggestion.ACTIVE_DEVELOPMENT,
        f"PM decision is {pm.decision}; return to dev with review feedback.",
    )


def summarize_route(action: RouteAction, status: StatusSuggestion, reason: str) -> str:
    return f"[{action.value}] {status.value}: {reason}"
