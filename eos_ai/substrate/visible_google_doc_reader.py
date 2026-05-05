"""
Visible Google Doc reader for W0-001R computer-use fallback test.

Reads a Google Doc through the visible Chrome UI using only:
- Windows UI Automation / accessibility tree
- Mouse / keyboard / scrolling
- Task Scheduler /IT for interactive session execution

No API. No Playwright. No CDP. No credential access.
This is the worst-case fallback for document content reading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DocReadMethod(Enum):
    ACCESSIBILITY_TREE = "accessibility_tree"
    KEYBOARD_SELECT_ALL = "keyboard_select_all"
    SCROLL_AND_READ = "scroll_and_read"


class DocReadStatus(Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    NOT_ATTEMPTED = "not_attempted"


@dataclass
class DocTabCURead:
    tab_title: str
    tab_index: int
    word_count: int = 0
    char_count: int = 0
    text_content: str = ""
    status: DocReadStatus = DocReadStatus.NOT_ATTEMPTED
    scroll_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tab_title": self.tab_title,
            "tab_index": self.tab_index,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "status": self.status.value,
            "scroll_count": self.scroll_count,
        }


@dataclass
class DocCUReadResult:
    file_id: str
    title: str
    method: DocReadMethod
    total_tabs_detected: int = 0
    total_tabs_read: int = 0
    total_words: int = 0
    total_chars: int = 0
    status: DocReadStatus = DocReadStatus.NOT_ATTEMPTED
    tabs_read: list[DocTabCURead] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "title": self.title,
            "method": self.method.value,
            "total_tabs_detected": self.total_tabs_detected,
            "total_tabs_read": self.total_tabs_read,
            "total_words": self.total_words,
            "total_chars": self.total_chars,
            "status": self.status.value,
            "tabs_read": [t.to_dict() for t in self.tabs_read],
        }


DOC_CHROME_URL_PATTERN = re.compile(
    r"https://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)"
)

BLOCKED_DOC_ACTIONS: frozenset[str] = frozenset(
    {
        "edit_document",
        "delete_document",
        "share_document",
        "download_document",
        "print_document",
        "change_permissions",
        "switch_account",
        "open_gmail",
    }
)


def validate_doc_read_scope(url: str) -> list[str]:
    """Validate that the URL is a Google Doc and scope is read-only."""
    errors: list[str] = []
    if not DOC_CHROME_URL_PATTERN.search(url):
        errors.append(f"URL does not appear to be a Google Doc: {url}")
    lower_url = url.lower()
    if "gmail" in lower_url or "mail.google" in lower_url:
        errors.append("Gmail access is blocked")
    return errors


def build_doc_open_command(
    file_id: str,
    chrome_path: str = r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    profile_directory: str = "Profile 5",
) -> str:
    """Build Chrome command to open a specific Google Doc."""
    url = f"https://docs.google.com/document/d/{file_id}/edit"
    return (
        f'"{chrome_path}" '
        f'--profile-directory="{profile_directory}" '
        f'--force-renderer-accessibility '
        f'"{url}"'
    )


def build_doc_tab_detection_script() -> str:
    """Build PowerShell script to detect document tabs in Chrome.

    Google Docs tabs appear as tab strip elements in the accessibility tree.
    Tab names are accessible as button/tab controls.
    """
    return r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$auto = [System.Windows.Automation.AutomationElement]
$root = $auto::RootElement

# Find Chrome window with Google Docs
$chromeCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ClassNameProperty, "Chrome_WidgetWin_1")
$chromeWindows = $root.FindAll(
    [System.Windows.Automation.TreeScope]::Children, $chromeCondition)

$docWindow = $null
foreach ($win in $chromeWindows) {
    if ($win.Current.Name -match "Google Docs") {
        $docWindow = $win
        break
    }
}

if (-not $docWindow) {
    Write-Output "ERROR: No Google Docs window found"
    exit 1
}

Write-Output "WINDOW: $($docWindow.Current.Name)"

# Find tab strip elements (document tabs)
$tabCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::TabItem)
$tabs = $docWindow.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants, $tabCondition)

Write-Output "TAB_COUNT: $($tabs.Count)"
foreach ($tab in $tabs) {
    Write-Output "TAB: $($tab.Current.Name)"
}

# Find document content area
$docCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Document)
$docs = $docWindow.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants, $docCondition)

Write-Output "DOC_ELEMENTS: $($docs.Count)"
foreach ($doc in $docs) {
    $name = $doc.Current.Name
    if ($name.Length -gt 200) { $name = $name.Substring(0, 200) + "..." }
    Write-Output "DOC_CONTENT: $name"
}
"""


def build_doc_scroll_read_script(max_scrolls: int = 20) -> str:
    """Build PowerShell script to scroll through doc and read content."""
    return f"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms

$auto = [System.Windows.Automation.AutomationElement]
$root = $auto::RootElement

