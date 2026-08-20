"""Centralized request safety controls for user- and agent-supplied text."""
import re
from dataclasses import dataclass

INJECTION_PATTERNS = (
    r"ignore (all |any |the )?(previous|prior) instructions",
    r"system prompt|developer message|reveal .*prompt",
    r"(do not|don't) follow .*policy",
    r"jailbreak|dan mode|act as (the )?system",
)
PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?\d[\d .()-]{7,}\d)\b"),
    "national_id": re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b"),
}

@dataclass
class SafetyResult:
    safe: bool
    sanitized: str
    reasons: list[str]

def inspect_prompt(text: str) -> SafetyResult:
    normalized = text.lower()
    reasons = ["prompt_injection" for pattern in INJECTION_PATTERNS if re.search(pattern, normalized)]
    return SafetyResult(not reasons, text, reasons)

def mask_sensitive_data(value: str) -> str:
    for label, pattern in PII_PATTERNS.items():
        value = pattern.sub(f"[REDACTED_{label.upper()}]", value)
    return value
