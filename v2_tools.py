#!/usr/bin/env python3

import subprocess
import json, os, urllib.request


TOOLS = [                                            # NEW: the menu
    {"name": "read_file",
     "description": "Read a text file and return its contents.",
     "input_schema": {"type": "object",
                      "properties": {"path": {"type": "string"}},
                      "required": ["path"]}},
    {"name": "run_command",
     "description": "Run a shell command and return stdout+stderr.",
     "input_schema": {"type": "object",
                      "properties": {"command": {"type": "string"}},
                      "required": ["command"]}},
]

def execute_tool(name, args):                        # NEW: the dispatch
    """Map the model's JSON request to a real function call."""
    try:
        if name == "read_file":
            return open(args["path"]).read()
        if name == "run_command":
            out = subprocess.run(args["command"], shell=True,
                                 capture_output=True, text=True, timeout=60)
            return out.stdout + out.stderr
        return f"ERROR: unknown tool {name}"
    except Exception as e:
        return f"ERROR: {e}"                         # errors go BACK to the model




def call_llm(messages):
    body={"model": MODEL,
          "system": SYSTEM,
          "messages": messages}
    req = urllib.request.Request(
        ENDPOINT,
        data = json.dumps(body).encode(),
        headers = {"content-type": "application/json",
                   "x-api-key": API_KEY,})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def main():
    messages = []
    while True:
        user_text = input("\nyou> ").strip()
        if user_text in ("/quit", ""):
            break
        messages.append({"role": "user", "content": user_text})

        reply = call_llm(messages)
        messages.append({"role": "assistant", "content": reply["content"]})

        for block in reply["content"]:
            if block["type"] == "text":
                print(f"\nassistant> {block['text']}")
            elif block["type"] == "tool_use":        # NEW: honor ONE request
                print(f"\n[tool] {block['name']}({json.dumps(block['input'])})")
                result = execute_tool(block["name"], block["input"])
                messages.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": block["id"],
                     "content": result}]})
                reply2 = call_llm(messages)          # let the model react once
                messages.append({"role": "assistant",
                                 "content": reply2["content"]})
                for b2 in reply2["content"]:
                    if b2["type"] == "text":
                        print(f"\nassistant> {b2['text']}")
                # If reply2 asks for ANOTHER tool, v2 drops it. Chapter 4.

if __name__ == "__main__":
    main()
