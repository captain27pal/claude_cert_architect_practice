# Claude Agent SDK – `stop_reason` Weather Demo

A small, beginner-friendly Python example that shows **why Claude stops talking**
at each step of a conversation, using the Claude Agent SDK and a pretend weather tool.

## What you'll learn

Every time Claude replies, it reports a **`stop_reason`**: the reason it stopped.
This demo shows the two most important ones:

| `stop_reason` | Plain-English meaning |
|---|---|
| `tool_use` | "I need to use a tool. I'll wait for its answer before I continue." |
| `end_turn` | "I'm finished. I've said everything I wanted to say." |

You'll also see **how the tool's answer is appended to the conversation**, which is
how Claude "learns" the weather before answering you.

## How it works (the short story)

```
 You:    "What's the weather in Paris?"
   │
   ▼
 Claude: "Let me use get_weather(city=Paris)"     stop_reason = tool_use
   │
   ▼
 Tool:   "Weather in Paris: 18°C, light rain"     (appended to the conversation)
   │
   ▼
 Claude: "It's 18°C with light rain..."          stop_reason = end_turn
```

The weather data is **made up** (see `FAKE_WEATHER` in the script), so no real
weather service or extra account is needed.

## Requirements

- Python 3.10+ (tested with Python 3.14)
- `claude-agent-sdk` (tested with 0.2.173)
- `python-dotenv`
- An Anthropic API key from the [Anthropic Console](https://console.anthropic.com/)

## Setup

1. **Activate the local virtual environment** (from this folder):

   ```bash
   # Git Bash
   source venv/Scripts/activate
   # PowerShell
   venv\Scripts\Activate.ps1
   ```

2. **Install the packages** (skip if already installed):

   ```bash
   pip install claude-agent-sdk python-dotenv
   ```

3. **Add your API key** to the `.env` file in this folder:

   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

   No quotes, no spaces. If `.env` has no key, the script will ask you to type one.

## Run it

```bash
python weather_stop_reason_demo.py
```

On Windows, if the `°` symbol causes an encoding error, run:

```bash
PYTHONIOENCODING=utf-8 python weather_stop_reason_demo.py
```

To try a different city, change `question` in `main()`. Paris, Tokyo and New York
have pretend data; any other city gets "20°C, clear skies".

## Example output (shortened)

```
STEP 3: CLAUDE replies (AssistantMessage)
  Claude asks to use a tool:
     tool name : mcp__weather__get_weather
     tool input: {"city": "Paris"}
  stop_reason = 'tool_use'
  What this means: Claude paused because it wants to use a tool...

STEP 4: TOOL RESULT is sent back to Claude (UserMessage)
  Answer for request id toolu_01...:
     Weather in Paris: 18°C, light rain
  >> Added to the conversation (now 3 entries)

STEP 5: CLAUDE replies (AssistantMessage)
  Claude says: It's 18°C (about 64°F) in Paris right now, with light rain...
  stop_reason = 'end_turn'
  What this means: Claude finished...

STEP 6: FINISHED (ResultMessage)
  stop_reason  : 'end_turn'
  turns taken  : 2
  cost (USD)   : $0.0025
```

At the end, the full conversation prints, so you can watch it grow from
1 entry to 4.

## Project files

| File | What it is |
|---|---|
| `weather_stop_reason_demo.py` | The demo: defines the weather tool and asks Claude a question |
| `lib/sdk_parser.py` | Formats every SDK message into labelled, plain-English log output |
| `lib/__init__.py` | Makes `lib` importable as a package |
| `.env` | Your API key (private, ignored by git) |
| `.gitignore` | Keeps `.env`, `venv/` and `__pycache__/` out of git |
| `Plan.md` | The project's goals and requirements |
| `anthropic_arch_free_c0de_camp.ipynb` | Scratch notebook |

## Key concepts

- **Tool**: a Python function Claude can ask to run. Here it's `get_weather`,
  created with the SDK's `@tool` decorator and served through
  `create_sdk_mcp_server`.
- **`AssistantMessage`**: something Claude said, or a tool it asked to use.
- **`UserMessage`**: what goes back to Claude. Here it carries the tool's answer.
- **`ResultMessage`**: the SDK's final summary, with the answer, the final
  `stop_reason`, the turn count and the cost.

### Why `include_partial_messages=True` is needed

The SDK hands over Claude's reply *before* it knows the `stop_reason`, so
`AssistantMessage.stop_reason` arrives as `None`. The real value comes a moment
later in a raw stream event called `message_delta`, which the SDK only sends when
`include_partial_messages=True`. `lib/sdk_parser.py` holds each reply until that
event arrives, then prints everything in a sensible order.

If you reuse `sdk_parser` in your own scripts, turn this option on.

## Using `sdk_parser` in your own code

```python
from claude_agent_sdk import ClaudeAgentOptions, query
from lib.sdk_parser import MessageLogger

options = ClaudeAgentOptions(include_partial_messages=True)

log = MessageLogger()
log.prompt("Hello!")
async for message in query(prompt="Hello!", options=options):
    log.show(message)
log.show_conversation()
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `Not logged in` | Make sure `.env` contains `ANTHROPIC_API_KEY=sk-ant-...`, or run `claude login`. |
| `stop_reason = None` | Set `include_partial_messages=True` in `ClaudeAgentOptions`. |
| `UnicodeEncodeError` with `°` | Run with `PYTHONIOENCODING=utf-8`. |
| `ModuleNotFoundError: dotenv` | Run `pip install python-dotenv` inside the venv. |

## Security

- Never share or commit `.env`. It holds your API key.
- Don't print API keys in notebooks. Saved cell outputs keep the key in the file.
  If that happens, revoke the key in the Anthropic Console and clear the outputs.
