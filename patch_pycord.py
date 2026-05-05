"""
Patch py-cord's voice_client.py at build time.

Two guards applied:
1. ws.close(4000) in on_voice_server_update — self.ws can be _MissingSentinel
   when the event fires before the websocket is initialized. This is the root
   cause of the 4006 session invalidation loop.
2. poll_event() in poll_voice_ws — same _MissingSentinel crash, different path.

Uses regex to capture actual indentation from the file, avoiding
hardcoded space counts that break when py-cord indentation changes.
"""
import re
import pathlib
import sys

# Support python3.11 and python3.12 builds
for version in ('3.11', '3.12', '3.13'):
    p = pathlib.Path(
        f'/usr/local/lib/python{version}/site-packages/discord/voice_client.py'
    )
    if p.exists():
        break
else:
    print('voice_client.py not found — skipping patch')
    raise SystemExit(0)

print(f'Patching {p}')
src = p.read_text()
patched = 0

# ── Patch 1: guard self.ws.close(4000) ────────────────────────────────────────
# on_voice_server_update fires → tries await self.ws.close(4000)
# → self.ws is _MissingSentinel → crash → session invalidated → 4006
#
# Before:
#     await self.ws.close(4000)
# After:
#     if callable(getattr(self.ws, "close", None)):
#         await self.ws.close(4000)

pattern_close = r'( +)(await self\.ws\.close\(4000\))'

def _guard_close(m):
    ind  = m.group(1)
    call = m.group(2)
    return (
        f'{ind}if callable(getattr(self.ws, "close", None)):\n'
        f'{ind}    {call.strip()}'
    )

new_src, n = re.subn(pattern_close, _guard_close, src, count=1)
if n > 0:
    src = new_src
    patched += n
    print(f'Patch 1 applied: guarded ws.close(4000) ({n} site)')
else:
    print('Patch 1: ws.close(4000) pattern not found — already patched or version mismatch')

# ── Patch 2: guard poll_event() in poll_voice_ws ──────────────────────────────
# Same _MissingSentinel crash via the polling path.
#
# Before:
#     await self.ws.poll_event()
# After:
#     if not callable(getattr(self.ws, "poll_event", None)): return
#     await self.ws.poll_event()

pattern_poll = r'( +)(await self\.ws\.poll_event\(\))'

def _guard_poll(m):
    ind  = m.group(1)
    call = m.group(2)
    return (
        f'{ind}if not callable(getattr(self.ws, "poll_event", None)): return\n'
        f'{ind}{call}'
    )

new_src, n = re.subn(pattern_poll, _guard_poll, src, count=1)
if n > 0:
    src = new_src
    patched += n
    print(f'Patch 2 applied: guarded poll_event() ({n} site)')
else:
    print('Patch 2: poll_event() pattern not found — already patched or version mismatch')

# ── Patch 3: guard poll_event() in connect_websocket ──────────────────────────
# connect_websocket uses a local `ws` variable (not self.ws) in a while loop.
# If ws is _MissingSentinel, calling ws.poll_event() crashes the session.
#
# Before:
#     while ws.secret_key is None:
#         await ws.poll_event()
# After:
#     while ws.secret_key is None:
#         if not callable(getattr(ws, "poll_event", None)):
#             break
#         await ws.poll_event()

old_conn = (
    'while ws.secret_key is None:\n'
    '            await ws.poll_event()'
)
new_conn = (
    'while ws.secret_key is None:\n'
    '            if not callable(getattr(ws, "poll_event", None)):\n'
    '                break\n'
    '            await ws.poll_event()'
)
if old_conn in src and new_conn not in src:
    src = src.replace(old_conn, new_conn)
    patched += 1
    print('Patch 3 applied: guarded connect_websocket poll_event')
else:
    print('Patch 3: connect_websocket pattern not found — already patched or version mismatch')

if patched > 0:
    p.write_text(src)
    print(f'voice_client.py written — {patched} patch(es) applied')
else:
    print('No patches applied')
