# Actuator Backend Leverage Evaluation

## Phase 96.8AN — W0 Real Actuator Maturity Leverage Proof

## Evaluation Criteria

Each backend was evaluated against the minimum requirements for
producing a real GUI actuation proof:
1. Launch Chrome visibly on a logged-in Windows desktop
2. Focus Chrome in the foreground
3. Navigate to a safe URL (https://www.google.com)
4. Capture a screenshot of the result
5. Report window handle (HWND), PID, and title

## Backend Evaluation

### Windows Interactive Desktop Relay (PowerShell)
- **Technology**: Win32 P/Invoke via PowerShell + System.Drawing
- **Install**: Zero — already deployed and proven in Phase 96.8Q
- **WSL compatible**: No (runs on native Windows desktop)
- **Screenshot**: Yes — `System.Drawing.Graphics.CopyFromScreen`
- **Focus/HWND**: Yes — `GetForegroundWindow`, `Get-Process.MainWindowHandle`
- **Browser navigation**: Yes — `Start-Process chrome.exe --new-window <url>`
- **API surface**: Custom JSON inbox/outbox via filesystem relay
- **Security risk**: Low — explicit, scoped actions
- **Integration time**: 0 hours (already integrated)
- **Recommended**: PRIMARY BACKEND

### Playwright (CDP)
- **Technology**: Chromium DevTools Protocol
- **Install**: `pip install playwright && playwright install chromium`
- **WSL compatible**: Yes (headless browser only)
- **Screenshot**: Yes (browser viewport only, not desktop)
- **Focus/HWND**: No — browser-only, no HWND awareness
- **Browser navigation**: Yes — native, fastest and most reliable
- **Security risk**: Low — sandboxed browser context
- **Integration time**: 2 hours
- **Recommended**: Future use for browser-internal automation

### pyautogui
- **Technology**: Cross-platform mouse/keyboard/screenshot
- **Install**: `pip install pyautogui Pillow`
- **WSL compatible**: No — needs display server
- **Screenshot**: Yes (full desktop)
- **Focus/HWND**: Limited — `getWindowsWithTitle()` only, no HWND
- **Browser navigation**: Fragile — types in address bar, focus race issues
- **Security risk**: Medium — unrestricted mouse/keyboard input
- **Integration time**: 2 hours
- **Recommended**: Desktop screenshot fallback only

### Win32 APIs (pywin32/ctypes)
- **Technology**: Direct Windows API Python bindings
- **Install**: `pip install pywin32`
- **WSL compatible**: No — requires native Windows process
- **Screenshot**: Partial — needs `BitBlt`/`PrintWindow` (additional code)
- **Focus/HWND**: Yes — full `FindWindow`, `SetForegroundWindow`
- **Browser navigation**: No — can focus Chrome but cannot control page
- **Security risk**: Low — explicit, scoped API calls
- **Integration time**: 3 hours
- **Recommended**: Window management when Python preferred over PowerShell

### Windows UI Automation
- **Technology**: Microsoft accessibility framework
- **Install**: `pip install uiautomation`
- **WSL compatible**: No — COM requires native Windows session
- **Screenshot**: No
- **Focus/HWND**: Yes — HWND enumeration and PID lookup
- **Browser navigation**: Limited — fragile address bar interaction
- **Security risk**: Low — read-heavy accessibility framework
- **Integration time**: 4 hours
- **Recommended**: Non-browser desktop app inspection (future)

### UI-TARS Desktop (ByteDance)
- **Technology**: Vision-model agent with Electron wrapper
- **Install**: High — 7GB+ model download, Node, Electron
- **WSL compatible**: No — needs Windows display access
- **Screenshot**: Yes (feeds its vision model)
- **Focus/HWND**: Abstracted away — agent handles it
- **Browser navigation**: Yes — via vision, slow and non-deterministic
- **Security risk**: High — autonomous vision agent
- **Integration time**: 12+ hours
- **Recommended**: NOT RECOMMENDED for deterministic proof

## Selection Decision

**Selected: Windows Interactive Desktop Relay (PowerShell)**

### Rationale
1. Already deployed and proven in Phase 96.8Q
2. Zero integration time — no new dependencies
3. Full capability coverage (7/7): chrome_launch, window_focus,
   hwnd_observation, screenshot_capture, browser_navigation,
   foreground_detection, process_detection
4. Already has screenshot via `System.Drawing`, HWND via `Get-Process`,
   foreground detection via `GetForegroundWindow` P/Invoke
5. Runs in the founder's logged-in Windows desktop session (required
   for foreground GUI actuation)

### What the relay already provides
- `Handle-ChromeProof`: Launches Chrome, captures 3 screenshots
  (launch, focus, navigation), collects HWND, validates foreground,
  writes structured proof JSON
- `Handle-OpenApplicationUrl`: Chrome launch with dry-run support
- `Capture-Screenshot`: Full desktop screenshot via System.Drawing
- `Get-ForegroundWindowInfo`: Win32 GetForegroundWindow P/Invoke
- Filesystem JSON inbox/outbox for cross-environment communication

### What Phase 96.8AN adds on top
The maturity model classifies relay output into L0-L7 levels. The
relay does the actuating. The maturity layer does the classifying.
This is separation of concerns: the relay doesn't know about maturity
levels, and the maturity model doesn't know about PowerShell.
