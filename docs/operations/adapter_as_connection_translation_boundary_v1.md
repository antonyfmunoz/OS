# Adapter as Connection/Translation Boundary v1

**Status:** ACTIVE
**Layer:** Adapter Boundary Layer
**Scope:** Universal — corrects prior terminology ambiguity

---

## Core Doctrine

Adapters are NOT execution agents. Adapters are the universal connection and translation boundary between UMH's internal model and external reality.

### What Adapters Do

- **Connect** — establish and maintain connection to external system
- **Validate connection** — confirm the connection is live and authorized
- **Describe capabilities** — enumerate what the external system can do
- **Translate requests** — convert UMH internal contracts into external system calls
- **Validate operations** — check whether a specific operation is permitted
- **Normalize results** — convert external responses into UMH proof artifacts
- **Observe state** — monitor external system state without mutating
- **Disconnect** — cleanly release the connection

### What Adapters Do NOT Do

- Independently execute actions
- Make autonomous decisions about what to run
- Bypass governance policies
- Override mastery requirements
- Execute without worker/runtime binding

---

## Preferred Adapter Contract

```
Adapter {
  connect()
  validate_connection()
  describe_capabilities()
  translate_request()
  validate_operation()
  normalize_result()
  observe_state()
  disconnect()
}
```

---

## Legacy Terminology Correction

If existing code or documentation contains:

```
Adapter {
  connect()
  validate()
  execute()
  observe()
  disconnect()
}
```

The `execute()` method is **NOT** autonomous adapter execution. It is a governed invocation dispatched by the Execution Plane through the Action System. The adapter translates and mediates — the Execution Plane performs.

---

## Adapters Are Not Only APIs

Adapters connect and translate any external reality:

| Adapter Type | What It Mediates |
|--------------|-----------------|
| Environment Adapter | VPS, WSL, tmux, Windows GUI, Chrome |
| Model Adapter | Anthropic API, OpenAI API, Ollama |
| Data Source Adapter | Filesystem, Database, Google Drive |
| Human Approval Adapter | Founder confirmation, team approvals |
| Tool Adapter | CLI tools, MCP servers, SaaS APIs |
| Physical-World Adapter | Hardware, IoT, physical infrastructure |
| Browser Adapter | Chrome, headless browsers, Computer Use |

---

## Relationship to Execution

```
UMH Internal → Adapter (translate) → External System
                  ↑
    Execution Plane invokes adapter
    through governed Work Packet
```

The Adapter Layer is invoked BY the Execution Plane. It does not self-invoke.
