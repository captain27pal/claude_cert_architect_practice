"""Weather demo: watch stop_reason change as Claude uses a tool.

What happens, in plain words:
  1. We ask Claude about the weather.
  2. Claude can't know the weather by itself, so it asks to use our
     get_weather tool and stops.            -> stop_reason = "tool_use"
  3. The SDK runs our tool and appends the answer to the conversation.
  4. Claude reads the answer and writes its reply, then stops for good.
                                            -> stop_reason = "end_turn"

Run:  python weather_stop_reason_demo.py
"""

import asyncio
import getpass
import os

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query, tool
from dotenv import load_dotenv

from lib.sdk_parser import MessageLogger

# Read ANTHROPIC_API_KEY from the .env file next to this script.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# Pretend weather data, so the demo works without a real weather service.
FAKE_WEATHER = {
    "paris": "18°C, light rain",
    "tokyo": "24°C, sunny",
    "new york": "12°C, windy",
}


@tool("get_weather", "Get the current weather for a city.", {"city": str})
async def get_weather(args):
    city = args["city"]
    report = FAKE_WEATHER.get(city.lower(), "20°C, clear skies")
    return {"content": [{"type": "text", "text": f"Weather in {city}: {report}"}]}


weather_server = create_sdk_mcp_server(name="weather", tools=[get_weather])

options = ClaudeAgentOptions(
    system_prompt="You are a helpful assistant. Use the get_weather tool for weather questions.",
    mcp_servers={"weather": weather_server},
    tools=[],  # turn off Claude Code's built-in tools so only our weather tool exists
    allowed_tools=["mcp__weather__get_weather"],  # let it run without asking permission
    max_turns=5,
    include_partial_messages=True,  # needed to see stop_reason on each Claude reply
)


def _set_env(var: str):
    """Ask for an environment variable if it isn't already set."""
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"Enter value for {var}: ")


async def main():
    _set_env("ANTHROPIC_API_KEY")  # only asks if .env didn't provide it
    question = "What's the weather like in Paris right now?"
    log = MessageLogger()
    log.prompt(question)

    async for message in query(prompt=question, options=options):
        log.show(message)

    log.show_conversation()


if __name__ == "__main__":
    asyncio.run(main())
