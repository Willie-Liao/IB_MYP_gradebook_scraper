#!/usr/bin/env python3
"""Inject GitNexus code-intelligence context when the user prompt is code-related."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENTS_MD = PROJECT_ROOT / "AGENTS.md"
REPO_NAME = "IB_MYP_gradebook_scraper"

# Prompt / attachment signals that this is a code question (per AGENTS.md hook trigger).
CODE_PROMPT_RE = re.compile(
    r"(?i)"
    r"(\b(code|refactor|debug|fix|bug|implement|function|class|method|module|import|rename)\b"
    r"|\b(test|pytest|unittest|scraper|extractor|auth|gui|excel|gradebook)\b"
    r"|\b(architecture|gitnexus|impact|symbol|commit|edit|modify|patch|diff)\b"
    r"|\b(how does|what does|where is|explain|trace|blast radius)\b"
    r"|\b(src/|tests/|\.py\b|login_example|managebac)\b"
    r"|\b(add|remove|update|delete|create)\b.{0,40}\b(file|function|class|module|script)\b)"
)

CODE_FILE_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}
CODE_FILE_PARTS = ("src/", "tests/", ".cursor/", ".claude/", "login_example")


def _load_gitnexus_context() -> str:
    text = AGENTS_MD.read_text(encoding="utf-8")
    start = text.find("<!-- gitnexus:start -->")
    end = text.find("<!-- gitnexus:end -->")
    if start == -1 or end == -1:
        return (
            f"# GitNexus hook\n\n"
            f"Use GitNexus MCP (`user-gitnexus`) for this repo (`{REPO_NAME}`). "
            f"Run `impact` before edits and `detect_changes` before commits."
        )
    block = text[start + len("<!-- gitnexus:start -->") : end].strip()
    return (
        "# GitNexus code intelligence (AGENTS.md hook)\n\n"
        "This user message is **code-related**. Before answering or editing:\n"
        "- Use **GitNexus MCP** (`user-gitnexus`, repo: "
        f"`{REPO_NAME}`).\n"
        "- Prefer `query` / `context` over blind grepping.\n"
        "- Run `impact` before symbol edits; `detect_changes` before commits.\n\n"
        f"{block}"
    )


def _is_code_related(prompt: str, attachments: list[dict]) -> bool:
    if CODE_PROMPT_RE.search(prompt or ""):
        return True
    for att in attachments or []:
        path = (att.get("file_path") or "").replace("\\", "/")
        if not path:
            continue
        lower = path.lower()
        if any(part in lower for part in CODE_FILE_PARTS):
            return True
        if Path(lower).suffix in CODE_FILE_SUFFIXES and "gradebook_scraper" in lower:
            return True
        if lower.endswith(".py") or "/src/" in lower or lower.startswith("src/"):
            return True
    return False


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        print("{}")
        return

    event = data.get("hook_event_name", "")

    if event == "beforeSubmitPrompt":
        prompt = data.get("prompt", "")
        attachments = data.get("attachments") or []
        if _is_code_related(prompt, attachments):
            print(json.dumps({"additional_context": _load_gitnexus_context()}))
        else:
            print("{}")
        return

    print("{}")


if __name__ == "__main__":
    main()
