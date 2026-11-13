#!/usr/bin/env python3
"""
claude_bedrock.py - call Claude on Amazon Bedrock from Python.

Shows, in one file:
  1. Authentication with a Bedrock API key (stub, you fill it in)
  2. A basic call with the Converse API
  3. Passing context: system prompt, a pinned document, and conversation history
  4. Token management: count before sending, cap output, trim history, read usage
  5. The other options: streaming and the raw InvokeModel API

Requires: Python 3.9+, boto3 >= 1.39.0 (older versions ignore Bedrock API keys)
    pip install --upgrade boto3

Examples:
    python claude_bedrock.py "Explain inference profiles in two sentences."
    python claude_bedrock.py --context-file notes.txt "Summarise this document."
    python claude_bedrock.py --mode stream "Write a haiku about latency."
    python claude_bedrock.py --mode invoke "Same question, raw InvokeModel API."
    python claude_bedrock.py --chat --budget 2000
"""
import argparse
import json
import os
import sys

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# 1. Configuration and authentication
# ---------------------------------------------------------------------------

# STUB: paste your Bedrock API key here, or leave this alone and export
# AWS_BEARER_TOKEN_BEDROCK in your shell (the environment variable wins).
# Never commit a real key to version control.
BEDROCK_API_KEY = "PASTE_YOUR_BEDROCK_API_KEY_HERE"

REGION = os.environ.get("AWS_REGION", "us-east-1")

# A plain model ID stays in one Region. An inference profile ID (prefix "us.",
# "eu.", "global.", ...) lets Bedrock route across Regions. Check the Bedrock
# console for the IDs available to your account before running.
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")

DEFAULT_SYSTEM = "You are a concise, accurate assistant."

# Optional: fill in your model's list prices (USD per million tokens) to see a
# cost estimate after each call. Left as None so the script never guesses.
PRICE_IN_PER_MTOK = None
PRICE_OUT_PER_MTOK = None


def configure_auth():
    """Make the Bedrock API key visible to boto3, which reads it from the environment."""
    if os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        return
    if BEDROCK_API_KEY.startswith("PASTE_"):
        sys.exit(
            "No Bedrock API key found. Set BEDROCK_API_KEY in this file or export "
            "AWS_BEARER_TOKEN_BEDROCK before running."
        )
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = BEDROCK_API_KEY


def make_client():
    """Create the Bedrock runtime client, with retries for throttling errors."""
    return boto3.client(
        "bedrock-runtime",
        region_name=REGION,
        config=Config(retries={"max_attempts": 5, "mode": "adaptive"}, read_timeout=120),
    )


# ---------------------------------------------------------------------------
# 2. Building a request (Converse API)
# ---------------------------------------------------------------------------

def user_msg(text):
    return {"role": "user", "content": [{"text": text}]}


def assistant_msg(text):
    return {"role": "assistant", "content": [{"text": text}]}


def build_system(system_prompt, document=None):
    """
    The system prompt carries standing instructions. A reference document is
    pinned here too, so it is never trimmed away when the history is shortened.
    """
    blocks = [{"text": system_prompt}]
    if document:
        blocks.append({"text": f"<document>\n{document}\n</document>"})
    return blocks


def build_request(system, messages, max_tokens, temperature=None, top_p=None, stop=None):
    """
    Assemble the keyword arguments for client.converse().

    inferenceConfig options:
      maxTokens      hard cap on output tokens (also caps what you can be billed for)
      temperature    randomness; lower is steadier
      topP           nucleus sampling; set one of temperature/topP, not both
      stopSequences  strings that end generation early
    """
    config = {"maxTokens": max_tokens}
    if temperature is not None:
        config["temperature"] = temperature
    if top_p is not None:
        config["topP"] = top_p
    if stop:
        config["stopSequences"] = stop
    return {
        "modelId": MODEL_ID,
        "system": system,
        "messages": messages,
        "inferenceConfig": config,
        # Model-specific extras go here, for example:
        # "additionalModelRequestFields": {"top_k": 40},
    }


# ---------------------------------------------------------------------------
# 3. Token management
# ---------------------------------------------------------------------------

def count_input_tokens(client, system, messages):
    """
    Ask Bedrock how many input tokens this request would use, before sending it.
    Not every model supports counting, so fall back to a rough estimate
    (about 4 characters per token for English).
    """
    try:
        resp = client.count_tokens(
            modelId=MODEL_ID,
            input={"converse": {"messages": messages, "system": system}},
        )
        return resp["inputTokens"]
    except ClientError:
        chars = sum(len(b.get("text", "")) for b in system)
        chars += sum(len(b.get("text", "")) for m in messages for b in m["content"])
        return chars // 4


def trim_history(client, system, messages, budget):
    """
    Drop the oldest user/assistant pair until the input fits the token budget.
    The latest user message is always kept. Returns how many messages were dropped.
    """
    dropped = 0
    while len(messages) > 1 and count_input_tokens(client, system, messages) > budget:
        del messages[:2]  # history alternates user, assistant, so remove one pair
        dropped += 2
    return dropped


