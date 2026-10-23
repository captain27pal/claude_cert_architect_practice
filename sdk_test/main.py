import json
import os
import asyncio
from anthropic import AsyncAnthropic

client = AsyncAnthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)


# async def main() -> None:
#     message = await client.messages.create(
#         max_tokens=2048,
#         messages=[
#             {
#                 "role": "user",
#                 "content": "Hello, Claude",
#             }
#         ],
#         model="claude-sonnet-5-5",
#     )
#     print(message.content)


# asyncio.run(main())

import os
import asyncio
from anthropic import AsyncAnthropic, DefaultAioHttpClient


async def main() -> None:
    async with AsyncAnthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        http_client=DefaultAioHttpClient(),
    ) as client:
        message = await client.messages.create(
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": "Hello, Claude,why using aiohttp leads to better concurrency performance than using requests in Python? Answer in 5 bullet points.",
                }
            ],
            model="claude-sonnet-5-5",
        )
        # print(message.content)
        # print(json.dumps(message.model_dump(), indent=2))
        tool_use = next((block for block in message.content if block.type == "tool_use"), None)
        if tool_use:
            print("Tool Use Detected:")
            print(json.dumps(tool_use.model_dump(), indent=2))
        else:
            print("No tool use detected in the message content.")

asyncio.run(main())