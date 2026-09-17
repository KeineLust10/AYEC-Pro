#!/usr/bin/env python3
"""
Claude Local Proxy — LEGACY Ollama path.

Translates Anthropic Messages API to Ollama / llama.cpp OpenAI API.
Kept for users who want the old Ollama route. The recommended path is now
the MLX Native Anthropic Server (`proxy/server.py`) — it speaks Anthropic
directly, no translation layer, ~7.5x faster on real Claude Code tasks.
"""

import json
import sys
import time
import uuid
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.parse import urlparse

# Backend configuration — switch between Ollama and llama-server (TurboQuant)
import os
BACKEND = os.environ.get("PROXY_BACKEND", "turbo")  # "turbo" (default) or "ollama"

BACKENDS = {
    "ollama": "http://localhost:11434/v1/chat/completions",
    "turbo":  "http://localhost:8090/v1/chat/completions",
}
BACKEND_URL = BACKENDS.get(BACKEND, BACKENDS["ollama"])

MODEL_MAP_OLLAMA = {
    "claude-opus-4-6": "qwen3.5:122b",
    "claude-sonnet-4-6": "qwen3.5:122b",
    "claude-haiku-4-5-20251001": "qwen3.5:4b",
}
MODEL_MAP_TURBO = {
    "claude-opus-4-6": "test",
    "claude-sonnet-4-6": "test",
    "claude-haiku-4-5-20251001": "test",
}
MODEL_MAP = MODEL_MAP_TURBO if BACKEND == "turbo" else MODEL_MAP_OLLAMA
DEFAULT_MODEL = "test" if BACKEND == "turbo" else "qwen3.5:122b"
PORT = 4000


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def strip_think_tags(text):
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    return cleaned if cleaned else text


def get_path(full_path):
    """Extract path without query parameters."""
    return urlparse(full_path).path


def convert_anthropic_to_openai(body):
    model = body.get("model", "claude-sonnet-4-6")
    ollama_model = MODEL_MAP.get(model, DEFAULT_MODEL)

    messages = []
    if body.get("system"):
        sys_text = body["system"]
        if isinstance(sys_text, list):
            sys_text = "\n".join(b.get("text", "") for b in sys_text if b.get("type") == "text")
        messages.append({"role": "system", "content": sys_text})

    for msg in body.get("messages", []):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            parts = []
            for block in content:
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    tc = block.get("content", "")
                    if isinstance(tc, list):
                        tc = "\n".join(b.get("text", str(b)) for b in tc)
                    parts.append(str(tc))
                elif block.get("type") == "tool_use":
                    parts.append(f"[Tool call: {block.get('name', '')}({json.dumps(block.get('input', {}))})]")
            content = "\n".join(p for p in parts if p)
        messages.append({"role": role, "content": content})

    tools = None
    if body.get("tools"):
        tools = []
        for tool in body["tools"]:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                }
            })

    openai_body = {
        "model": ollama_model,
        "messages": messages,
        "max_tokens": body.get("max_tokens", 8192),
        "temperature": body.get("temperature", 0.7),
    }
    if tools:
        openai_body["tools"] = tools
    if body.get("stop_sequences"):
        openai_body["stop"] = body["stop_sequences"]

    return openai_body


def convert_openai_to_anthropic(openai_resp, request_model):
    choice = openai_resp.get("choices", [{}])[0]
    message = choice.get("message", {})
    usage = openai_resp.get("usage", {})

    content_blocks = []

    # Handle tool calls
    if message.get("tool_calls"):
        for tc in message["tool_calls"]:
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            content_blocks.append({
                "type": "tool_use",
                "id": tc.get("id", f"toolu_{uuid.uuid4().hex[:20]}"),
                "name": fn.get("name", ""),
                "input": args,
            })

    # Merge reasoning + content
    reasoning = message.get("reasoning", "") or ""
    content = message.get("content", "") or ""

    if not content.strip() and reasoning.strip():
        # Extract code blocks from reasoning if present
        code_blocks = re.findall(r'```[\w]*\n(.*?)```', reasoning, re.DOTALL)
        if code_blocks:
            lang_blocks = re.findall(r'(```[\w]*\n.*?```)', reasoning, re.DOTALL)
            content = "\n\n".join(lang_blocks) if lang_blocks else code_blocks[-1]
        else:
            content = reasoning

    content = strip_think_tags(content)

    # Clean reasoning artifacts from start
    if content.lstrip().startswith("Thinking"):
        lines = content.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('```') or stripped.startswith('def ') or stripped.startswith('class ') or stripped.startswith('function ') or stripped.startswith('import ') or stripped.startswith('#') or stripped.startswith('//'):
                content = '\n'.join(lines[i:])
                break

    if content.strip() and not content_blocks:
        content_blocks.append({"type": "text", "text": content.strip()})
    elif not content_blocks:
        content_blocks.append({"type": "text", "text": "(No output)"})

    stop_reason = "end_turn"
    if choice.get("finish_reason") == "tool_calls":
        stop_reason = "tool_use"
    elif choice.get("finish_reason") == "length":
        stop_reason = "max_tokens"

    return {
        "id": f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "model": request_model,
        "content": content_blocks,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        }
    }


def send_json(handler, status, data):
    resp = json.dumps(data).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", len(resp))
    handler.end_headers()
    handler.wfile.write(resp)


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_HEAD(self):
        log(f"HEAD {self.path}")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def do_POST(self):
        path = get_path(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(content_length) if content_length else b'{}'
        body = json.loads(raw)
        log(f"POST {self.path} model={body.get('model','-')} max_tokens={body.get('max_tokens','-')}")

        if path in ("/v1/messages", "/messages"):
            request_model = body.get("model", "claude-sonnet-4-6")
            openai_body = convert_anthropic_to_openai(body)
            log(f"  → Ollama model={openai_body['model']} tokens={openai_body['max_tokens']}")

            try:
                req = Request(
                    BACKEND_URL,
                    data=json.dumps(openai_body).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urlopen(req, timeout=600) as resp:
                    openai_resp = json.loads(resp.read().decode('utf-8', 'replace'))

                anthropic_resp = convert_openai_to_anthropic(openai_resp, request_model)
                text = anthropic_resp["content"][0].get("text", "")[:80]
                log(f"  ← OK ({anthropic_resp['usage']['output_tokens']} tok) {text}...")
                send_json(self, 200, anthropic_resp)

            except Exception as e:
                log(f"  ← ERROR: {e}")
                send_json(self, 500, {"error": {"type": "server_error", "message": str(e)}})
        else:
            log(f"  Unknown POST path: {path}")
            send_json(self, 200, {})

    def do_GET(self):
        path = get_path(self.path)
        log(f"GET {self.path}")

        if path in ("/v1/models", "/models"):
            send_json(self, 200, {
                "object": "list",
                "data": [
                    {"id": name, "object": "model", "created": int(time.time()), "owned_by": "local"}
                    for name in MODEL_MAP
                ]
            })
        elif path == "/health":
            send_json(self, 200, {"status": "ok"})
        else:
            send_json(self, 200, {})


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), ProxyHandler)
    print(f"Claude Local Proxy on http://localhost:{PORT}")
    print(f"Backend: {BACKEND} → {BACKEND_URL}")
    print(f"Models: {list(MODEL_MAP.keys())}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()
