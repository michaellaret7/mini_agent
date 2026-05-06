<div align="center">


# local-agent

**A streaming, tool-calling agent client that talks to any OpenAI-compatible endpoint.**

[![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/uv-managed-DE5FE9)](https://github.com/astral-sh/uv)

</div>

---

## What this is

A minimal agent loop. It streams tokens from a chat-completions endpoint, parses tool calls, executes them, and feeds the results back — until the model stops asking for tools and returns a final answer.

The client supports three backends:

- A hosted vLLM endpoint (e.g. RunPod proxy) — original target was NVIDIA Nemotron 3 Nano on vLLM.
- OpenAI's API.
- Anthropic's API (via an OpenAI-compatible shim).

## Features

- **Streaming token-by-token output** with live reasoning passthrough (the `<think>...</think>` blocks thinking models emit).
- **Tool calling** in the standard OpenAI tool-call format, with fragment reassembly across stream chunks.
- **Built-in tools** — bash, read/write/edit, glob, grep, and a `tree` view of the filesystem.

## Requirements

- Python 3.12
- [`uv`](https://github.com/astral-sh/uv) for dependency management
- An endpoint to talk to — Anthropic, OpenAI, or a hosted vLLM endpoint

## Setup

```bash
# 1. Install dependencies
uv sync --group agent

# 2. Configure provider credentials
cp .env.example .env
# then edit .env — see "Configuring the endpoint" below
```

## Running

```bash
uv run python -m agent
```

You'll get a `>` prompt. Try:

```
> what's 2 ** 16 plus the number of files in agent/tools?
> what's the weather in new york right now?
> read agent/loop.py and explain how tool calls are reassembled across stream chunks
```

Type `exit` to quit.

## Configuring the endpoint

`agent/client.py` builds the OpenAI-compatible client. Three modes:

**Hosted vLLM (default)** — `Agent(tools=[...])` or `Agent(tools=[...], provider='vllm')`. The client reads `VLLM_API_URL` and `VLLM_MODEL` from `.env`. Point `VLLM_API_URL` at your RunPod (or other) endpoint.

**OpenAI / Anthropic** — pass `provider='openai'` (or `'anthropic'`) and a `model` name. The client reads `OPENAI_API_KEY` / `OPENAI_API_URL` (or the `ANTHROPIC_*` equivalents) from `.env`.

## Project layout

```
local-agent/
├── agent/
│   ├── __main__.py         # REPL entry point (uv run python -m agent)
│   ├── agent.py            # Agent class, message history, context wiring
│   ├── client.py           # OpenAI-compatible client builder (vllm / openai / anthropic)
│   ├── loop.py             # streaming execution loop, tool-call reassembly
│   ├── tool_handler.py     # tool registry + dispatch
│   ├── context/
│   │   ├── system_prompt.md
│   │   └── memory.md
│   └── tools/              # individual tools (one file each)
│       └── base/           # bash, read, write, edit, glob, grep, tree
└── pyproject.toml
```

## How the loop works

`agent/loop.py` is the interesting part. The model's response can interleave plain text, reasoning, and tool-call fragments — the latter arrive in pieces keyed by index, with the function name on the first fragment and arguments dribbling in across many subsequent chunks. The loop:

1. Streams a completion, printing content live.
2. Reassembles fragmented `tool_calls` into complete dicts.
3. If there are tool calls, executes each one through `ToolHandler.execute()` and appends the results as `role: "tool"` messages.
4. Repeats until the model returns a turn with no tool calls — that's the final answer.
5. Bails out at `max_iters=10` to avoid runaway loops.

Reasoning content is printed live but **not** appended to history, matching the convention for thinking models.

## Adding a tool

A tool is just a dict with four keys. Drop a file in `agent/tools/` like:

```python
# agent/tools/echo.py
def echo(text: str) -> str:
    return text

tool = {
    'name': 'echo',
    'description': 'Echo a string back unchanged.',
    'parameters': {
        'type': 'object',
        'properties': {
            'text': {'type': 'string', 'description': 'String to echo.'},
        },
        'required': ['text'],
    },
    'function': echo,
}
```

Then register it on the agent:

```python
from agent.tools import echo
agent = Agent()
agent.add_tool(**echo.tool)
```

The schema goes to the model on the next request, and `ToolHandler` dispatches to your `function` when the model calls it.

## License

MIT (or whatever you prefer — add a `LICENSE` file).

## Acknowledgements

- [wttr.in](https://wttr.in) for the weather endpoint
