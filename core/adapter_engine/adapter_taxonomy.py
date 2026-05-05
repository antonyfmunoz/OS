"""Adapter taxonomy for the UMH Adapter Engine.

Classifies adapter categories and external system types. Every
external system requires an adapter boundary. Every adapter category
has governance, proof, and optionally Tool Mastery requirements.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from enum import Enum


class AdapterCategory(str, Enum):
    TOOL = "tool"
    SAAS = "saas"
    API = "api"
    CLI = "cli"
    MCP = "mcp"
    ENVIRONMENT = "environment"
    RUNTIME = "runtime"
    MODEL = "model"
    HUMAN_APPROVAL = "human_approval"
    DATA_SOURCE = "data_source"
    FILESYSTEM = "filesystem"
    DATABASE = "database"
    BROWSER = "browser"
    COMPUTER_USE = "computer_use"
    PHYSICAL_WORLD = "physical_world"


class ExternalSystemType(str, Enum):
    GOOGLE_WORKSPACE = "google_workspace"
    GOOGLE_DRIVE = "google_drive"
    GOOGLE_DOCS = "google_docs"
    GMAIL = "gmail"
    GOOGLE_SHEETS = "google_sheets"
    GOOGLE_SLIDES = "google_slides"
    GOOGLE_CALENDAR = "google_calendar"
    CLAUDE_CODE = "claude_code"
    CODEX = "codex"
    OPENAI_API = "openai_api"
    ANTHROPIC_API = "anthropic_api"
    LOCAL_WSL = "local_wsl"
    LOCAL_WINDOWS_GUI = "local_windows_gui"
    VPS = "vps"
    TMUX = "tmux"
    SHELL = "shell"
    CHROME_BROWSER = "chrome_browser"
    FOUNDER_CONFIRMATION = "founder_confirmation"
    FILESYSTEM = "filesystem"
    DATABASE = "database"
    UNKNOWN = "unknown"


_TOOL_MASTERY_CATEGORIES = frozenset(
    {
        AdapterCategory.TOOL,
        AdapterCategory.SAAS,
        AdapterCategory.API,
        AdapterCategory.CLI,
        AdapterCategory.MCP,
        AdapterCategory.BROWSER,
        AdapterCategory.COMPUTER_USE,
    }
)


def adapter_category_requires_boundary(category: AdapterCategory) -> bool:
    return True


def external_system_requires_adapter(system_type: ExternalSystemType) -> bool:
    return True


def adapter_category_requires_tool_mastery(category: AdapterCategory) -> bool:
    return category in _TOOL_MASTERY_CATEGORIES


def adapter_category_requires_governance(category: AdapterCategory) -> bool:
    return True


def adapter_category_requires_proof(category: AdapterCategory) -> bool:
    return True


def list_all_adapter_categories() -> list[AdapterCategory]:
    return list(AdapterCategory)


def list_all_external_system_types() -> list[ExternalSystemType]:
    return list(ExternalSystemType)


def classify_external_system(system_type: ExternalSystemType) -> AdapterCategory:
    mapping: dict[ExternalSystemType, AdapterCategory] = {
        ExternalSystemType.GOOGLE_WORKSPACE: AdapterCategory.SAAS,
        ExternalSystemType.GOOGLE_DRIVE: AdapterCategory.SAAS,
        ExternalSystemType.GOOGLE_DOCS: AdapterCategory.SAAS,
        ExternalSystemType.GMAIL: AdapterCategory.SAAS,
        ExternalSystemType.GOOGLE_SHEETS: AdapterCategory.SAAS,
        ExternalSystemType.GOOGLE_SLIDES: AdapterCategory.SAAS,
        ExternalSystemType.GOOGLE_CALENDAR: AdapterCategory.SAAS,
        ExternalSystemType.CLAUDE_CODE: AdapterCategory.TOOL,
        ExternalSystemType.CODEX: AdapterCategory.TOOL,
        ExternalSystemType.OPENAI_API: AdapterCategory.MODEL,
        ExternalSystemType.ANTHROPIC_API: AdapterCategory.MODEL,
        ExternalSystemType.LOCAL_WSL: AdapterCategory.ENVIRONMENT,
        ExternalSystemType.LOCAL_WINDOWS_GUI: AdapterCategory.ENVIRONMENT,
        ExternalSystemType.VPS: AdapterCategory.ENVIRONMENT,
        ExternalSystemType.TMUX: AdapterCategory.ENVIRONMENT,
        ExternalSystemType.SHELL: AdapterCategory.CLI,
        ExternalSystemType.CHROME_BROWSER: AdapterCategory.BROWSER,
        ExternalSystemType.FOUNDER_CONFIRMATION: AdapterCategory.HUMAN_APPROVAL,
        ExternalSystemType.FILESYSTEM: AdapterCategory.FILESYSTEM,
        ExternalSystemType.DATABASE: AdapterCategory.DATABASE,
        ExternalSystemType.UNKNOWN: AdapterCategory.TOOL,
    }
    return mapping.get(system_type, AdapterCategory.TOOL)
