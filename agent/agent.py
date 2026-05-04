from __future__ import annotations

# When run directly (`python agent/agent.py`), Python only puts agent/ on
# sys.path, so `import agent.loop` fails. Add the project root so both
# `python agent/agent.py` and `python -m agent.agent` work.
if __package__ in (None, ''):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from agent.client import build_client
from agent.loop import execution_loop
from agent.tool_handler import ToolHandler
from agent.tools import calculator, file_architecture, read_file, weather

load_dotenv()

class Agent:
    def __init__(
        self,
        tools: list[dict[str, Any]],
        model_provider: str | None = None,
        model: str | None = None,
        local: bool = False
    ) -> None:

        self.client, self.model = build_client(model_provider, model, local=local)
        self.model_provider = model_provider
        self.tools = tools
        self.handler = ToolHandler()
        self.messages: list[dict] = []

        self.system_prompt = (Path(__file__).parent / 'context' / 'system_prompt.md').read_text(encoding='utf-8').strip()
        self.memory = (Path(__file__).parent / 'context' / 'memory.md').read_text(encoding='utf-8').strip()

        # Register tools with the agent
        for tool in self.tools:
            self.handler.register(tool)
        
        self.build_context()

    def build_context(self) -> None:
        self.messages.append({'role': 'system', 'content': self.system_prompt})

        if self.memory:
            self.messages.append({'role': 'system', 'content': self.memory})

    def run(self, prompt: str) -> str:
        self.messages.append({'role': 'user', 'content': prompt})
        return execution_loop(self.client, self.handler, self.messages, model=self.model)


if __name__ == '__main__':
    agent = Agent(
        tools=[
            weather.tool, 
            read_file.tool, 
            calculator.tool, 
            file_architecture.tool
        ],
        local=True
    )

    while True:
        prompt = input('> ')
        if prompt == 'exit':
            break
        agent.run(prompt)
        print()