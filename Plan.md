## Scope
- we are learning about claude agent sdk
- the focus is one idea: `stop_reason`, the reason Claude stopped talking at a given moment
- one small, runnable weather example; no real weather service needed

##  Requirements

- must use the claude-agent-sdk
- python 3
- must use lib/sdk_parser to format messaging
- just use the local python environment
- API key comes from `.env` (`ANTHROPIC_API_KEY`), or is asked for at run time if missing

## Goals
We want to show the user how stop_reason works within claude agent sdk.
We need to see stop_reason for tool_user
We need to see stop_reason for end_result
We need to see how the result is appended
I want to use a weather tool-use example
We are implementing in python
explanations should be simple enough for a laymen with little technical knowledge to be understood
We want to use lib/sdk_parser to format logging information

## Design

The run is a short conversation with two Claude replies:

| # | Who | What happens | stop_reason |
|---|-----|--------------|-------------|
| 1 | You | Ask "What's the weather like in Paris right now?" | - |
| 2 | Claude | Can't know the weather, so it asks to call `get_weather(city="Paris")` | `tool_use` |
| 3 | Tool | Our tool returns a fake report; the SDK appends it to the conversation | - |
| 4 | Claude | Reads the report and writes the final answer | `end_turn` |
| 5 | SDK | Final summary: answer, turns, cost | `end_turn` |

Pieces:
- `weather_stop_reason_demo.py` - defines the `get_weather` tool (fake data), builds the options, runs `query()`
- `lib/sdk_parser.py` - `MessageLogger` prints each message with a plain-English "What this means" and keeps a running copy of the conversation
- `.env` - holds `ANTHROPIC_API_KEY`

Decisions:
- The weather data is hard-coded so the demo is repeatable and free of outside dependencies.
- `include_partial_messages=True` is required. Without it each Claude reply reports `stop_reason = None`, because the real value only arrives in a later stream event.
- Built-in tools are turned off (`tools=[]`) so the weather tool is the only one Claude can use, which keeps the story clear.
- Only `tool_use` and `end_turn` are demonstrated; the other stop reasons are explained in the parser's lookup table.

## Steps

1. [x] Write `lib/sdk_parser.py` with `MessageLogger` (`prompt`, `show`, `show_conversation`)
2. [x] Write the `get_weather` tool and the in-process server in `weather_stop_reason_demo.py`
3. [x] Wire up options and the `query()` loop, logging every message through `MessageLogger`
4. [x] Load the API key from `.env`, with a prompt as fallback
5. [x] Write the README with a plain-English explanation
6. [x] Run it end to end in the local environment and check the output against the Acceptance checks (passed; the `°` symbol printed as `�` on the Windows console, see Risks)
7. [ ] Read the output as a beginner would and simplify any wording that is still too technical
8. [ ] Optional: add a second question that needs no tool (for example "What is 2+2?") to show a run with a single `end_turn` and no `tool_use`

## Acceptance checks
- Output shows `stop_reason = 'tool_use'` on Claude's first reply, with the tool name and input
- Output shows the tool's answer being appended, and the conversation entry count going up
- Output shows `stop_reason = 'end_turn'` on Claude's final reply and in the final summary
- "THE FULL CONVERSATION" section lists: you, claude (tool request), tool result, claude
- No stop_reason shows as `None`
- All logging goes through `lib/sdk_parser`; the demo has no `print` calls of its own for messages
- Runs with `python weather_stop_reason_demo.py` using only the local environment

## Risks
- Missing or invalid API key: the run fails at the first call. Check `.env`.
- Stop reasons showing as `None`: `include_partial_messages` was turned off.
- Claude answers without using the tool: tighten the system prompt so it uses `get_weather` for weather questions.
- Garbled `°` on Windows: the console code page can't show it. Run with `PYTHONUTF8=1`, or drop the symbol from the fake data.
- SDK message shapes change between versions: `sdk_parser` depends on them, so pin the version in `requirements.txt`.
