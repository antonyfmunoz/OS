# EOS Protocol Architecture

EOS has four distinct protocol layers.
Each layer has a clear scope, owner,
and contract. Changes to one layer
do not require changes to another.

---

## Layer 0 — AI Identity (Universal)

**File:** `eos_ai/ai_identity.py`
**Scope:** Every response, everywhere, always
**Owner:** The AI itself
**Injected:** Step 0 in `cognitive_loop.py` — before everything else

These principles apply regardless of:
- Which platform (EOS, CreatorOS, LYFEOS)
- Which user or instance
- Which company or stage
- Which model is running underneath

### The 12 principles
1. World class output
2. First principles reasoning
3. Context before advice
4. Systems thinking
5. Compound intelligence
6. Human psychology depth
7. Surface what matters
8. Reality grounded
9. Honesty over comfort
10. Leverage over effort
11. Timing of knowledge
12. Nature of primitives

### Contract
Never modified per user.
Never overridden by instance context.
Non-negotiable. Always first.

---

## Layer 1 — Platform Protocols (EOS)

**Files:** `eos_ai/cognitive_loop.py`, `eos_ai/primitives.py`,
           `eos_ai/agent_hierarchy.py`, `eos_ai/reality_context.py`
**Scope:** All EOS instances
**Owner:** EOS platform
**Injected:** Steps 1a–1h in `cognitive_loop.py`

These apply to every user regardless of:
- Which OS module is active
- Which company or stage
- Which AI name the user chose

### What injects
```
1a. Semantic memory      — top-5 relevant past interactions (similarity > 0.6)
1b. Domain knowledge     — KnowledgeDomainRegistry, task-type mapped
1c. Behavioral context   — KnowledgeLayerEngine (psychology, negotiation, crisis)
1d. BIS venture context  — BusinessInstanceManager (stage, offer, ICP)
1e. Ambient reality      — SessionState ambient, RealityContext formatted
1f. Primitive context    — PrimitiveRegistry, stage-filtered
1g. AI name and persona  — get_ai_name(), identity statement
1h. Agent hierarchy      — AgentHierarchy.format_for_prompt(agent)
```

### Contract
Same structure for all users.
Content varies by user's BIS at runtime.
Never hardcoded to one instance.
All instance values loaded from database.

---

## Layer 2 — OS Module Protocols

**Files:** `eos_ai/os_registry.py` (registry), `eos_ai/trinity.py` (cross-OS intelligence)
**Scope:** Users subscribed to that OS
**Owner:** Each OS module
**Injected:** After Layer 1 step 1h, before Layer 3 (via TrinityEngine)

### EntrepreneurOS (active — v1.0)
Business primitives, CEO agents,
revenue tracking, sales workflows,
company hierarchy, BIS stage guidance

### CreatorOS (coming — v0.1)
Content calendar, audience intelligence,
brand primitives, content agents,
distribution tracking, engagement signals

### LYFEOS (coming — v0.1)
Life primitives, habit tracking,
health/energy/relationship agents,
XP system, gamification, personal growth

### Contract
Each OS module injects its context only when user is subscribed.
OS modules share the Layer 0 and 1 substrate but do not interfere
with each other. Cross-OS intelligence only activates when multiple
modules are subscribed.

---

## Layer 3 — Instance Context (Runtime)

**Source:** Neon database per `org_id`
**Scope:** One specific user instance
**Owner:** The user
**Injected:** Via BIS at runtime

This is what makes EOS personal:
- User's AI name (set during setup wizard)
- User's company name and stage
- User's offer, ICP, primary channel
- User's north star
- User's EA soul doc (generated on setup)
- User's agent soul docs
- User's historical interaction patterns

### Contract
Never hardcoded in platform files.
Always loaded from database at runtime.
Completely isolated per `org_id`.
One user's context never bleeds into another.

---

## Layer interactions

The four layers stack in order. Each response the AI produces
passes through all active layers before the LLM sees it.

