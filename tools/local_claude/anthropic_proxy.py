#!/usr/bin/env python3
"""
Windows-friendly Anthropic Messages API shim for Claude Code + Ollama.

This keeps the same basic trick used by claude-code-local:
Claude Code talks to localhost:4000 using Anthropic-style requests,
while this proxy translates them to Ollama's OpenAI-compatible endpoint.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from urllib.request import Request, urlopen

HOST = os.environ.get("LOCAL_CLAUDE_HOST", "127.0.0.1")
PORT = int(os.environ.get("LOCAL_CLAUDE_PORT", "4000"))
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
OLLAMA_CHAT_URL = f"{OLLAMA_BASE_URL.rstrip('/')}/chat/completions"
DEFAULT_OLLAMA_MODEL = os.environ.get("LOCAL_OLLAMA_MODEL", "qwen3-coder:30b")
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("LOCAL_CLAUDE_TIMEOUT", "1800"))
UPSTREAM_RETRIES = int(os.environ.get("LOCAL_CLAUDE_RETRIES", "3"))
UPSTREAM_RETRY_DELAY_SECONDS = float(os.environ.get("LOCAL_CLAUDE_RETRY_DELAY", "1.5"))

MODEL_MAP = {
    "claude-opus-4-6": DEFAULT_OLLAMA_MODEL,
    "claude-sonnet-4-6": DEFAULT_OLLAMA_MODEL,
    "claude-haiku-4-5": DEFAULT_OLLAMA_MODEL,
    "claude-haiku-4-5-20251001": DEFAULT_OLLAMA_MODEL,
}


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)


def get_path(full_path: str) -> str:
    return urlparse(full_path).path


def flatten_content(content) -> str:
    if isinstance(content, str):
        return content

    if not isinstance(content, list):
        return str(content)

    parts: list[str] = []
    for block in content:
        block_type = block.get("type")
        if block_type == "text":
            parts.append(block.get("text", ""))
        elif block_type == "tool_result":
            result = block.get("content", "")
            if isinstance(result, list):
                text_items = [item.get("text", str(item)) for item in result]
                parts.append("\n".join(text_items))
            else:
                parts.append(str(result))
        elif block_type == "tool_use":
            parts.append(
                f"[Tool call: {block.get('name', '')}({json.dumps(block.get('input', {}), ensure_ascii=False)})]"
            )
    return "\n".join(part for part in parts if part)


def convert_anthropic_to_openai(body: dict) -> dict:
    requested_model = body.get("model", "claude-sonnet-4-6")
    ollama_model = MODEL_MAP.get(requested_model, DEFAULT_OLLAMA_MODEL)

    messages: list[dict] = []
    system_value = body.get("system")
    if system_value:
        if isinstance(system_value, list):
            system_text = "\n".join(
                block.get("text", "") for block in system_value if block.get("type") == "text"
            )
        else:
            system_text = str(system_value)
        messages.append({"role": "system", "content": system_text})

    for message in body.get("messages", []):
        messages.append(
            {
                "role": message.get("role", "user"),
                "content": flatten_content(message.get("content", "")),
            }
        )

    openai_payload = {
        "model": ollama_model,
        "messages": messages,
        "max_tokens": body.get("max_tokens", 8192),
        "temperature": body.get("temperature", 0.2),
        "stream": False,
    }

    anthropic_tools = body.get("tools") or []
    if anthropic_tools:
        openai_payload["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                },
            }
            for tool in anthropic_tools
        ]

    stop_sequences = body.get("stop_sequences")
    if stop_sequences:
        openai_payload["stop"] = stop_sequences

    return openai_payload


def strip_think_tags(text: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    cleaned = re.sub(r"</think>", "", cleaned).strip()
    return cleaned if cleaned else text


def convert_openai_to_anthropic(openai_response: dict, requested_model: str) -> dict:
    choice = openai_response.get("choices", [{}])[0]
    message = choice.get("message", {})
    usage = openai_response.get("usage", {})
    content_blocks: list[dict] = []

    tool_calls = message.get("tool_calls") or []
    for tool_call in tool_calls:
        fn = tool_call.get("function", {})
        try:
            input_payload = json.loads(fn.get("arguments", "{}"))
        except json.JSONDecodeError:
            input_payload = {}

        content_blocks.append(
            {
                "type": "tool_use",
                "id": tool_call.get("id", f"toolu_{uuid.uuid4().hex[:20]}"),
                "name": fn.get("name", ""),
                "input": input_payload,
            }
        )

    reasoning = message.get("reasoning", "") or ""
    text = message.get("content", "") or ""
    if not str(text).strip() and str(reasoning).strip():
        text = reasoning
    text = strip_think_tags(str(text))
    if text.strip() and not content_blocks:
        content_blocks.append({"type": "text", "text": text.strip()})
    elif not content_blocks:
        content_blocks.append({"type": "text", "text": "(No output)"})

    finish_reason = choice.get("finish_reason")
    stop_reason = "end_turn"
    if finish_reason == "tool_calls":
        stop_reason = "tool_use"
    elif finish_reason == "length":
        stop_reason = "max_tokens"

    return {
        "id": f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "model": requested_model,
        "content": content_blocks,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    }


def send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    try:
        handler.wfile.write(body)
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        log("Client disconnected before proxy response was written")


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def do_GET(self):
        path = get_path(self.path)
        if path in ("/health", "/v1/health"):
            send_json(self, 200, {"status": "ok", "backend": OLLAMA_CHAT_URL, "model": DEFAULT_OLLAMA_MODEL})
            return

        if path in ("/models", "/v1/models"):
            send_json(
                self,
                200,
                {
                    "object": "list",
                    "data": [
                        {
                            "id": model_name,
                            "object": "model",
                            "created": int(time.time()),
                            "owned_by": "local",
                        }
                        for model_name in MODEL_MAP
                    ],
                },
            )
            return

        send_json(self, 200, {})

    def do_POST(self):
        path = get_path(self.path)
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        request_body = json.loads(raw_body.decode("utf-8"))

        if path not in ("/messages", "/v1/messages"):
            send_json(self, 200, {})
            return

        requested_model = request_body.get("model", "claude-sonnet-4-6")
        upstream_payload = convert_anthropic_to_openai(request_body)
        log(
            f"POST {path} requested_model={requested_model} "
            f"ollama_model={upstream_payload['model']} max_tokens={upstream_payload['max_tokens']}"
        )

        last_error = None
        for attempt in range(1, UPSTREAM_RETRIES + 1):
            try:
                upstream_request = Request(
                    OLLAMA_CHAT_URL,
                    data=json.dumps(upstream_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(upstream_request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                    upstream_response = json.loads(response.read().decode("utf-8", "replace"))
                anthropic_response = convert_openai_to_anthropic(upstream_response, requested_model)
                send_json(self, 200, anthropic_response)
                return
            except Exception as exc:
                last_error = exc
                log(f"ERROR attempt {attempt}/{UPSTREAM_RETRIES}: {exc}")
                if attempt < UPSTREAM_RETRIES:
                    time.sleep(UPSTREAM_RETRY_DELAY_SECONDS)

        send_json(self, 500, {"error": {"type": "server_error", "message": str(last_error)}})


if __name__ == "__main__":
    log(f"Claude local proxy listening on http://{HOST}:{PORT}")
    log(f"Upstream Ollama endpoint: {OLLAMA_CHAT_URL}")
    log(f"Default mapped model: {DEFAULT_OLLAMA_MODEL}")
    HTTPServer((HOST, PORT), ProxyHandler).serve_forever()
