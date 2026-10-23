"""sdk_parser - turns Claude Agent SDK messages into plain-English log output.

The SDK hands you a stream of message objects. This module prints each one
with a label, a short "what this means" explanation, and - most importantly -
the stop_reason, which tells you WHY Claude stopped talking at that moment.

It also keeps a running copy of the conversation so you can see how each
tool result gets appended before Claude continues.

Usage (set include_partial_messages=True in ClaudeAgentOptions, otherwise
each Claude reply's stop_reason shows as None):
    from lib.sdk_parser import MessageLogger

    log = MessageLogger()
    log.prompt("What's the weather in Paris?")
    async for message in query(prompt=..., options=...):
        log.show(message)
    log.show_conversation()
"""

import json
import os
import sys
from datetime import datetime
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

LINE = "=" * 70
THIN = "-" * 70

# Plain-English meaning of every stop_reason Claude can give.
STOP_REASON_MEANING = {
    "tool_use": (
        "Claude paused because it wants to use a tool. It is waiting for the "
        "tool's answer before it can continue."
    ),
    "end_turn": (
        "Claude finished. It has said everything it wanted to say and is not "
        "waiting for anything."
    ),
    "max_tokens": "Claude was cut off because it hit the length limit.",
    "stop_sequence": "Claude stopped because it produced a special 'stop' word.",
    "pause_turn": "Claude paused a long-running step and will pick it up again.",
    "refusal": "Claude declined to answer this request.",
}


def explain_stop_reason(stop_reason: str | None) -> str:
    if stop_reason is None:
        return "(no stop_reason reported for this message)"
    return STOP_REASON_MEANING.get(stop_reason, "An uncommon stop reason.")


def _pretty(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2)
    return str(value)


def _tool_result_text(content: Any) -> str:
    """Tool results can be a plain string or a list of content pieces."""
    if isinstance(content, list):
        return "\n".join(
            piece.get("text", _pretty(piece)) if isinstance(piece, dict) else str(piece)
            for piece in content
        )
    return _pretty(content)


def _project_dir() -> str:
    """Folder of the script being run (e.g. hello_world/ for hello_world/main.py)."""
    main_file = getattr(sys.modules.get("__main__"), "__file__", None)
    return os.path.dirname(os.path.abspath(main_file)) if main_file else os.getcwd()