# Find Chrome/Docs window
$chromeCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ClassNameProperty, "Chrome_WidgetWin_1")
$chromeWindows = $root.FindAll(
    [System.Windows.Automation.TreeScope]::Children, $chromeCondition)

$docWindow = $null
foreach ($win in $chromeWindows) {{
    if ($win.Current.Name -match "Google Docs|document") {{
        $docWindow = $win
        break
    }}
}}

if (-not $docWindow) {{
    Write-Output "ERROR: No document window found"
    exit 1
}}

Write-Output "WINDOW: $($docWindow.Current.Name)"

# Read initial text content from accessibility tree
$textCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Text)
$textElements = $docWindow.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants, $textCondition)

Write-Output "INITIAL_TEXT_ELEMENTS: $($textElements.Count)"

$allText = @()
foreach ($elem in $textElements) {{
    $name = $elem.Current.Name
    if ($name -and $name.Trim()) {{
        $allText += $name
    }}
}}

Write-Output "INITIAL_WORD_COUNT: $(($allText -join ' ').Split().Count)"

# Scroll and accumulate
$scrollCount = 0
$prevCount = $allText.Count

for ($i = 0; $i -lt {max_scrolls}; $i++) {{
    [System.Windows.Forms.SendKeys]::SendWait("{{PGDN}}")
    Start-Sleep -Milliseconds 1500

    $textElements = $docWindow.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants, $textCondition)

    $newTexts = @()
    foreach ($elem in $textElements) {{
        $name = $elem.Current.Name
        if ($name -and $name.Trim() -and $allText -notcontains $name) {{
            $newTexts += $name
        }}
    }}

    $allText += $newTexts
    $scrollCount++

    if ($newTexts.Count -eq 0) {{
        Write-Output "SCROLL_$($scrollCount): 0 new elements (end of content)"
        break
    }} else {{
        Write-Output "SCROLL_$($scrollCount): $($newTexts.Count) new elements"
    }}
}}

Write-Output "TOTAL_SCROLLS: $scrollCount"
Write-Output "TOTAL_TEXT_ELEMENTS: $($allText.Count)"
Write-Output "TOTAL_WORD_COUNT: $(($allText -join ' ').Split().Count)"
Write-Output "---CONTENT_START---"
$allText -join "`n"
Write-Output "---CONTENT_END---"
"""


def parse_doc_cu_output(raw_output: str) -> DocCUReadResult:
    """Parse the PowerShell output from a CU doc read."""
    lines = raw_output.strip().split("\n")

    title = ""
    tab_count = 0
    word_count = 0
    text_content = ""
    scroll_count = 0
    in_content = False
    content_lines: list[str] = []

    for line in lines:
        line = line.strip()
        if line.startswith("WINDOW:"):
            title = line[7:].strip()
        elif line.startswith("TAB_COUNT:"):
            tab_count = int(line[10:].strip())
        elif line.startswith("TOTAL_WORD_COUNT:"):
            word_count = int(line[17:].strip())
        elif line.startswith("TOTAL_SCROLLS:"):
            scroll_count = int(line[14:].strip())
        elif line == "---CONTENT_START---":
            in_content = True
        elif line == "---CONTENT_END---":
            in_content = False
        elif in_content:
            content_lines.append(line)

    text_content = "\n".join(content_lines)
    actual_words = len(text_content.split()) if text_content.strip() else 0

    result = DocCUReadResult(
        file_id="",
        title=title,
        method=DocReadMethod.SCROLL_AND_READ,
        total_tabs_detected=tab_count,
        total_tabs_read=1,
        total_words=actual_words or word_count,
        total_chars=len(text_content),
        status=DocReadStatus.COMPLETE if actual_words > 0 else DocReadStatus.PARTIAL,
    )

    if text_content.strip():
        result.tabs_read.append(DocTabCURead(
            tab_title="Main",
            tab_index=0,
            word_count=actual_words,
            char_count=len(text_content),
            text_content=text_content,
            status=DocReadStatus.COMPLETE,
            scroll_count=scroll_count,
        ))

    return result


def build_cu_vs_api_coverage(
    cu_word_count: int,
    api_word_count: int,
    cu_tabs_read: int,
    api_total_tabs: int,
) -> dict[str, Any]:
    """Build coverage comparison between CU and API extraction."""
    word_recall = round(cu_word_count / api_word_count, 3) if api_word_count > 0 else 0.0
    tab_coverage = round(cu_tabs_read / api_total_tabs, 3) if api_total_tabs > 0 else 0.0

    if word_recall >= 0.9:
        confidence = "HIGH"
    elif word_recall >= 0.5:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return {
        "cu_word_count": cu_word_count,
        "api_word_count": api_word_count,
        "word_recall": word_recall,
        "cu_tabs_read": cu_tabs_read,
        "api_total_tabs": api_total_tabs,
        "tab_coverage": tab_coverage,
        "confidence": confidence,
    }
