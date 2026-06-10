"""Vision query handler — grounded visual question answering.

Every visual answer must trace to a frame, scene state, or explicit
"I don't know" with a reason. No hallucinated visual claims.

Flow:
  query → check camera state → check scene state → if needed, capture
  snapshot → if needed, call VLM → return grounded answer with confidence.
"""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def handle_visual_query(
    transcript: str,
    scene_manager: Any,
    mesh_dispatch_fn: Any = None,
    target_node: str = "beast_windows",
) -> dict[str, Any]:
    """Process a visual query and return a grounded answer.

    Returns a dict with: answer, confidence, source, frame_id, timestamp.
    """
    from substrate.workstation.camera_commands import classify_camera_command

    cmd = classify_camera_command(transcript)
    manager = scene_manager
    scene = manager.scene

    # Visual query operations that use scene state
    if cmd.operation == "visual_query":
        target = cmd.params.get("target", "")
        result = manager.query_visual(target)
        return {
            "answer": result["answer"],
            "confidence": "grounded" if result.get("status") != "not_found" else "none",
            "source": "scene_state",
            "frame_id": scene.frame_id,
            "timestamp": scene.timestamp,
            "details": result,
        }

    # "what do you see" / "what is on my desk" — needs fresh frame + VLM
    if cmd.operation == "analyze" and cmd.needs_ai:
        return _analyze_with_vlm(
            transcript=transcript,
            scene_manager=manager,
            mesh_dispatch_fn=mesh_dispatch_fn,
            target_node=target_node,
        )

    # Tracking commands
    if cmd.operation == "track_start":
        target = cmd.params.get("target", "")
        obj = manager.start_tracking(target)
        if obj:
            return {
                "answer": f"Now tracking {obj.label} (status: {obj.status}, confidence: {obj.confidence:.0%}).",
                "confidence": "grounded",
                "source": "tracking",
                "track_id": obj.track_id,
            }
        return {
            "answer": f"Could not start tracking '{target}'. I don't see it in the current scene.",
            "confidence": "none",
            "source": "tracking",
        }

    if cmd.operation == "track_stop":
        target = cmd.params.get("target", "")
        stopped = manager.stop_tracking(target)
        return {
            "answer": f"Stopped tracking {target}." if stopped else f"'{target}' was not being tracked.",
            "confidence": "grounded",
            "source": "tracking",
        }

    # Label item
    if cmd.operation == "label_item":
        label = cmd.params.get("label", "")
        obj = manager.label_item(label, frame_id=scene.frame_id)
        return {
            "answer": f"Labeled as '{obj.label}'. I'll remember this item.",
            "confidence": "operator_confirmed",
            "source": "operator_label",
            "track_id": obj.track_id,
        }

    # Watch mode
    if cmd.operation == "watch_start":
        target = cmd.params.get("target", "")
        condition = _infer_watch_condition(transcript)
        watch = manager.start_watch(target, condition=condition)
        if watch:
            return {
                "answer": f"Watching {target} for '{condition}'. Watch expires in 60 minutes.",
                "confidence": "grounded",
                "source": "watch_mode",
                "watch_id": watch.watch_id,
            }
        return {
            "answer": "Cannot start another watch — maximum active watches reached.",
            "confidence": "grounded",
            "source": "watch_mode",
        }

    if cmd.operation == "watch_stop":
        target = cmd.params.get("target", "")
        stopped = manager.stop_watch(target)
        return {
            "answer": f"Stopped watching {target}." if stopped else f"No active watch on '{target}'.",
            "confidence": "grounded",
            "source": "watch_mode",
        }

    # Follow mode
    if cmd.operation == "follow_start":
        target = cmd.params.get("target", "operator")
        follow = manager.start_follow(target)
        return {
            "answer": f"Follow mode active — keeping {target} centered.",
            "confidence": "grounded",
            "source": "follow_mode",
            "follow": follow.to_dict(),
        }

    if cmd.operation == "follow_stop":
        manager.stop_follow()
        return {
            "answer": "Follow mode stopped.",
            "confidence": "grounded",
            "source": "follow_mode",
        }

    return {
        "answer": "I'm not sure what you're asking about the camera.",
        "confidence": "none",
        "source": "fallback",
    }