class MessageLogger:
    """Prints SDK messages step by step and remembers the conversation.

    Everything printed is also written to <project>/logs/<timestamp>.log,
    where <project> is the folder of the script you ran. Each MessageLogger
    (so each run) gets its own new file, e.g. logs/2026-10-23_14-05-33.log.
    Pass log_dir to choose another folder, or write_log=False to turn it off.
    """

    def __init__(self, log_dir: str | None = None, write_log: bool = True) -> None:
        self.log_path: str | None = None
        self._log_file = None
        if write_log:
            folder = log_dir or os.path.join(_project_dir(), "logs")
            os.makedirs(folder, exist_ok=True)
            stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.log_path = os.path.join(folder, f"{stamp}.log")
            # "x" = never overwrite; a second run in the same second fails loudly.
            self._log_file = open(self.log_path, "x", encoding="utf-8")
            print(f"(logging this run to {self.log_path})")
        self.step = 0
        # Our own simple record of the conversation, in the order it grows.
        self.conversation: list[tuple[str, str]] = []
        self._streaming = False  # True once we see raw stream events
        self._waiting: list[Any] = []  # messages held until stop_reason arrives

    # ---- helpers -------------------------------------------------------

    def _print(self, text: str = "") -> None:
        """Show text on screen and copy it to the log file."""
        print(text)
        if self._log_file:
            self._log_file.write(text + "\n")
            self._log_file.flush()  # keep the log useful even if the run crashes

    def close(self) -> None:
        if self._log_file:
            self._log_file.close()
            self._log_file = None

    def _header(self, title: str) -> None:
        self.step += 1
        self._print(f"\n{LINE}\nSTEP {self.step}: {title}\n{LINE}")

    def _explain(self, text: str) -> None:
        self._print(f"  What this means: {text}")

    def _append(self, who: str, what: str) -> None:
        self.conversation.append((who, what))
        self._print(f"  >> Added to the conversation (now {len(self.conversation)} entries): "
              f"[{who}] {what.splitlines()[0][:60]}")

    # ---- public API ----------------------------------------------------

    def prompt(self, text: str) -> None:
        """Log the question we are sending to Claude."""
        self._header("YOU ask Claude a question")
        self._print(f"  Question: {text}")
        self._append("you", text)

    def show(self, message: Any) -> None:
        """Log any message that comes out of the SDK.

        Why the waiting list: the SDK hands us Claude's reply BEFORE Claude's
        stop_reason is known (AssistantMessage.stop_reason is None). The real
        stop_reason arrives a moment later in a raw "message_delta" stream
        event (needs include_partial_messages=True). So we hold the reply,
        and anything after it, until that event shows up - then print them
        in a sensible order.
        """
        if isinstance(message, StreamEvent):
            self._on_stream_event(message.event)
            return
        if self._waiting or (
            isinstance(message, AssistantMessage)
            and message.stop_reason is None
            and self._streaming
        ):
            self._waiting.append(message)
            return
        if isinstance(message, ResultMessage):
            self._flush(None)
        self._dispatch(message)

    def _on_stream_event(self, event: dict[str, Any]) -> None:
        if event.get("type") == "message_start":
            self._streaming = True
        elif event.get("type") == "message_delta":
            self._flush(event.get("delta", {}).get("stop_reason"))

    def _flush(self, stop_reason: str | None) -> None:
        waiting, self._waiting = self._waiting, []
        for message in waiting:
            if isinstance(message, AssistantMessage) and stop_reason is not None:
                message.stop_reason = stop_reason
            self._dispatch(message)

    def _dispatch(self, message: Any) -> None:
        if isinstance(message, SystemMessage):
            self._show_system(message)
        elif isinstance(message, AssistantMessage):
            self._show_assistant(message)
        elif isinstance(message, UserMessage):
            self._show_user(message)
        elif isinstance(message, ResultMessage):
            self._show_result(message)
        # Other message kinds (rate-limit notices, ...) are not needed to
        # understand stop_reason, so we skip them quietly.

    def show_conversation(self) -> None:
        """Print the whole conversation, showing how it grew."""
        self._print(f"\n{LINE}\nTHE FULL CONVERSATION (in the order it was built)\n{LINE}")
        for number, (who, what) in enumerate(self.conversation, start=1):
            self._print(f"  {number}. [{who}]")
            for line in what.splitlines():
                self._print(f"       {line}")
        self._print(LINE)

    # ---- one method per message kind -----------------------------------

    def _show_system(self, message: SystemMessage) -> None:
        if message.subtype != "init":
            return
        self._header("SETUP (SystemMessage)")
        tools = message.data.get("tools", [])
        self._explain("The SDK started a session. Here are the tools Claude may use.")
        self._print(f"  Tools available: {tools}")

    def _show_assistant(self, message: AssistantMessage) -> None:
        self._header("CLAUDE replies (AssistantMessage)")
        for block in message.content:
            if isinstance(block, TextBlock):
                self._print(f"  Claude says: {block.text}")
                self._append("claude", block.text)
            elif isinstance(block, ThinkingBlock):
                self._print(f"  Claude thinks: {block.thinking[:200]}")
            elif isinstance(block, ToolUseBlock):
                self._print(f"  Claude asks to use a tool:")
                self._print(f"     tool name : {block.name}")
                self._print(f"     tool input: {_pretty(block.input)}")
                self._print(f"     request id: {block.id}")
                self._append("claude (tool request)",
                             f"call {block.name} with {json.dumps(block.input)}")
        self._print(THIN)
        self._print(f"  stop_reason = {message.stop_reason!r}")
        self._explain(explain_stop_reason(message.stop_reason))

    def _show_user(self, message: UserMessage) -> None:
        if not isinstance(message.content, list):
            return
        results = [b for b in message.content if isinstance(b, ToolResultBlock)]
        if not results:
            return
        self._header("TOOL RESULT is sent back to Claude (UserMessage)")
        self._explain(
            "Our tool ran and its answer is appended to the conversation, so "
            "Claude can read it and continue."
        )
        for block in results:
            text = _tool_result_text(block.content)
            self._print(f"  Answer for request id {block.tool_use_id}:")
            for line in text.splitlines():
                self._print(f"     {line}")
            if block.is_error:
                self._print("     (the tool reported an error)")
            self._append("tool result", text)

    def _show_result(self, message: ResultMessage) -> None:
        self._header("FINISHED (ResultMessage)")
        self._explain("The SDK's final summary of the whole run.")
        self._print(f"  final answer : {message.result}")
        self._print(f"  stop_reason  : {message.stop_reason!r}  -> "
              f"{explain_stop_reason(message.stop_reason)}")
        self._print(f"  turns taken  : {message.num_turns}")
        self._print(f"  had an error : {message.is_error}")
        if message.total_cost_usd is not None:
            self._print(f"  cost (USD)   : ${message.total_cost_usd:.4f}")
