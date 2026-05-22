"""Node mesh outcome receiver — delivers outcomes to remote nodes."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from services.umh.sockets.envelopes import OutcomeEnvelope

logger = logging.getLogger(__name__)


class NodeOutcomeReceiver:
    """Proxies OutcomeReceiver protocol to a remote node over WebSocket.

    Fire-and-forget: sends outcome notification if the node is connected,
    logs a warning if not. No queuing in Phase 1.
    """

    def __init__(self, node_id: str, ws: Any) -> None:
        self._node_id = node_id
        self._ws = ws

    @property
    def integration_id(self) -> str:
        return f"node-{self._node_id}"

    def on_outcome(self, envelope: OutcomeEnvelope) -> None:
        msg = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "outcome.notify",
                "params": {
                    "outcome_id": str(envelope.outcome_id),
                    "outcome_type": envelope.outcome_type,
                    "summary": envelope.summary,
                    "trace_id": str(envelope.trace_id),
                },
            }
        )
        try:
            loop = getattr(self._ws, "_loop", None)
            if loop is not None and loop.is_running():
                asyncio.run_coroutine_threadsafe(self._ws.send(msg), loop)
            else:
                asyncio.get_event_loop().run_until_complete(self._ws.send(msg))
        except Exception as exc:
            logger.warning("outcome delivery to node %s failed: %s", self._node_id, exc)

    def accepts_outcomes(self) -> list[str]:
        return []
