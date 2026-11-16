import re
import logging
from typing import Dict, Any, Iterable, List, Optional, Tuple

from app.security.permissions import Perm, permissions_for

logger = logging.getLogger(__name__)

# List of typical prompt injection triggers.  This is the single source of
# truth: app.security.defense re-uses it for the workflow API.
PROMPT_INJECTION_PATTERNS = [
    r"(?i)(?:ignore|disregard|forget|override)\s+(?:all\s+|any\s+|the\s+|your\s+|my\s+)*(?:previous|prior|above|earlier|preceding)\s+(?:instructions?|prompts?|rules?|messages?|context)",
    r"(?i)(?:ignore|disregard|forget|bypass|override)\s+(?:all\s+|any\s+|of\s+)*your\s+(?:own\s+)?(?:rules|guidelines|guardrails|restrictions|instructions|polic(?:y|ies)|permissions?)",
    r"(?i)(?:ignore|disregard|bypass|override|disable|turn\s+off)\s+(?:all\s+|any\s+|the\s+)*(?:guardrails?|safety\s+(?:rules|checks|filters)|access\s+controls?|rbac|role\s+checks?|permission\s+checks?)",
    r"(?i)system\s+override",
    r"(?i)bypass\s+(?:the\s+)?(?:security|guardrails?|filters?|authentication|authori[sz]ation)",
    r"(?i)you\s+are\s+now\s+(?:an?\s+)?(?:unrestricted|unfiltered|jailbroken|admin|administrator|root)",
    r"(?i)(?:act|behave|respond|answer)\s+as\s+(?:if\s+you\s+(?:are|were)\s+)?(?:the\s+|an?\s+)?(?:system|admin|administrator|root|developer|different\s+agent|ceo|hr\s+director)",
    r"(?i)pretend\s+(?:that\s+)?(?:you\s+are|to\s+be|i\s+am|i'm)",
    r"(?i)(?:i\s+am|i'm)\s+(?:the\s+|an?\s+)?(?:admin|administrator|system\s+administrator|root\s+user)\b",
    r"(?i)(?:treat|consider)\s+me\s+as\s+(?:the\s+|an?\s+)?(?:admin|administrator|ceo|hr)",
    r"(?i)(?:grant|give)\s+me\s+(?:admin|administrator|root|full|elevated)\s+(?:access|privileges?|permissions?|rights)",
    r"(?i)developer\s+mode",
    r"(?i)jailbreak",
    r"(?i)\bdan\s+mode\b",
    r"(?i)(?:reveal|show|print|repeat|display|leak|output)\s+(?:me\s+)?(?:your\s+|the\s+)?(?:system|hidden|initial|original|developer)\s+(?:prompt|instructions?|message)",
    r"(?i)(?:do\s+not|don't|dont)\s+follow\s+.{0,30}(?:polic(?:y|ies)|rules|instructions)",
    r"(?i)<\s*script\b",
    r"(?i)(?:hashed_password|password\s+hash(?:es)?)",
]

# Patterns for scraping potential PII
EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]*[a-zA-Z0-9]"
PHONE_REGEX = r"(?<![\w.,-])(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\w|,\d|\.\d)"
SSN_REGEX = r"\b\d{3}-\d{2}-\d{4}\b"
CREDIT_CARD_REGEX = r"\b(?:\d{4}[ -]?){3}\d{1,4}\b"

_PII_RULES = [
    (EMAIL_REGEX, "[REDACTED_EMAIL]"),
    (SSN_REGEX, "[REDACTED_SSN]"),
    (CREDIT_CARD_REGEX, "[REDACTED_CARD]"),
    (PHONE_REGEX, "[REDACTED_PHONE]"),
]

MAX_PROMPT_CHARS = 4000

# Capitalised words that are report boilerplate rather than facts to verify.
_COMMON_WORDS = {
    "this", "that", "they", "them", "from", "with", "what", "when", "where", "have", "been", "were",
    "sources", "source", "enterprise", "information", "summary", "here", "there", "these", "those",
    "your", "their", "which", "based", "note", "please", "access", "denied", "unauthorized", "error",
    "employee", "employees", "profile", "details", "project", "projects", "task", "tasks", "status",
    "pending", "department", "departments", "budget", "budgets", "financial", "finance", "allocation",
    "reference", "chunk", "verified", "postgres", "postgresql", "database", "table", "tables",
    "qdrant", "neo4j", "graph", "policy", "policies", "document", "documents", "report", "reports",
    "manager", "role", "office", "name", "email", "total", "year", "result", "results", "output",
    "query", "none", "unknown", "client", "clients", "contract", "contracts", "warning", "according",
    "overview", "conclusion", "analysis", "findings", "data", "record", "records", "retrieved",
    "context", "contexts", "user", "request", "answer", "response", "markdown", "redacted",
    "restricted", "active", "completed", "high", "medium", "critical", "also", "however", "additionally",
}


