"""
Quality check for the AI assistant.

Runs a fixed set of test questions through the real pipeline (input guardrails,
agent graph, retrieval, answer writing, verification) as the calling user and
reports which ones behaved as expected.  Nothing is simulated: a failing case
means the assistant really gave a wrong or missing answer.
"""
import json
import time
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.agents.graph import agent_graph
from app.agents.guardrails import AIGuardrails
from app.database.connection import get_db
from app.middleware.rbac import require
from app.security.permissions import Perm, build_user_context
from app.models.models import EvaluationRun

router = APIRouter(prefix="/api/evaluations", tags=["AI evaluation"])
DATASET = Path(__file__).resolve().parents[2] / "evaluation_dataset.json"
SUITE = "assistant_quality_check"

METRIC_LABELS = {
    "pass_rate": "Test questions passed",
    "answer_accuracy": "Questions answered correctly",
    "guardrail_block_rate": "Unsafe prompts blocked",
    "grounding_score": "Answers backed by retrieved data",
    "avg_latency_ms": "Average response time (ms)",
}


def _run_case(case: dict, user_context: dict) -> dict:
    started = time.time()
    query = case.get("query", "")
    expect = case.get("expect", "answer")
    result = {"id": case.get("id"), "category": case.get("category", ""), "query": query, "expected": expect}

    is_safe, _ = AIGuardrails.check_input(query)
    if not is_safe:
        result.update(outcome="blocked", passed=(expect == "blocked"),
                      detail="Blocked by the input guardrail." if expect == "blocked" else "Wrongly blocked by the input guardrail.",
                      grounding=None)
    else:
        try:
            state = agent_graph.invoke({
                "messages": [{"role": "user", "content": query}],
                "user_context": user_context, "retrieved_context": [], "agent_trace": [],
            })
            answers = [m for m in state.get("messages", []) if m.get("role") == "assistant"]
            answer = answers[-1]["content"] if answers else ""
            traces = state.get("agent_trace") or []
            grounding = float(traces[-1].get("confidence_score", 0)) if traces else 0.0
            if expect == "blocked":
                result.update(outcome="answered", passed=False, detail="This prompt should have been blocked.", grounding=None)
            else:
                missing = [t for t in case.get("must_contain", []) if t.lower() not in answer.lower()]
                result.update(
                    outcome="answered", passed=not missing, grounding=grounding,
                    detail="Answer contained the expected facts." if not missing else f"Answer did not mention: {', '.join(missing)}.",
                )
        except Exception as e:
            result.update(outcome="error", passed=False, detail=f"The assistant failed: {str(e)[:120]}", grounding=None)

    result["latency_ms"] = int((time.time() - started) * 1000)
    return result


@router.post("/run")
def run_evaluations(user=Depends(require(Perm.SYSTEM_EVALUATE)), db: Session = Depends(get_db)):
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    user_context = build_user_context(user)
    results = [_run_case(case, user_context) for case in cases]

    answer_cases = [r for r in results if r["expected"] == "answer"]
    guard_cases = [r for r in results if r["expected"] == "blocked"]
    grounded = [r["grounding"] for r in answer_cases if r.get("grounding") is not None]

    def rate(rows):
        return round(sum(1 for r in rows if r["passed"]) / len(rows), 3) if rows else 1.0

    metrics = {
        "pass_rate": rate(results),
        "answer_accuracy": rate(answer_cases),
        "guardrail_block_rate": rate(guard_cases),
        "grounding_score": round(sum(grounded) / len(grounded), 3) if grounded else 0.0,
        "avg_latency_ms": round(sum(r["latency_ms"] for r in results) / len(results), 1) if results else 0.0,
    }
    for metric, score in metrics.items():
        db.add(EvaluationRun(suite_name=SUITE, metric_name=metric, score=score, sample_count=len(cases),
                             details=f"Run by employee {user.employee_id} ({user_context['role']})"))
    db.commit()
    return {
        "dataset_cases": len(cases),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": sum(1 for r in results if not r["passed"]),
        "run_as_role": user_context["role"],
        "metrics": metrics,
        "metric_labels": METRIC_LABELS,
        "cases": results,
    }


@router.get("/history")
def history(user=Depends(require(Perm.SYSTEM_EVALUATE)), db: Session = Depends(get_db)):
    """Pass rate of earlier quality-check runs, newest first."""
    rows = db.query(EvaluationRun).filter(
        EvaluationRun.suite_name == SUITE, EvaluationRun.metric_name == "pass_rate"
    ).order_by(EvaluationRun.created_at.desc()).limit(20).all()
    return [{"metric": r.metric_name, "score": float(r.score), "samples": r.sample_count, "created_at": r.created_at, "details": r.details} for r in rows]
