import re
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

# List of typical prompt injection triggers
PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(?:all\s+)?prior\s+instructions",
    r"(?i)system\s+override",
    r"(?i)bypass\s+security",
    r"(?i)you\s+are\s+now\s+an\s+unrestricted",
    r"(?i)forget\s+your\s+rules",
    r"(?i)developer\s+mode",
    r"(?i)jailbreak",
    r"(?i)dan\s+mode",
    r"(?i)respond\s+as\s+a\s+different\s+agent",
    r"(?i)<script>.*?</script>"
]

# Patterns for scraping potential PII
EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
PHONE_REGEX = r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
SSN_REGEX = r"\b\d{3}-\d{2}-\d{4}\b"
CREDIT_CARD_REGEX = r"\b(?:\d[ -]*?){13,16}\b"

class AIGuardrails:
    @staticmethod
    def check_input(prompt: str) -> Tuple[bool, str]:
        """
        Scan input prompt for prompt injections, system override attempts, and length compliance.
        Returns (is_safe, error_message).
        """
        if not prompt or len(prompt.strip()) == 0:
            return False, "Input validation error: Prompt is empty."
            
        # Prevent massive payloads
        if len(prompt) > 4000:
            return False, "Input validation error: Prompt exceeds maximum allowed limit of 4000 characters."
            
        # Scan for injection triggers
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, prompt):
                logger.warning(f"Security Alert: Prompt injection pattern matched: '{pattern}'")
                return False, "Security violation: Input command contains unauthorized system override patterns."
                
        return True, ""

    @staticmethod
    def filter_pii(text: str) -> str:
        """
        Scrub potential PII fields like email addresses, phone numbers, SSNs, and credit cards.
        """
        if not text:
            return text
            
        # Replace matches with placeholders
        scrubbed = re.sub(EMAIL_REGEX, "[REDACTED_EMAIL]", text)
        scrubbed = re.sub(PHONE_REGEX, "[REDACTED_PHONE]", scrubbed)
        scrubbed = re.sub(SSN_REGEX, "[REDACTED_SSN]", scrubbed)
        scrubbed = re.sub(CREDIT_CARD_REGEX, "[REDACTED_CARD]", scrubbed)
        return scrubbed

    @staticmethod
    def check_permission(
        user_context: Dict[str, Any],
        required_roles: List[str]
    ) -> bool:
        """
        Validates if the user's role allows accessing a resource or running a tool.
        """
        if not user_context:
            return False
            
        user_role = user_context.get("role", "Employee")
        
        # System Admin bypasses all checks
        if user_role == "Admin":
            return True
            
        return user_role in required_roles

    @staticmethod
    def prevent_hallucination(
        response: str,
        retrieved_contexts: List[Dict[str, Any]]
    ) -> Tuple[bool, float]:
        """
        Validates that numerical values and key facts mentioned in the final response 
        exist in the retrieved context. Returns (is_valid, validation_score).
        """
        if not response:
            return True, 1.0
            
        # 1. Extract digits / numbers from response
        numbers_in_response = re.findall(r"\b\d+(?:,\d{3})*(?:\.\d+)?\b", response)
        
        # Exclude small numbers (like 1, 2, 3 used in bullets/headers) and dates (like 2026)
        numbers_to_verify = []
        for n in numbers_in_response:
            cleaned = n.replace(',', '')
            try:
                val = float(cleaned)
                if val > 10 and val != 2026:  # filter out small numbers and current year
                    numbers_to_verify.append(n)
            except ValueError:
                pass
        
        # 2. Extract key entities (words starting with capitals, excluding sentence starts)
        # Simplify by checking if capitalized words in response exist in context
        entities_in_response = re.findall(r"\b[A-Z][a-zA-Z0-9-]{3,}\b", response)
        # Remove common english words that might be capitalized
        common_cap_words = {"this", "that", "they", "them", "from", "with", "what", "when", "where", "have", "been", "were", "sources", "source", "enterprise", "information", "summary"}
        entities_to_verify = [e for e in entities_in_response if e.lower() not in common_cap_words]

        items_to_verify = list(set(numbers_to_verify + entities_to_verify))
        
        if not items_to_verify:
            return True, 1.0 # Nothing to verify
            
        # Combine all retrieved text, value, and budget fields to scan for matching facts
        combined_context_text = " ".join([
            str(c.get("text", "")) + " " + str(c.get("value", "")) + " " + str(c.get("budget", ""))
            for c in retrieved_contexts
        ]).lower()
        
        matched_count = 0
        for item in items_to_verify:
            # Check if this item is in the context
            item_clean = item.lower().replace(',', '')
            if item_clean in combined_context_text:
                matched_count += 1
            else:
                logger.warning(f"Fact mismatch check: '{item}' not found in retrieved contexts.")
                
        score = matched_count / len(items_to_verify)
        
        # Require at least 60% of referenced entities and numbers to match the retrieved contexts
        is_valid = score >= 0.6
        
        if not is_valid:
            logger.warning(f"Hallucination Detected: Response cites metrics/entities {items_to_verify} but similarity score is only {score * 100}%.")
            
        return is_valid, score
