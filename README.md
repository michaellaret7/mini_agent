<div align="center">

# mini-agent

**The simplest, most obvious form of an agent — built from first principles.**

[![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/uv-managed-DE5FE9)](https://github.com/astral-sh/uv)

</div>

---

## What this is

An agent, stripped to the parts that actually make it an agent — and nothing else. No framework, no orchestration layer, no abstractions you have to learn before you can read the code.

If you've ever wanted to see how an LLM agent really works under the hood, this is meant to be the answer. Two short files do the entire job:

- `agent/loop.py` — call the model, run any tools it asks for, append the results, call again. That's the loop.
- `agent/agent.py` — wire up a client, a system prompt, a tool registry, and message history.

Everything else (tools, provider switching, streaming) is straightforward code you can read top-to-bottom in a sitting.

## The whole idea, in plain English

An agent is just:

1. Send the conversation to an LLM, along with a list of tools it's allowed to call.
2. If the model replies with tool calls, run those tools locally and append the results to the conversation.
3. Loop until the model replies without asking for tools — that's the final answer.

That's it. The rest is plumbing.

## Requirements

- Python 3.12
- [`uv`](https://github.com/astral-sh/uv) for dependency management
- An [OpenRouter](https://openrouter.ai) API key (or a hosted vLLM endpoint)

## Setup

```bash
# 1. Install dependencies (note: --group agent, not a plain sync)
uv sync --group agent

# 2. Add credentials
cp .env.example .env
# edit .env — only the provider you actually use needs real values
```

## Running

```bash
uv run python main.py
```

You'll get a `>` prompt. Try:

```
> what files are in this repo?
> read agent/loop.py and explain how it works
> create a file hello.txt that says "hi"
```

Type `exit` to quit.

By default `main.py` runs with `anthropic/claude-opus-4-7` via OpenRouter. To switch models, edit the `Agent(...)` call in `main.py` — anything OpenRouter exposes will work.

## Project layout

```
mini_agent/
├── main.py                 # REPL entry point
├── agent/
│   ├── agent.py            # Agent class — owns messages + tool registry
│   ├── loop.py             # The loop. Streaming + tool-call reassembly.
│   ├── client.py           # Build an OpenAI-compatible client for any provider
│   ├── tool_handler.py     # Dispatch parsed tool calls to Python functions
│   └── context/
│       ├── system_prompt.md
│       └── memory.md
├── tools/
│   └── base/               # bash, read, write, edit, glob, grep, tree, search
└── pyproject.toml
```

## The loop

`agent/loop.py` is the heart of the agent. In pseudocode:

```
loop:
    content, tool_calls = call_model(messages, tools)
    append assistant turn to messages
    if no tool_calls:
        return content
    for each tool_call:
        run the tool, append the result as a 'tool' message
```

Two details worth knowing if you want to extend it:

- **Streaming reassembly.** When streaming, the OpenAI protocol delivers tool calls as fragments keyed by `index` — the first fragment carries the function name, later fragments dribble in the JSON arguments. The loop merges them by index so parallel tool calls don't get scrambled.
- **Reasoning passthrough.** For thinking models, `reasoning_content` is printed live to the screen but deliberately *not* appended to message history. The model's "thoughts" are for your eyes, not for the next prompt.

## Providers

`agent/client.py` builds an OpenAI-compatible client for two backends. Both speak the same wire format, so the loop doesn't know or care which one is in use:

| Provider     | How it's reached                                                              |
|--------------|-------------------------------------------------------------------------------|
| `openrouter` | OpenRouter — one API key, every frontier model (Anthropic, OpenAI, DeepSeek…) |
| `vllm`       | Any self-hosted or proxied vLLM server (e.g. RunPod)                          |

Pick one in code: `Agent(provider='openrouter', model='openai/gpt-5')`.

## Tools

A tool is a dict with four keys: a name, a description, a JSON Schema for its parameters, and the Python function to call. Drop a new file in `tools/base/`:

```python
# tools/base/echo.py
def echo(text: str) -> str:
    return text

tool = {
    'name': 'Echo',
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
from tools.base import echo
agent.add_tool(**echo.tool)
```

The schema goes to the model on the next request; when the model calls `Echo(text="hi")`, `ToolHandler` looks up `echo` in the registry, runs it, and feeds the return value back as a `role: "tool"` message.

### Built-in tools

| Tool        | Purpose                                              |
|-------------|------------------------------------------------------|
| `Bash`      | Run a shell command (real bash, Git Bash on Windows) |
| `ReadFile`  | Read a file with line numbers                        |
| `Write`     | Write a file                                         |
| `Edit`      | Edit a file in place                                 |
| `Glob`      | Find files by pattern                                |
| `Grep`      | Search file contents                                 |
| `Tree`      | Show a directory tree                                |
| `WebSearch` | Web search via Parallel Search API                   |

## License

MIT.
