# `core/` — Hopilot's Shared Kernel

This package is the **shared kernel** of the Hopilot Python backend: the small set of
types and primitives that every other layer (`controller/`, `service/`, `engine/`,
`api/`, `tools/`, `protocols/`) is allowed to depend on.

It is intentionally narrow. Adding to `core/` is a commitment — anything placed here
becomes part of the project's lingua franca.

## Constitution

A module belongs in `core/` **if and only if** it satisfies all three rules:

1. **Shared by every layer.** It is (or will plausibly be) imported by multiple
   layers — not just one. If only one feature uses it, it lives with that feature.
2. **No upward dependencies.** It must not import from `controller/`, `services/`,
   `engine/`, `api/`, `tools/`, `protocols/`, or any other higher layer. `core/`
   sits at the bottom of the dependency graph.
3. **Feature- and provider-agnostic.** No knowledge of a specific feature
   (e.g. _copilot_, _session management_) or a specific LLM provider
   (e.g. _Claude_, _Gemini_, _OpenAI_). Names that start with a feature/provider
   identifier (e.g. `CopilotRequest`, `ClaudeAdapter`) are a strong signal that the
   type does **not** belong here.

If a candidate fails any rule, it belongs in its owning feature/layer instead.
A type can always be **promoted** into `core/` later, once a second layer starts
depending on it.

## What lives here today

| Module           | Role                                                                                                                              |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `models.py`      | Shared domain vocabulary — `HOSession`, `HOMessage`, `HOreAct`, `HOChunk`, `Payload` variants. The data types every layer speaks. |
| `event_bus.py`   | Type-keyed async pub/sub. 1:N fire-and-forget. Dispatches by event _class_.                                                       |
| `request_bus.py` | Type-keyed async mediator. 1:1 request/response. MediatR-style; a natural seam for future CQRS.                                   |
| `channel.py`     | Transport-agnostic duplex stream abstraction over an injected send/receive pair (used by the WebSocket controller).               |

## What does NOT belong here

- Feature DTOs (`CopilotRequest`, `SessionCreateCommand`, …) → live next to the
  feature that owns them (`services/`, `protocols/`, `controller/handlers/`).
- Provider adapters or SDK-specific message shapes → `api/provider/`.
- Application orchestration, ReAct loops, tool execution → `engine/`, `services/`.
- Anything that imports from a higher layer.

## When in doubt

Default to **not** putting it in `core/`. Promotion is cheap; demotion is painful
(every importer has to change). Wait until at least two unrelated layers
genuinely need the type, then move it here in a focused commit.
