#!/usr/bin/env python3

import json, os, urllib.request
import subprocess


API_KEY = os.environ["DEEPSEEK_API_KEY"]
MODEL = "deepseek-flash"
ENDPOINT="https://api.deepseek.com/anthropic/v1/messages"
MAX_ROUNDS = 10


MAIN_SYSTEM = ("You are a capable engineering agent working on the local "
               "machine. Use your tools to complete the user's task. "
               "Delegate self-contained searches and research to the agent "
               "tool to keep your own context small.")

SUB_SYSTEM = ("You are a focused subagent. Complete the task you were "
              "given using your tools, then end with a clear, "
              "self-contained report of your findings. Cite file paths.")


def call_llm(messages, tools, system):
    body={"model": MODEL,
          "system": system,
          "tools": tools,
          "messages": messages}
    req = urllib.request.Request(
        ENDPOINT,
        data = json.dumps(body).encode(),
        headers = {"content-type": "application/json",
                   "x-api-key": API_KEY,})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


BASE_TOOLS = [                                            # NEW: the menu
    {"name": "read_file",
     "description": "Read a text file and return its contents.",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"}},
                      "required": ["path"]}},
    {"name": "write_file",                           # NEW: change the world
     "description": "Write content to a file, replacing it if it exists.",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"},
                                     "content": {"type": "string"}},
                      "required": ["path", "content"]}},                      
    {"name": "run_command",
     "description": "Run a shell command and return stdout+stderr.",
     "input_schema": {"type": "object",
                      "properties": {"command": {"type": "string"}},
                      "required": ["command"]}},
]

AGENT_TOOL = {                                       # NEW: delegation
    "name": "agent",
    "description": ("Delegate a self-contained task to a subagent with its "
                    "own fresh context. It can read files and run commands, "
                    "and returns only its final answer. Use it for searches "
                    "and research whose details you don't need to keep. "
                    "The subagent knows NOTHING about this conversation, so "
                    "include all necessary background in the task."),
    "input_schema": {"type": "object",
                     "properties": {"task": {"type": "string"}},
                     "required": ["task"]},
}

MAIN_TOOLS = BASE_TOOLS + [AGENT_TOOL]
SUB_TOOLS = BASE_TOOLS                               # no grandchildren


def execute_tool(name, args, allow_agent):                        # NEW: the dispatch
    """Map the model's JSON request to a real function call."""
    try:
        if name == "read_file":
            return open(args["path"]).read()
        if name == "write_file":
            with open(args["path"], "w") as f:
                f.write(args["content"])
            return f"wrote {len(args['content'])} bytes to {args['path']}"        
        if name == "run_command":
            out = subprocess.run(args["command"], shell=True,
                                 capture_output=True, text=True, timeout=60)
            return out.stdout + out.stderr
        if name == "agent" and allow_agent:          # NEW
            return run_subagent(args["task"])
        return f"ERROR: unknown tool {name}"
    except Exception as e:
        return f"ERROR: {e}"                         # errors go BACK to the model



def run_subagent(task):
    """A subagent IS the agent loop, run over a fresh array."""
    sub_messages = [{"role": "user", "content": task}]     # fresh world
    final_text = run_loop(sub_messages, tools=SUB_TOOLS,   # chapter 4's loop
                          system=SUB_SYSTEM, quiet=True)
    return final_text or "(subagent returned no answer)"   # only this survives


def run_loop(messages, tools, system, quiet=False, allow_agent=False):
    """Chapter 4's agent loop, now reusable. Returns the final text."""
    final_text = ""
    for _ in range(MAX_ROUNDS):
        reply = call_llm(messages, tools, system)
        messages.append({"role": "assistant", "content": reply["content"]})
        for block in reply["content"]:
            if block["type"] == "text" and block["text"].strip():
                final_text = block["text"]
                if not quiet:
                    print(f"\nassistant> {block['text']}")

        if reply["stop_reason"] != "tool_use":
            return final_text

        results = []
        for block in reply["content"]:
            if block["type"] == "tool_use":
                tag = "sub" if quiet else "tool"
                print(f"[{tag}] {block['name']}({json.dumps(block['input'])[:100]})")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": execute_tool(block["name"], block["input"],
                                            allow_agent),
                })
        messages.append({"role": "user", "content": results})
    return final_text



def main():
    messages = []
    while True:
        user_text = input("\nyou> ").strip()
        if user_text in ("/quit", ""):
            break
        messages.append({"role": "user", "content": user_text})
        run_loop(messages, tools=MAIN_TOOLS, system=MAIN_SYSTEM,
                 allow_agent=True)

if __name__ == "__main__":
    main()

