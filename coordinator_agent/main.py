# A basic coordinator agent.
#
# The coordinator is a normal Claude agent loop (same shape as
# tool_use/agentic_loop.py). Its "tools" are specialist sub-agents: when it
# calls one, we run a separate, focused Claude call and hand the answer back
# as the tool result.

import anthropic

client = anthropic.Anthropic()

# Change these to switch models. The coordinator plans and delegates; the
# workers do the narrow jobs, so they can use a cheaper model.
COORDINATOR_MODEL = "claude-sonnet-5-5"
WORKER_MODEL = "claude-haiku-5-5"

MAX_STEPS = 10  # safety stop so a confused coordinator can't loop forever

COORDINATOR_SYSTEM = (
    "You are a coordinator. You do not research or write yourself. "
    "Break the user's request into steps and delegate each step to the right "
    "specialist: first the researcher to gather facts, then the writer to turn "
    "those facts into the final text. Pass the researcher's notes to the writer "
    "word for word. When the writer returns, give the user its text as the answer."
)

# Each specialist has its own system prompt: that is what makes it a specialist.
SPECIALISTS = {
    "ask_researcher": {
        "description": "Gather the key facts about a topic. Returns short bullet-point notes.",
        "param": "topic",
        "system": "You are a researcher. Reply with 4-6 accurate, concise bullet points. No intro or outro.",
    },
    "ask_writer": {
        "description": "Write the final text from research notes. Returns a short paragraph.",
        "param": "notes",
        "system": "You are a writer. Turn the notes you are given into one clear, friendly paragraph for the audience the notes mention. Reply with the paragraph only.",
    },
}

tools = [
    {
        "name": name,
        "description": spec["description"],
        "input_schema": {
            "type": "object",
            "properties": {spec["param"]: {"type": "string"}},
            "required": [spec["param"]],
        },
    }
    for name, spec in SPECIALISTS.items()
]


def run_subagent(name, tool_input):
    """Run one specialist: a single, separate Claude call with its own role."""
    spec = SPECIALISTS.get(name)
    if spec is None:
        return f"Unknown specialist: {name}"
    response = client.messages.create(
        model=WORKER_MODEL,
        max_tokens=1024,
        system=spec["system"],
        messages=[{"role": "user", "content": tool_input[spec["param"]]}],
    )
    return next(block.text for block in response.content if block.type == "text")


def coordinate(request):
    messages = [{"role": "user", "content": request}]

    for step in range(1, MAX_STEPS + 1):
        response = client.messages.create(
            model=COORDINATOR_MODEL,
            max_tokens=1024,
            system=COORDINATOR_SYSTEM,
            tools=tools,
            messages=messages,
        )
        print(f"[coordinator step {step}] stop_reason = {response.stop_reason}")

        if response.stop_reason == "refusal":
            return "The request was declined."
        if response.stop_reason != "tool_use":
            return next(block.text for block in response.content if block.type == "text")

        # Run every delegation Claude asked for, then return all results together.
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"  -> delegating to {block.name}: {str(block.input)[:100]}")
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": run_subagent(block.name, block.input),
                }
            )
        messages.append({"role": "user", "content": results})

    return "Stopped: the coordinator used all its steps without finishing."


if __name__ == "__main__":
    print(coordinate("Explain why the sky is blue to a 10-year-old."))
