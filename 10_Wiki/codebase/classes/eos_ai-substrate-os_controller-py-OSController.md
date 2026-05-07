---
type: codebase-class
file: eos_ai/substrate/os_controller.py
line: 119
generated: 2026-05-07
---

# OSController

**File:** [[eos_ai-substrate-os_controller-py]] | **Line:** 119

Deep OS-level control surface.

Singleton via default().  Uses pyautogui when available, falls back
to xdotool/subprocess.  Thread-safe.

## Methods

- [[eos_ai-substrate-os_controller-py-OSController-__init__]]`() → None` — 
- [[eos_ai-substrate-os_controller-py-OSController-default]]`() → 'OSController'` — Return the process-wide singleton.
- [[eos_ai-substrate-os_controller-py-OSController-reset_default_for_tests]]`() → None` — Tear down singleton for test isolation.
- [[eos_ai-substrate-os_controller-py-OSController-execute]]`(action, payload) → OSActionResult` — Thread-safe dispatch to the appropriate handler.
- [[eos_ai-substrate-os_controller-py-OSController-_dispatch]]`(action, payload) → OSActionResult` — Route to the correct handler.  Caller holds _lock.
- [[eos_ai-substrate-os_controller-py-OSController-_do_open_app]]`(payload) → OSActionResult` — Open an application by name or path.
- [[eos_ai-substrate-os_controller-py-OSController-_do_focus_window]]`(payload) → OSActionResult` — Focus a window by title substring.
- [[eos_ai-substrate-os_controller-py-OSController-_do_list_windows]]`(payload) → OSActionResult` — List all open windows.
- [[eos_ai-substrate-os_controller-py-OSController-_do_type_text]]`(payload) → OSActionResult` — Type text at current cursor position.
- [[eos_ai-substrate-os_controller-py-OSController-_do_press_keys]]`(payload) → OSActionResult` — Press keyboard keys/shortcuts.
- [[eos_ai-substrate-os_controller-py-OSController-_do_move_mouse]]`(payload) → OSActionResult` — Move mouse to absolute coordinates.
- [[eos_ai-substrate-os_controller-py-OSController-_do_click]]`(payload) → OSActionResult` — Click at coordinates with specified button.
- [[eos_ai-substrate-os_controller-py-OSController-_do_scroll]]`(payload) → OSActionResult` — Scroll by amount (positive = up, negative = down).
- [[eos_ai-substrate-os_controller-py-OSController-_do_read_screen]]`(payload) → OSActionResult` — Take a screenshot with optional basic OCR.
- [[eos_ai-substrate-os_controller-py-OSController-_try_ocr]]`(image_path) → Optional[str]` — Best-effort OCR on a screenshot.  Returns text or None.
- [[eos_ai-substrate-os_controller-py-OSController-_do_create_file]]`(payload) → OSActionResult` — Create a file with optional content.
- [[eos_ai-substrate-os_controller-py-OSController-_do_read_file]]`(payload) → OSActionResult` — Read a file and return its content.
- [[eos_ai-substrate-os_controller-py-OSController-_do_write_file]]`(payload) → OSActionResult` — Write content to an existing or new file.
