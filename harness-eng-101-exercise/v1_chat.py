#!/usr/bin/env python3

"""harness v1: a chat loop, The array IS the conversation."""
import json, os, urllib.request

API_KEY = os.environ["DEEPSEEK_API_KEY"]
MODEL = "deepseek-flash"
ENDPOINT="https://api.deepseek.com/anthropic/v1/messages"
SYSTEM = "You are a concise assistant."

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
        if user_text == "/clear":
            messages = []
            continue
        messages.append({"role":"user", "content": user_text})
        reply = call_llm(messages)
        text = "".join(b["text"] for b in reply["content"]
                   if b["type"] == "text")
        messages.append({"role":"assistant", "content": reply["content"]})
        print(f"\nassistant> {text}")

if __name__ == "__main__":
    main()