def report(usage, latency_ms=None, stop_reason=None):
    line = f"[tokens in={usage.get('inputTokens', usage.get('input_tokens'))} "
    line += f"out={usage.get('outputTokens', usage.get('output_tokens'))}"
    if latency_ms is not None:
        line += f" latency={latency_ms}ms"
    if stop_reason:
        line += f" stop={stop_reason}"
    line += "]"
    tin = usage.get("inputTokens", usage.get("input_tokens", 0))
    tout = usage.get("outputTokens", usage.get("output_tokens", 0))
    if PRICE_IN_PER_MTOK is not None and PRICE_OUT_PER_MTOK is not None:
        cost = tin / 1e6 * PRICE_IN_PER_MTOK + tout / 1e6 * PRICE_OUT_PER_MTOK
        line += f" [~${cost:.4f}]"
    print(line, file=sys.stderr)
    if stop_reason == "max_tokens":
        print("[warning: output was cut off by --max-tokens]", file=sys.stderr)


# ---------------------------------------------------------------------------
# 4. The three ways to call the model
# ---------------------------------------------------------------------------

def call_converse(client, request):
    """Converse API: one request format across models, returns the whole reply."""
    resp = client.converse(**request)
    blocks = resp["output"]["message"]["content"]
    text = "".join(b["text"] for b in blocks if "text" in b)
    report(resp["usage"], resp.get("metrics", {}).get("latencyMs"), resp.get("stopReason"))
    return text


def call_stream(client, request):
    """ConverseStream: same request, but text arrives in pieces as it is generated."""
    resp = client.converse_stream(**request)
    parts, usage, stop = [], {}, None
    for event in resp["stream"]:
        if "contentBlockDelta" in event:
            delta = event["contentBlockDelta"]["delta"]
            if "text" in delta:
                print(delta["text"], end="", flush=True)
                parts.append(delta["text"])
        elif "messageStop" in event:
            stop = event["messageStop"].get("stopReason")
        elif "metadata" in event:
            usage = event["metadata"].get("usage", {})
    print()
    report(usage, stop_reason=stop)
    return "".join(parts)


def call_invoke(client, prompt, system_text, max_tokens, temperature=None):
    """
    InvokeModel: the raw, provider-specific format. For Claude this is the
    Anthropic Messages shape. Use it when you need a feature Converse does not
    expose yet; otherwise Converse is simpler and portable across models.
    """
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system_text,
        "messages": [{"role": "user", "content": prompt}],
    }
    if temperature is not None:
        body["temperature"] = temperature
    resp = client.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    data = json.loads(resp["body"].read())
    text = "".join(b["text"] for b in data["content"] if b.get("type") == "text")
    report(data["usage"], stop_reason=data.get("stop_reason"))
    return text


# ---------------------------------------------------------------------------
# 5. Command line
# ---------------------------------------------------------------------------

def chat_loop(client, args, system):
    """Multi-turn chat. History is resent each turn, so it is trimmed to the budget."""
    history = []
    print(f"Chatting with {MODEL_ID}. Type /quit to exit.", file=sys.stderr)
    while True:
        try:
            prompt = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if prompt in ("/quit", "/exit"):
            break
        if not prompt:
            continue
        history.append(user_msg(prompt))
        dropped = trim_history(client, system, history, args.budget)
        if dropped:
            print(f"[trimmed {dropped} old messages to fit {args.budget} tokens]", file=sys.stderr)
        request = build_request(system, history, args.max_tokens, args.temperature)
        reply = call_converse(client, request)
        print(f"claude> {reply}")
        history.append(assistant_msg(reply))


def main():
    p = argparse.ArgumentParser(description="Call Claude on Amazon Bedrock.")
    p.add_argument("prompt", nargs="?", help="the user prompt")
    p.add_argument("--mode", choices=["converse", "stream", "invoke"], default="converse")
    p.add_argument("--system", default=DEFAULT_SYSTEM, help="system prompt")
    p.add_argument("--context-file", help="text file to include as reference context")
    p.add_argument("--max-tokens", type=int, default=512, help="output token cap")
    p.add_argument("--temperature", type=float, default=None)
    p.add_argument("--budget", type=int, default=8000, help="max input tokens before history is trimmed")
    p.add_argument("--chat", action="store_true", help="interactive multi-turn chat")
    args = p.parse_args()

    if not args.chat and not args.prompt:
        p.error("give a prompt, or use --chat")

    configure_auth()
    client = make_client()

    document = None
    if args.context_file:
        with open(args.context_file, encoding="utf-8") as f:
            document = f.read()
    system = build_system(args.system, document)

    try:
        if args.chat:
            chat_loop(client, args, system)
            return

        messages = [user_msg(args.prompt)]
        n_in = count_input_tokens(client, system, messages)
        print(f"[input tokens before sending: {n_in}]", file=sys.stderr)
        if n_in > args.budget:
            sys.exit(f"Input is {n_in} tokens, over the budget of {args.budget}. Shorten the context.")

        if args.mode == "invoke":
            system_text = "\n\n".join(b["text"] for b in system)
            print(call_invoke(client, args.prompt, system_text, args.max_tokens, args.temperature))
        else:
            request = build_request(system, messages, args.max_tokens, args.temperature)
            if args.mode == "stream":
                call_stream(client, request)
            else:
                print(call_converse(client, request))
    except ClientError as e:
        err = e.response["Error"]
        sys.exit(f"Bedrock error {err['Code']}: {err['Message']}")


if __name__ == "__main__":
    main()