```
Every response
│
├── Layer 0  AI Identity          (ai_identity.py)
│   └── 12 universal principles
│       Always. No exceptions.
│
├── Layer 1  Platform Protocols   (cognitive_loop.py)
│   └── Steps 1a–1h
│       Same structure for every user.
│       Content pulled from user's database.
│
├── Layer 2  OS Module            (per subscription)
│   └── EntrepreneurOS / CreatorOS / LYFEOS
│       Only what the user has activated.
│
└── Layer 3  Instance Context     (Neon, org_id)
    └── User's BIS, AI name, soul doc, history
        Unique to this user. Loaded at runtime.
```

**Key properties:**

- Layers are independent. Changing Layer 0 principles
  does not require touching Layer 3 instance data.

- Layers compound. Layer 0 shapes how Layer 1 context
  is interpreted. Layer 1 shapes how Layer 3 data is applied.

- Layers never leak. Layer 3 context for User A is
  invisible to User B. `org_id` isolation is enforced at
  the database level via Neon RLS.

- Layers degrade gracefully. If Layer 3 BIS is missing,
  Layer 1 still injects. If Layer 1 domain lookup fails,
  Layer 0 still applies. Every injection is wrapped in
  try/except — enhancement never blocks execution.

---

## Decision tree for builders

Before writing any code, identify which layer the change belongs to:

```
Does this apply to every AI response everywhere?
  YES → Layer 0 (ai_identity.py)

Does this apply to every EOS user regardless of instance?
  YES → Layer 1 (cognitive_loop.py or platform modules)

Does this apply only to users of a specific OS product?
  YES → Layer 2 (OS module injection)

Does this apply only to one user's specific data?
  YES → Layer 3 (loaded from Neon, never hardcoded)
```

**Common mistakes:**

| Wrong | Right |
|---|---|
| Hardcoding `"lyfe_institute"` in platform code | Load venture_id from BIS at runtime |
| Hardcoding `"DEX"` in any platform file | Use `get_ai_name(ctx)` |
| Putting stage-specific advice in cognitive_loop | Put it in BIS and let primitive engine filter |
| Modifying Layer 0 for one user's preferences | Layer 0 is non-negotiable for all users |

---

## Full injection order (cognitive_loop.py reference)

```
Step 0   ai_identity.py          — Layer 0: universal principles
Step 0a  soul doc (agent)        — Layer 3: user's EA soul doc via BIS, else hierarchy
Step 1a  semantic memory         — Layer 1: relevant past interactions
Step 1b  domain knowledge        — Layer 1: KnowledgeDomainRegistry
Step 1b2 layered domain          — Layer 1: get_layered_injection
Step 1c  behavioral context      — Layer 1: KnowledgeLayerEngine
Step 1d  BIS venture context     — Layer 3: BusinessInstanceManager
Step 1e  ambient reality         — Layer 1: RealityContext
Step 1f  primitive context       — Layer 1+3: PrimitiveRegistry (stage-filtered)
Step 1g  AI name and persona     — Layer 3: get_ai_name()
Step 1h  agent hierarchy         — Layer 1: AgentHierarchy.format_for_prompt()
Step 2   OS module context       — Layer 2: TrinityEngine.format_for_prompt()
Step 2b  cross-OS insight        — Layer 2: TrinityEngine.get_cross_os_insight() (multi-OS only)
```

---

## Isolation guarantee

Every user's data is isolated at the `org_id` level in Neon.
RLS (Row Level Security) enforces this at the database layer.
No application-level code can access another user's data
without explicitly passing a different `org_id`.

This means:
- Two users on the same VPS see different memory
- Two users see different BIS / stage / offer context
- Two users can have different AI names and soul docs
- Adding a new user is: create org in Neon, run setup wizard

---

## The harness principle

EOS is a harness. It takes any LLM and adds the four layers above.

This is why swapping the underlying model does not break the system.
The intelligence lives in the layers, not in the model.
The model is a commodity. The harness is the product.

As the layers deepen, the harness becomes less visible to the user.
The end state: the user just talks, and the system already knows
what they mean — because it knows their businesses, their patterns,
and their goals. The harness disappears into the substrate.

---

*This document is the single source of truth for the EOS protocol architecture.
Read before building. Update when the architecture changes.*
