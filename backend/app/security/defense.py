"""Centralized request safety controls for user- and agent-supplied text.

Thin wrapper around app.agents.guardrails so the workflow API and the chat
agents enforce exactly the same prompt-injection and PII rules.
"""
import re
from dataclasses import dataclass

from app.agents.guardrails import AIGuardrails, PROMPT_INJECTION_PATTERNS

# Kept for backwards compatibility with code that imports this name.
INJECTION_PATTERNS = tuple(PROMPT_INJECTION_PATTERNS)


@dataclass
class SafetyResult:
    safe: bool
    sanitized: str
    reasons: list[str]


def inspect_prompt(text: str) -> SafetyResult:
    reasons = []
    if any(re.search(pattern, text or "") for pattern in PROMPT_INJECTION_PATTERNS):
        reasons.append("prompt_injection")
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text or ""):
        reasons.append("control_characters")
    return SafetyResult(not reasons, text, reasons)


def mask_sensitive_data(value: str) -> str:
    return AIGuardrails.filter_pii(value)
