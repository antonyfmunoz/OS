"""
Goal API — REST endpoints for goal selection + focus management.

Endpoints:
    GET  /goals              — list all goals (optional ?state= filter)
    POST /goals              — create a goal
    GET  /goals/<id>         — get single goal + explainability
    POST /goals/<id>/activate — force-activate a goal
    POST /goals/<id>/defer    — defer a goal
    POST /goals/<id>/complete — mark goal completed
    POST /goals/<id>/drop     — drop a goal
    POST /goals/cycle         — run selection cycle

Runs standalone on port 8090, or register(app) to mount on existing Flask.

Usage:
    python3 services/goal_api.py
    curl http://localhost:8090/goals
"""

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from flask import Flask, request, jsonify
from control_plane.goals.goal_selector import GoalSelector, GoalState

app = Flask(__name__)


def _selector() -> GoalSelector:
    budget = int(os.getenv("GOAL_FOCUS_BUDGET", "3"))
    return GoalSelector(focus_budget=budget)


def _goal_to_dict(goal) -> dict:
    return {
        "id": goal.id,
        "title": goal.title,
        "description": goal.description,
        "state": goal.state.value,
        "priority": goal.priority,
        "expected_impact": goal.expected_impact,
        "estimated_cost": goal.estimated_cost,
        "confidence": goal.confidence,
        "dependency_unlock": goal.dependency_unlock,
        "venture_id": goal.venture_id,
        "blocked_by": goal.blocked_by,
        "score": goal.score,
        "rank": goal.rank,
        "score_explanation": goal.score_explanation,
        "created_at": goal.created_at.isoformat(),
        "updated_at": goal.updated_at.isoformat(),
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────


@app.route("/goals", methods=["GET"])
def list_goals():
    state_filter = request.args.get("state")
    sel = _selector()
    if state_filter:
        try:
            state = GoalState(state_filter)
        except ValueError:
            return jsonify({"error": f"Invalid state: {state_filter}"}), 400
        goals = sel.list_goals(state=state)
    else:
        goals = sel.list_goals()
    return jsonify({"goals": [_goal_to_dict(g) for g in goals], "count": len(goals)})


@app.route("/goals", methods=["POST"])
def create_goal():
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not title:
        return jsonify({"error": "title is required"}), 400

    sel = _selector()
    goal = sel.add_goal(
        title=title,
        description=data.get("description", ""),
        priority=data.get("priority", 5),
        expected_impact=data.get("expected_impact", 0.5),
        estimated_cost=data.get("estimated_cost", 0.5),
        confidence=data.get("confidence", 0.5),
        venture_id=data.get("venture_id"),
        blocked_by=data.get("blocked_by", []),
    )
    return jsonify(_goal_to_dict(goal)), 201


@app.route("/goals/<goal_id>", methods=["GET"])
def get_goal(goal_id: str):
    sel = _selector()
    try:
        goal = sel.get_goal(goal_id)
    except ValueError:
        return jsonify({"error": "Goal not found"}), 404
    all_goals = sel.load_goals()
    sel.score_goal(goal, all_goals)
    result = _goal_to_dict(goal)
    result["explain"] = sel.explain(goal)
    return jsonify(result)


@app.route("/goals/<goal_id>/activate", methods=["POST"])
def activate_goal(goal_id: str):
    sel = _selector()
    try:
        goal = sel.activate(goal_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(_goal_to_dict(goal))


@app.route("/goals/<goal_id>/defer", methods=["POST"])
def defer_goal(goal_id: str):
    sel = _selector()
    try:
        goal = sel.defer(goal_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(_goal_to_dict(goal))


@app.route("/goals/<goal_id>/complete", methods=["POST"])
def complete_goal(goal_id: str):
    sel = _selector()
    try:
        goal = sel.complete(goal_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(_goal_to_dict(goal))


@app.route("/goals/<goal_id>/drop", methods=["POST"])
def drop_goal(goal_id: str):
    sel = _selector()
    try:
        goal = sel.drop(goal_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(_goal_to_dict(goal))


@app.route("/goals/cycle", methods=["POST"])
def run_cycle():
    sel = _selector()
    active = sel.run_selection_cycle()
    return jsonify(
        {
            "active_count": len(active),
            "focus_budget": sel.focus_budget,
            "active_goals": [_goal_to_dict(g) for g in active],
        }
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"service": "goal-api", "status": "ok"})


# ─── Mount helper ────────────────────────────────────────────────────────────


def register(flask_app: Flask) -> None:
    """Mount goal API routes on an existing Flask app."""
    flask_app.add_url_rule("/goals", "list_goals", list_goals, methods=["GET"])
    flask_app.add_url_rule("/goals", "create_goal", create_goal, methods=["POST"])
    flask_app.add_url_rule("/goals/<goal_id>", "get_goal", get_goal, methods=["GET"])
    flask_app.add_url_rule(
        "/goals/<goal_id>/activate", "activate_goal", activate_goal, methods=["POST"]
    )
    flask_app.add_url_rule("/goals/<goal_id>/defer", "defer_goal", defer_goal, methods=["POST"])
    flask_app.add_url_rule(
        "/goals/<goal_id>/complete", "complete_goal", complete_goal, methods=["POST"]
    )
    flask_app.add_url_rule("/goals/<goal_id>/drop", "drop_goal", drop_goal, methods=["POST"])
    flask_app.add_url_rule("/goals/cycle", "run_cycle", run_cycle, methods=["POST"])
    print("[GoalAPI] routes mounted on existing Flask app")


if __name__ == "__main__":
    port = int(os.getenv("GOAL_API_PORT", "8090"))
    print(f"[GoalAPI] Starting on port {port}")
    app.run(host="0.0.0.0", port=port)
