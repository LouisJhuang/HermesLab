"""Tests for automated_routing_workflow routing rules."""

from automated_routing_workflow import (
    PMReviewComment,
    QAVerdictComment,
    RouteAction,
    StatusSuggestion,
    TaskRoutingInput,
    TaskVerdict,
    route_task,
    summarize_route,
)


def qa_verdict(verdict: TaskVerdict) -> QAVerdictComment:
    return QAVerdictComment(verdict=verdict)


def pm_review(decision: str) -> PMReviewComment:
    return PMReviewComment(decision=decision)


def dev_complete_base() -> TaskRoutingInput:
    return TaskRoutingInput(
        task_id="t_example",
        assignee="agent-dev",
        status="in-progress",
        has_qa_verdict=False,
        has_pm_review=False,
        has_evidence=True,
        evidence_summary="run path + acceptance criteria provided",
    )


def test_routes_to_qa_when_no_qa_verdict():
    task = dev_complete_base()
    action, status, reason = route_task(task)
    assert action == RouteAction.ROUTE_TO_QA
    assert status == StatusSuggestion.QA_READY


def test_routes_back_to_dev_on_qa_failed():
    task = dev_complete_base()
    task.qa_verdict = qa_verdict(TaskVerdict.FAILED)
    task.has_qa_verdict = True
    action, status, reason = route_task(task)
    assert action == RouteAction.RETURN_TO_DEV
    assert status == StatusSuggestion.ACTIVE_DEVELOPMENT


def test_routes_back_to_dev_on_qa_blocked():
    task = dev_complete_base()
    task.qa_verdict = qa_verdict(TaskVerdict.BLOCKED)
    task.has_qa_verdict = True
    action, status, reason = route_task(task)
    assert action == RouteAction.RETURN_TO_DEV


def test_qa_passed_routes_to_pm():
    task = dev_complete_base()
    task.qa_verdict = qa_verdict(TaskVerdict.PASSED)
    task.has_qa_verdict = True
    action, status, reason = route_task(task)
    assert action == RouteAction.ROUTE_TO_PM
    assert status == StatusSuggestion.PM_READY


def test_qa_passed_with_followups_still_routes_to_pm():
    task = dev_complete_base()
    task.qa_verdict = qa_verdict(TaskVerdict.PASSED_WITH_FOLLOWUPS)
    task.has_qa_verdict = True
    action, status, reason = route_task(task)
    assert action == RouteAction.ROUTE_TO_PM


def test_pm_approved_completes():
    task = dev_complete_base()
    task.qa_verdict = qa_verdict(TaskVerdict.PASSED)
    task.has_qa_verdict = True
    task.pm_review = pm_review("Approved")
    task.has_pm_review = True
    action, status, reason = route_task(task)
    assert action == RouteAction.COMPLETE
    assert status == StatusSuggestion.COMPLETE


def test_pm_rejected_returns_to_dev():
    task = dev_complete_base()
    task.qa_verdict = qa_verdict(TaskVerdict.PASSED)
    task.has_qa_verdict = True
    task.pm_review = pm_review("Rejected")
    task.has_pm_review = True
    action, status, reason = route_task(task)
    assert action == RouteAction.RETURN_TO_DEV


def test_missing_evidence_blocks_qa_routing():
    task = dev_complete_base()
    task.has_evidence = False
    action, status, reason = route_task(task)
    assert action == RouteAction.ROUTE_TO_QA
    assert status == StatusSuggestion.QA_READY


def test_not_tested_stops_forward_routing():
    task = dev_complete_base()
    task.qa_verdict = qa_verdict(TaskVerdict.NOT_TESTED)
    task.has_qa_verdict = True
    action, status, reason = route_task(task)
    assert action == RouteAction.RETURN_TO_DEV
    assert status == StatusSuggestion.ACTIVE_DEVELOPMENT


def test_summarize_route_produces_readable_line():
    text = summarize_route(RouteAction.ROUTE_TO_PM, StatusSuggestion.PM_READY, "ok")
    assert text.startswith("[route_to_pm]")
    assert "pm-ready" in text


if __name__ == "__main__":
    print("parsed: automated_routing_workflow tests")