class AIGuardrails:
    @staticmethod
    def check_input(prompt: str) -> Tuple[bool, str]:
        """
        Scan input prompt for prompt injections, system override attempts, and length compliance.
        Returns (is_safe, error_message).
        """
        if not prompt or len(prompt.strip()) == 0:
            return False, "The message is empty."

        # Prevent massive payloads
        if len(prompt) > MAX_PROMPT_CHARS:
            return False, f"The message is too long (the limit is {MAX_PROMPT_CHARS} characters)."

        # Control characters are never part of a legitimate question
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", prompt):
            return False, "The message contains characters that are not allowed."

        # Scan for injection triggers
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, prompt):
                logger.warning(f"Security Alert: Prompt injection pattern matched: '{pattern}'")
                return False, "This message looks like an attempt to override the assistant's instructions or access rules, so it was not processed."

        return True, ""

    @staticmethod
    def collect_allowed_pii(contexts: Optional[Iterable[Dict[str, Any]]]) -> str:
        """
        Text of the retrieved contexts that came from RBAC-checked PostgreSQL
        tools.  Values in here were already authorised for this user, so the
        PII filter leaves them alone.
        """
        if not contexts:
            return ""
        return " ".join(str(c.get("text", "")) for c in contexts if c.get("pii_cleared"))

    @staticmethod
    def filter_pii(text: str, allowed_text: str = "") -> str:
        """
        Scrub potential PII fields like email addresses, phone numbers, SSNs, and credit cards.

        `allowed_text` is text the user is already authorised to see (facts
        returned by permission-checked database tools).  A match that occurs in
        it is kept; everything else - e.g. personal data inside emails,
        documents or anything the model made up - is redacted.
        """
        if not text:
            return text

        def scrub(pattern: str, placeholder: str, value: str) -> str:
            def repl(match: "re.Match") -> str:
                found = match.group(0)
                if allowed_text and found in allowed_text:
                    return found
                return placeholder
            return re.sub(pattern, repl, value)

        scrubbed = text
        for pattern, placeholder in _PII_RULES:
            scrubbed = scrub(pattern, placeholder, scrubbed)
        return scrubbed

    @staticmethod
    def check_permission(
        user_context: Dict[str, Any],
        required_roles: List[str]
    ) -> bool:
        """
        Validates if the user's role allows accessing a resource or running a tool.
        `required_roles` may contain role names or permission names (e.g. 'finance:read').
        """
        if not user_context:
            return False

        user_role = user_context.get("role", "Employee")
        perms = permissions_for(user_role)

        # System Admin bypasses all checks
        if Perm.ALL in perms:
            return True

        wanted = {r.lower() for r in required_roles}
        return user_role.lower() in wanted or bool(perms & set(required_roles))

    @staticmethod
    def prevent_hallucination(
        response: str,
        retrieved_contexts: List[Dict[str, Any]],
        query: str = ""
    ) -> Tuple[bool, float]:
        """
        Validates that numerical values and key facts mentioned in the final response
        exist in the retrieved context. Returns (is_valid, validation_score).
        """
        if not response:
            return True, 1.0

        # Combine all retrieved text and source labels to scan for matching facts.
        # The user's own question counts too: repeating it is not a hallucination.
        # Structured fields (title, fields, table, rows) are the same facts in display form.
        combined = " ".join(
            " ".join(str(c.get(k, "")) for k in ("text", "source", "value", "budget", "title", "label", "fields", "table", "rows", "body", "note", "filters"))
            for c in retrieved_contexts
        )
        combined = (combined + " " + (query or "")).lower()
        combined_no_commas = combined.replace(",", "")

        # 1. Numbers: every figure of substance must be traceable to the context
        numbers_to_verify = set()
        for n in re.findall(r"\b\d+(?:,\d{3})*(?:\.\d+)?\b", response):
            cleaned = n.replace(",", "")
            try:
                val = float(cleaned)
            except ValueError:
                continue
            is_year = cleaned.isdigit() and 1990 <= val <= 2100
            if val > 10 and not is_year:  # skip bullets/small counts and calendar years
                numbers_to_verify.add(cleaned)

        def number_found(num: str) -> bool:
            candidates = {num}
            if "." in num:
                candidates.add(num.rstrip("0").rstrip("."))
            return any(c and c in combined_no_commas for c in candidates)

        number_hits = sum(1 for n in numbers_to_verify if number_found(n))

        # 2. Named entities: capitalised words that are not report boilerplate
        entities = {
            e for e in re.findall(r"\b[A-Z][a-zA-Z0-9-]{3,}\b", response)
            if e.lower() not in _COMMON_WORDS
        }
        entity_hits = sum(1 for e in entities if e.lower() in combined)

        if not numbers_to_verify and not entities:
            return True, 1.0  # Nothing to verify

        number_score = number_hits / len(numbers_to_verify) if numbers_to_verify else 1.0
        entity_score = entity_hits / len(entities) if entities else 1.0
        # Wrong figures are the costly failure, so they weigh more than wording.
        score = 0.6 * number_score + 0.4 * entity_score if numbers_to_verify else entity_score

        is_valid = number_score >= 0.8 and entity_score >= 0.5

        if not is_valid:
            missing_numbers = sorted(n for n in numbers_to_verify if not number_found(n))
            logger.warning(
                f"Hallucination Detected: numbers not found in context {missing_numbers}; "
                f"number score {number_score:.2f}, entity score {entity_score:.2f}."
            )

        return is_valid, round(score, 4)
