# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Dependencies live in the `agent` group, not the default group. Use `uv sync --group agent` to install — a plain `uv sync` will leave `openai`, `httpx`, and `pydantic` missing.

Entry point: `uv run python -m agent.agent` (or `uv run python agent/agent.py`). The README's `python -m agent` does not work — there is no `agent/__main__.py`. `agent/agent.py` adds the project root to `sys.path` at import time so both invocation forms work.

Pinned to Python 3.12 (`<3.13`) via `pyproject.toml` and `.python-version`. uv will refuse to sync on a 3.13 interpreter.

There is no test suite, linter, or build step configured.

## Architecture

### Tool location

Tools live at the **top-level `tools/` package**, not `agent/tools/` as the README claims. `agent/agent.py` imports them as `from tools.base import bash, edit, glob, grep, read, tree, write`. When adding tools, follow this layout — do not create `agent/tools/`.

### Provider abstraction

All three providers (`vllm`, `openai`, `anthropic`) talk through the **OpenAI Python SDK**. Anthropic is reached via its OpenAI-compatible shim, not the `anthropic` SDK. `agent/client.py` is the single place that knows about provider differences:

- `vllm` uses a placeholder API key (the hosted endpoint is unauthenticated) and pulls `VLLM_API_URL` / `VLLM_MODEL` from env.
- `openai` / `anthropic` require both an API key env var and a model argument; the URL env var is optional.

Note: the `Agent` class default is `provider='vllm'`, but `agent/agent.py`'s `__main__` block overrides it to `provider='anthropic', model='claude-opus-4-7'`. Changing the default behavior of `python -m agent.agent` means editing that block, not the class default.

### The streaming loop (`agent/loop.py`)

This is the load-bearing file. Two non-obvious invariants:

1. **Tool-call fragment reassembly.** In streaming mode, OpenAI emits `tool_calls` as deltas keyed by `index`. The first fragment carries `id` and `function.name`; subsequent fragments append to `function.arguments`. `call_llm_stream` accumulates these into a dict-by-index, then sorts to a list. If you change the streaming logic, preserve the index-keyed merge — concatenating fragments in arrival order will corrupt parallel tool calls.

2. **Reasoning content is printed but never persisted.** `delta.reasoning_content` (and the non-stream `message.reasoning`) are surfaced live to stdout but deliberately **not** appended to `messages`. This matches the convention for thinking-model APIs and keeps `<think>` blocks out of subsequent prompts. Don't "fix" this by adding it to history.

The loop bails at `max_iters=10` to prevent runaway tool-call cycles.

### Agent ↔ ToolHandler split

`Agent` owns the tool **registry** (`self.tools` schema list + `self.tool_functions` callable map) and message history. `ToolHandler` owns **execution only** — it reads from `agent.tool_functions` and returns `role: "tool"` messages. The handler does not register tools. Keep this split when extending: registration on `Agent`, dispatch on `ToolHandler`.

### Tool schema

A tool module exports a `tool` dict with exactly four keys: `name`, `description`, `parameters` (JSON Schema), `function` (callable). Register via `agent.add_tool(**module.tool)`. `add_tool` is idempotent by name — re-registering is a silent no-op, not an error.

### Bash tool platform handling

`tools/base/bash.py` intentionally avoids `shell=True` and resolves a real bash binary at import time. On Windows it prefers Git Bash paths and skips `System32\bash.exe` (WSL), which sees a different filesystem. `BASH_PATH` env var overrides the lookup. Don't replace this with `shell=True` — it would silently dispatch to `cmd.exe` on Windows, which doesn't understand the POSIX commands the model emits.

## Configuration

`.env` is required. `.env.example` lists all three provider blocks (`ANTHROPIC_*`, `OPENAI_*`, `VLLM_*`). Only the credentials for the provider you actually use need real values.

System prompt and persistent memory are plain markdown at `agent/context/system_prompt.md` and `agent/context/memory.md`. Both are read at `Agent.__init__` and concatenated into the initial system message — there is no runtime reload.
