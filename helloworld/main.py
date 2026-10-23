import asyncio
import os
import sys

from claude_agent_sdk import query, ClaudeAgentOptions

# lib/ lives one folder up, so make it importable when running from helloworld/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.sdk_parser import MessageLogger

async def main():
    prompt = "find the fix the bug in the hello_world.rb"
    log = MessageLogger()  # also writes helloworld/logs/<timestamp>.log
    log.prompt(prompt)
    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                system_prompt="You are a helpful assistant.",
                max_turns=5,
                allowed_tools=["Read", "Edit", "Write", "Bash"],  # pre-approve these tools
                include_partial_messages=True,  # needed to see stop_reason on each reply
            ),
        ):
            log.show(message)
        log.show_conversation()
    finally:
        log.close()

asyncio.run(main())
