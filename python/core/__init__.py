"""
core/ — Hopilot's shared kernel.

Modules here MUST satisfy all three rules:
  1. Depended on by every layer (controller / service / engine / api / tools).
  2. No upward dependencies (never imports from services, engines, controllers, etc.).
  3. Not specific to any single feature or provider (e.g. copilot, claude, gemini).

See README.md in this directory for the full constitution.
"""
