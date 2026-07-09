"""Socket registration — wires concrete adapters into substrate ports.

Called once at startup by service entry points (discord_bot, operator, etc.)
to register all adapter implementations into substrate/sockets/ ports.
This is the ONLY file that bridges adapters → substrate/sockets/.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_all_sockets() -> None:
    """Register all adapter implementations into substrate socket ports."""
    _register_intelligence()
    _register_data_sources()
    _register_browser()
    _register_remote_exec()
    _register_tool_adapters()
    logger.info("[SocketRegistration] All adapter sockets registered")


def _register_intelligence() -> None:
    """Wire model_router, agent_runtime, CLI adapters into intelligence_port."""
    try:
        from substrate.sockets.intelligence_port import (
            register_agent_runtime,
            register_cli_adapter,
            register_model_router,
        )

        from adapters.models.model_router import (
            MODEL_REGISTRY,
            ROLE_SLOTS,
            call_with_fallback,
            get_router,
            refresh_provider_health,
        )
        from adapters.models.model_router import _ollama_available

        register_model_router(
            get_router=get_router,
            call_with_fallback=call_with_fallback,
            model_registry=MODEL_REGISTRY,
            refresh_provider_health=refresh_provider_health,
            role_slots=ROLE_SLOTS,
            ollama_available=_ollama_available,
        )

        # agent_runtime.py exports only the AgentRuntime class (no module-level
        # get_agent_runtime accessor); importing a non-existent name aborted the
        # whole intelligence registration mid-way. register_agent_runtime's
        # get_agent_runtime is optional, so pass the class alone.
        from adapters.models.agent_runtime import AgentRuntime
        register_agent_runtime(
            agent_runtime_cls=AgentRuntime,
        )

        try:
            from adapters.models.cc_sdk import is_available as cc_available
            from adapters.models.cc_sdk import query_cc_sync
            try:
                from adapters.models.cc_sdk import _get_subprocess_env
            except ImportError:
                _get_subprocess_env = None
            extra = {}
            if _get_subprocess_env is not None:
                extra["get_subprocess_env"] = _get_subprocess_env
            register_cli_adapter("cc_sdk", query_fn=query_cc_sync, is_available_fn=cc_available, **extra)
        except ImportError:
            pass

        try:
            from adapters.models.codex_cli import is_available as codex_available
            from adapters.models.codex_cli import query_codex_sync, review_codex_sync
            register_cli_adapter(
                "codex", query_fn=query_codex_sync,
                is_available_fn=codex_available,
                review_fn=review_codex_sync,
            )
        except ImportError:
            pass

        try:
            from adapters.models.hermes_cli import is_available as hermes_available
            from adapters.models.hermes_cli import query_hermes_sync
            register_cli_adapter("hermes", query_fn=query_hermes_sync, is_available_fn=hermes_available)
        except ImportError:
            pass

        try:
            from adapters.models.opencode_cli import is_available as opencode_available
            from adapters.models.opencode_cli import query_opencode_sync
            register_cli_adapter("opencode", query_fn=query_opencode_sync, is_available_fn=opencode_available)
        except ImportError:
            pass

        try:
            from adapters.models.llm_adapter import LLMAdapter
            from substrate.sockets.intelligence_port import register_llm_adapter
            register_llm_adapter(LLMAdapter)
        except ImportError:
            pass

        try:
            from adapters.models.routing.config import RoutingConfig, load_routing_config
            from substrate.sockets.intelligence_port import register_routing_config
            register_routing_config(load_routing_config)
        except ImportError:
            pass

    except Exception as e:
        logger.warning("[SocketRegistration] Intelligence registration failed: %s", e)


def _register_data_sources() -> None:
    """Wire Notion, GWS, NotebookLM, Calendar into data_source_port."""
    try:
        from substrate.sockets.data_source_port import (
            register_calendar,
            register_google_workspace,
            register_notebooklm,
            register_notion,
        )

        try:
            from adapters.notion.integration.auth import get_notion_client
            from adapters.notion.notion_publisher import get_publisher
            register_notion(get_client=get_notion_client, get_publisher=get_publisher)
        except ImportError:
            pass

        try:
            from adapters.google_workspace.email_gps import EmailGPS
            from adapters.google_workspace.gws_connector import GWSConnector
            from adapters.google_workspace.gws_scanner import GWSDocumentScanner
            register_google_workspace(
                connector_cls=GWSConnector,
                email_gps_cls=EmailGPS,
                scanner_cls=GWSDocumentScanner,
            )
        except ImportError:
            pass

        try:
            from adapters.notebooklm.notebooklm_sync import NotebookLMSync
            register_notebooklm(sync_cls=NotebookLMSync)
        except ImportError:
            pass

        try:
            from adapters.calendar.meetings import (
                draft_meeting_minutes,
                get_open_loop_meetings,
            )
            register_calendar(
                get_open_loop_meetings=get_open_loop_meetings,
                draft_meeting_minutes=draft_meeting_minutes,
            )
        except ImportError:
            pass

    except Exception as e:
        logger.warning("[SocketRegistration] Data source registration failed: %s", e)


def _register_browser() -> None:
    """Wire Scrapling into browser_port."""
    try:
        from substrate.sockets.browser_port import register_scrapling

        from adapters.scrapling.scrapling_connector import ScraplingConnector
        register_scrapling(connector_cls=ScraplingConnector)
    except ImportError:
        pass
    except Exception as e:
        logger.warning("[SocketRegistration] Browser registration failed: %s", e)


def _register_remote_exec() -> None:
    """Wire SSH into remote_exec_port."""
    try:
        from substrate.sockets.remote_exec_port import register_ssh

        from adapters.ssh.ssh_utils import scp_to, ssh_reachable, ssh_run
        register_ssh(ssh_run=ssh_run, ssh_reachable=ssh_reachable, scp_to=scp_to)
    except ImportError:
        pass
    except Exception as e:
        logger.warning("[SocketRegistration] Remote exec registration failed: %s", e)


def _register_tool_adapters() -> None:
    """Wire tool adapters into tool_adapter_port."""
    try:
        from substrate.sockets.tool_adapter_port import register_tool_adapter

        from adapters.tool_adapters import (
            FilesystemAdapter,
            GitAdapter,
            ShellAdapter,
            TmuxAdapter,
        )
        register_tool_adapter("tmux", TmuxAdapter)
        register_tool_adapter("shell", ShellAdapter)
        register_tool_adapter("git", GitAdapter)
        register_tool_adapter("filesystem", FilesystemAdapter)
    except ImportError:
        pass
    except Exception as e:
        logger.warning("[SocketRegistration] Tool adapter registration failed: %s", e)