def _analyze_with_vlm(
    transcript: str,
    scene_manager: Any,
    mesh_dispatch_fn: Any = None,
    target_node: str = "beast_windows",
) -> dict[str, Any]:
    """Capture a fresh frame and analyze with VLM, updating scene state."""
    scene = scene_manager.scene

    # If scene is recent (< 5s), use existing frame
    if scene.timestamp and (time.time() - scene.timestamp) < 5:
        if scene.vlm_analyzed and scene.summary:
            return {
                "answer": scene.summary,
                "confidence": "grounded",
                "source": "cached_vlm",
                "frame_id": scene.frame_id,
                "timestamp": scene.timestamp,
            }

    # Need a fresh snapshot
    if mesh_dispatch_fn is None:
        if not scene.timestamp:
            return {
                "answer": "Camera is not active. I can't see anything right now.",
                "confidence": "none",
                "source": "no_camera",
            }
        return {
            "answer": scene.summary or "I have a frame but no analysis capability right now.",
            "confidence": "low",
            "source": "stale_scene",
            "frame_id": scene.frame_id,
            "timestamp": scene.timestamp,
        }

    snapshot = mesh_dispatch_fn(target_node, "camera.snapshot", {"quality": 80})
    if not snapshot or not snapshot.get("success"):
        error = snapshot.get("error", "unknown") if snapshot else "dispatch failed"
        return {
            "answer": f"Could not capture a frame: {error}",
            "confidence": "none",
            "source": "capture_failed",
        }

    image_b64 = snapshot.get("image_base64", "")
    width = snapshot.get("width", 0)
    height = snapshot.get("height", 0)
    frame_id = f"frame_{int(time.time() * 1000)}"

    # Analyze with VLM
    from substrate.workstation.camera_commands import analyze_snapshot

    analysis = analyze_snapshot(
        image_base64=image_b64,
        transcript=transcript,
        width=width,
        height=height,
    )

    # Parse detected objects from VLM response
    detected = _extract_objects_from_vlm(analysis)

    scene_manager.update_scene_from_frame(
        frame_id=frame_id,
        preset=scene_manager.scene.preset,
        detected_objects=detected,
        summary=analysis,
        vlm_analyzed=True,
    )

    return {
        "answer": analysis,
        "confidence": "grounded",
        "source": "vlm_analysis",
        "frame_id": frame_id,
        "timestamp": time.time(),
        "detected_count": len(detected),
    }


def _extract_objects_from_vlm(analysis_text: str) -> list[dict[str, Any]]:
    """Extract detected objects from VLM analysis text.

    Best-effort extraction: looks for common workspace items mentioned
    in the analysis. This is a deterministic pass over VLM output, not
    a second LLM call.
    """
    _COMMON_OBJECTS = [
        "person", "face", "hands", "keyboard", "mouse", "phone",
        "notebook", "pen", "cup", "bottle", "headphones", "monitor",
        "laptop", "paper", "document", "camera", "tripod",
    ]

    detected: list[dict[str, Any]] = []
    text_lower = analysis_text.lower()

    for item in _COMMON_OBJECTS:
        if item in text_lower:
            detected.append({
                "label": item,
                "description": f"detected from VLM analysis",
                "confidence": 0.6,
                "source": "vision_model",
            })

    return detected


def _infer_watch_condition(transcript: str) -> str:
    """Infer what condition the operator wants to watch for."""
    lower = transcript.lower()
    if "disappear" in lower or "gone" in lower or "leave" in lower:
        return "disappeared"
    if "move" in lower:
        return "moved"
    if "appear" in lower or "show up" in lower:
        return "appeared"
    if "change" in lower:
        return "activity_changed"
    return "moved"
