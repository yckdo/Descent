"""Opt-in diagnostic adapter: never changes production RAG answer."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from stair_reasoner import reason


def enabled():
    return os.environ.get("STAIR_SHADOW_ENABLED", "0").strip().lower() in {"1", "true", "on", "yes"}


def compare_observation(rag_response, reasoning_spec=None, *, shadow_enabled=None):
    if not isinstance(rag_response, str):
        raise TypeError("rag_response must be a string")
    active = enabled() if shadow_enabled is None else shadow_enabled
    if not active:
        observation = {"mode": "disabled", "status": "not_run"}
    elif reasoning_spec is None:
        observation = {"mode": "shadow", "status": "no_spec"}
    else:
        try:
            report = reason(reasoning_spec)
            observation = {"mode": "shadow", "status": "completed",
                           "query": report["query"],
                           "reasoner_status": report["status"],
                           "proof_graph": report["proof_graph"],
                           "limitations": report["limitations"],
                           "warning": "Does not validate production answer"}
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
            observation = {"mode": "shadow", "status": "error",
                           "error_type": type(exc).__name__,
                           "warning": "Production answer unchanged"}
    return {"rag_response": rag_response, "shadow": observation}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--enable", action="store_true")
    args = parser.parse_args()
    if args.input.stat().st_size > 1024 * 1024:
        parser.error("Input exceeds 1 MiB")
    envelope = json.loads(args.input.read_text(encoding="utf-8"))
    print(json.dumps(compare_observation(envelope["rag_response"],
          envelope.get("reasoning_spec"), shadow_enabled=True if args.enable else None),
          ensure_ascii=False, indent=2))
