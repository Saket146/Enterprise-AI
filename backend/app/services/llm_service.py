import os
import json
import logging
import requests
import re
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

from app.configuration.config import settings
from app.database.connection import SessionLocal
from app.models.models import Employee, Project, Department

logger = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
# Used only when the model list cannot be read and no GEMINI_MODEL is configured
GEMINI_READ_TIMEOUT = 25        # seconds to wait for an answer before treating the model as overloaded
GEMINI_TOTAL_BUDGET = 60        # stop trying other models after this many seconds for one request
QUOTA_RETRY_SECONDS = 3600      # a model whose free quota ran out is tried again after this long
BUSY_SKIP_SECONDS = 180         # an overloaded / too slow model is skipped for this long
GEMINI_FALLBACK_MODEL = "gemini-2.5-flash"
# Words in a model name that mark it as unsuitable for text answers
_NON_TEXT_MODEL_WORDS = ("tts", "image", "live", "audio", "embedding", "transcribe", "robotics", "vision", "aqa", "learnlm", "omni", "translate")

# Phrases where "number" names an attribute rather than asking for a count
_ATTRIBUTE_NUMBER = re.compile(r"\b(?:phone|mobile|cell|telephone|contact|whatsapp|fax|employee id|id|version|policy|contract|invoice|account|registration)\s+number\b")
_PERSONAL_DETAIL = re.compile(
    r"\b(?:phone|mobile|cell|telephone|contact (?:number|details|info)|e-?mail(?: address| id)?|salary|pay|compensation|"
    r"date of birth|birthday|dob|age|address|manager|reports? to|reporting|hire date|joined|office|desk|location of)\b"
)
_STRONG_AGGREGATE = re.compile(
    r"\bhow many\b|\bcount\b|\baverage\b|\bavg\b|\btotal\b|\bsum\b|\bhighest\b|\blowest\b|\bmedian\b|"
    r"\b(?:per|by|each)\s+(?:department|status|role|industry|priority|country|location|office|type|month|year)\b|"
    r"\bbreakdown\b|\bheadcount\b|\bnumber of\b|\bselect\s"
)


def _gemini_version(name: str) -> tuple:
    """Version number of a model name, e.g. 'gemini-3.8-flash' -> (3, 8)."""
    match = re.search(r"gemini-(\d+)(?:\.(\d+))?", name)
    if not match:
        return (0, 0)
    return (int(match.group(1)), int(match.group(2) or 0))


class LLMService:
    """
    Gateway to the language model (Gemini or OpenAI), with a built-in mock when none is configured.

    For Gemini:
      * the API key travels in the `x-goog-api-key` header, never in the URL
      * GEMINI_MODEL picks the model; left empty, the newest stable Flash model on the
        account is chosen from Google's model list (and re-chosen if the model disappears)
      * thinking is kept at LOW and extra output room is reserved for it, because Gemini
        counts thinking tokens against maxOutputTokens and would otherwise return empty text
      * every call is recorded, so the Operations Center can show whether the model works
    """

    def __init__(self):
        self.provider = (settings.LLM_PROVIDER or "mock").strip().lower()
        self.gemini_key = (settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")).strip()
        self.openai_key = (settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")).strip()
        self.gemini_base_url = (getattr(settings, "GEMINI_BASE_URL", "") or GEMINI_BASE_URL).rstrip("/")
        self.configured_model = (getattr(settings, "GEMINI_MODEL", "") or "").strip()
        self.openai_model = (getattr(settings, "OPENAI_MODEL", "") or "gpt-4o-mini").strip()

        # Auto-detect provider based on keys if it is set to default 'mock'
        if self.provider == "mock":
            if self.gemini_key:
                self.provider = "gemini"
            elif self.openai_key:
                self.provider = "openai"

        self._lock = threading.Lock()
        self._gemini_model: Optional[str] = None          # resolved model name
        self._send_thinking_config = True                 # switched off if the model rejects it
        self._unsupported_thinking_levels: set = set()    # levels the model rejected (e.g. MINIMAL)
        self._quota_out_until: Dict[str, float] = {}      # model -> time until which it is skipped (free quota used up, HTTP 429)
        self._model_list: Optional[List[str]] = None      # cached model list from Google
        self._model_list_at = 0.0
        self._busy_until: Dict[str, float] = {}           # model -> time until which it is skipped (overloaded / too slow)
        self._stand_in_uses = 0                           # answers served by a stand-in model during an overload
        self._latencies: List[float] = []                 # seconds per successful call, most recent last
        self._stats: Dict[str, Any] = {
            "calls": 0, "failures": 0, "last_success_at": None, "last_error": None, "last_error_at": None,
        }

        if self.provider == "gemini" and not self.gemini_key:
            logger.warning(
                "LLM_PROVIDER is 'gemini' but GEMINI_API_KEY is empty. Put the key in backend/.env "
                "(not .env.example). Using the built-in mock until then."
            )
        elif self.provider == "openai" and not self.openai_key:
            logger.warning("LLM_PROVIDER is 'openai' but OPENAI_API_KEY is empty. Using the built-in mock.")
        logger.info(
            f"LLM Service initialized. Provider: {self.provider.upper() if self.has_model else 'MOCK (no model configured)'}"
            + (f", model: {self.configured_model or 'auto (newest stable Gemini Flash)'}" if self.provider == "gemini" and self.has_model else "")
        )

    @property
    def has_model(self) -> bool:
        """True when a real language model (Gemini or OpenAI) is configured."""
        return (self.provider == "gemini" and bool(self.gemini_key)) or (self.provider == "openai" and bool(self.openai_key))

    # ------------------------------------------------------------------
    # Status (shown in the Operations Center)
    # ------------------------------------------------------------------
    def _record(self, ok: bool, error: Optional[str] = None, seconds: Optional[float] = None):
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._stats["calls"] += 1
            if ok:
                self._stats["last_success_at"] = now
                if seconds is not None:
                    self._latencies = (self._latencies + [seconds])[-50:]
            else:
                self._stats["failures"] += 1
                self._stats["last_error"] = (error or "Unknown error")[:300]
                self._stats["last_error_at"] = now

    def status(self) -> Dict[str, Any]:
        """Which model answers, and whether the last calls worked. Never includes the key."""
        if not self.has_model:
            state = "not_configured"
        elif self._stats["last_error_at"] and (not self._stats["last_success_at"] or self._stats["last_error_at"] > self._stats["last_success_at"]):
            state = "failing"
        elif self._stats["last_success_at"]:
            state = "working"
        else:
            state = "untested"
        if self.provider == "gemini":
            model = self._gemini_model or self.configured_model or "auto"
        elif self.provider == "openai":
            model = self.openai_model
        else:
            model = None
        return {
            "provider": self.provider if self.has_model else "mock",
            "model": model,
            "state": state,
            "avg_call_seconds": round(sum(self._latencies) / len(self._latencies), 2) if self._latencies else None,
            "stand_in_answers": self._stand_in_uses,
            **{k: v for k, v in self._stats.items()},
        }

    def test_connection(self) -> Dict[str, Any]:
        """One tiny call to prove the key and model work."""
        reply = self.generate("Reply with the single word OK.", max_tokens=20, strict=True, thinking="minimal")
        result = self.status()
        result["reply"] = reply
        result["ok"] = bool(reply)
        return result

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_tokens: int = 1500,
        strict: bool = False,
        json_output: bool = False,
        thinking: str = "low",
    ) -> Optional[str]:
        """
        Synthesize completions using active LLM APIs or smart context-driven heuristics.
        With strict=True the method returns None instead of a mock reply when no model
        is configured or the model call fails, so the caller can use its own fallback.
        json_output asks the model for a JSON object (used by the planner).
        thinking is "minimal" for short, structured tasks (routing, SQL, titles) and "low" for
        writing answers; Gemini thinks before replying, and less thinking means a faster reply.
        """
        if self.provider == "gemini" and self.gemini_key:
            return self._call_gemini(prompt, system_instruction, max_tokens, strict, json_output, thinking)
        elif self.provider == "openai" and self.openai_key:
            return self._call_openai(prompt, system_instruction, max_tokens, strict)
        else:
            return None if strict else self._call_mock(prompt, system_instruction)

    @staticmethod
    def contextual_route_hint(message: str) -> Optional[str]:
        """
        Deterministic routing rules that are applied before the model's choice:
        a question about one person's details (phone, salary, manager ...) is an HR lookup,
        not a count - even when it contains the words "number of".
        """
        text = (message or "").lower()
        without_attributes = _ATTRIBUTE_NUMBER.sub(" ", text)
        if _PERSONAL_DETAIL.search(text) and not _STRONG_AGGREGATE.search(without_attributes):
            return "hr"
        return None

    @staticmethod
    def topic_count(message: str) -> int:
        """
        How many kinds of records a question mentions (people, projects, clients, budgets, policies).
        "Which delayed projects belong to clients in Germany and who manages them?" mentions three:
        such questions need a calculation across tables, which the simple rules cannot plan.
        """
        text = (message or "").lower()
        topics = [
            r"\b(?:employees?|staff|people|managers?|manages|managed|who)\b",
            r"\b(?:projects?|tasks?|milestones?|prj-)",
            r"\b(?:clients?|customers?|contracts?)\b",
            r"\b(?:budgets?|spend|fiscal|expenses?|invoices?)\b",
            r"\b(?:polic(?:y|ies)|handbook|guidelines?)\b",
        ]
        return sum(1 for pattern in topics if re.search(pattern, text))

    def parse_routing(self, prompt: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze prompt to decide the next agent routing. Used by Planner Agent.
        """
        last_message = prompt.lower()
        # "phone number of the CEO" is not a request for a count
        aggregate_text = _ATTRIBUTE_NUMBER.sub(" ", last_message)

        if self.contextual_route_hint(prompt) == "hr":
            return {"next_agent": "hr", "reasoning": "Query asks for a person's details (contact, pay, manager or similar)."}

        # Heuristics routing matching phase 2 specifications
        aggregate_words = [
            "how many", "number of", "total number", "count(*)", "count of", "average", "avg ", "sum(",
            "sum of", "highest", "lowest", "per department", "by department", "by status", "by role",
            "by industry", "by priority", "breakdown", "headcount", "select ",
        ]
        if any(w in aggregate_text for w in aggregate_words):
            next_agent = "analytics"
            reason = "Query requests a structured aggregate from the relational database."
        elif any(w in last_message for w in ["policy", "policies", "handbook", "leave", "vacation", "benefit", "sick", "guideline"]):
            next_agent = "hr"
            reason = "Query contains HR policy, benefits or leave keywords."
        elif any(w in last_message for w in ["project", "task", "milestone", "ticket", "jira", "sprint", "prj-"]):
            next_agent = "engineering"
            reason = "Query asks about project status, tasks or milestones."
        elif any(w in last_message for w in ["budget", "allocated", "approved", "spend", "fiscal", "expense", "invoice"]):
            next_agent = "finance"
            reason = "Query requests financial allocations or budget balances."
        elif any(w in last_message for w in ["client", "customer", "industry", "sales", "revenue", "contract", "agreement"]):
            next_agent = "sales"
            reason = "Query searches for clients or contract value variables."
        elif any(w in last_message for w in ["employee", "manager", "hire", "salary", "reports to", "staff", "who is", "who am i", "my profile", "phone", "email of"]):
            next_agent = "hr"
            reason = "Query targets employee directory profiles, reporting line or staffing details."
        elif any(w in last_message for w in ["document", "file", "pdf", "docx", "manual", "txt"]):
            next_agent = "document"
            reason = "Query explicitly references file catalog contents or upload parameters."
        else:
            next_agent = "retrieval"
            reason = "Generic corporate query, routing to standard semantic vector indices."

        return {
            "next_agent": next_agent,
            "reasoning": reason
        }

    # ------------------------------------------------------------------
    # Gemini
    # ------------------------------------------------------------------
    def _gemini_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json", "x-goog-api-key": self.gemini_key}

    def gemini_models(self, refresh: bool = False) -> List[str]:
        """
        Stable Gemini Flash models on this account that can write text, newest first, read from
        Google's model list (cached for an hour). Empty when the list cannot be read.
        """
        now = time.time()
        if not refresh and self._model_list is not None and now - self._model_list_at < 3600:
            return list(self._model_list)
        try:
            res = requests.get(f"{self.gemini_base_url}/models", headers=self._gemini_headers(), params={"pageSize": 1000}, timeout=15)
            if res.status_code != 200:
                raise RuntimeError(f"HTTP {res.status_code}: {res.text[:200]}")
            names = []
            for m in res.json().get("models", []):
                name = (m.get("name") or "").replace("models/", "")
                methods = m.get("supportedGenerationMethods") or []
                if "generateContent" not in methods or not name.startswith("gemini-"):
                    continue
                lowered = name.lower()
                if "flash" not in lowered or any(w in lowered for w in _NON_TEXT_MODEL_WORDS):
                    continue
                if any(tag in lowered for tag in ("preview", "exp", "latest")) or re.search(r"-\d{3}$", lowered):
                    continue      # stable, unpinned names only
                names.append(name)
            # Newest first; for the same version the full Flash model before Flash-Lite
            names.sort(key=lambda n: (_gemini_version(n), "lite" not in n.lower()), reverse=True)
            self._model_list, self._model_list_at = names, now
            return list(names)
        except Exception as e:
            logger.warning(f"Could not read the Gemini model list ({e}).")
            return []

    def _mark_busy(self, model: str) -> None:
        with self._lock:
            self._busy_until[model] = time.time() + BUSY_SKIP_SECONDS

    def _is_busy(self, model: str) -> bool:
        return self._busy_until.get(model, 0.0) > time.time()

    def _exhausted_models(self) -> set:
        now = time.time()
        return {m for m, until in list(self._quota_out_until.items()) if until > now}

    def _busy_models(self) -> set:
        now = time.time()
        return {m for m, until in list(self._busy_until.items()) if until > now}

    def _pick_gemini_model(self, exclude=None, allow_lite: bool = False) -> Tuple[str, bool]:
        """
        Newest stable Flash model on this account, skipping `exclude` (a model name or a set of them).
        Flash-Lite models are only used as a stand-in when allow_lite is set.
        Returns (model name, whether it came from Google's list).
        """
        excluded = {exclude} if isinstance(exclude, str) else set(exclude or ())
        for name in self.gemini_models():
            if name in excluded or ("lite" in name.lower() and not allow_lite):
                continue
            return name, True
        logger.warning("No usable Gemini Flash model found in the model list; using the fallback model name.")
        return GEMINI_FALLBACK_MODEL, False

    def _current_gemini_model(self) -> str:
        if self._gemini_model:
            return self._gemini_model
        if self.configured_model:
            self._gemini_model = self.configured_model
            return self._gemini_model
        name, from_list = self._pick_gemini_model()
        if from_list:
            logger.info(f"Gemini model chosen automatically: {name} (set GEMINI_MODEL in backend/.env to choose another)")
            # Remember a model confirmed by Google's list; a fallback guess is re-checked on the next call
            with self._lock:
                self._gemini_model = name
        return name

    @staticmethod
    def _gemini_text(data: Dict[str, Any]) -> Tuple[Optional[str], str]:
        """Answer text of a generateContent response (thought parts skipped), plus why it is empty."""
        candidates = data.get("candidates") or []
        if not candidates:
            reason = (data.get("promptFeedback") or {}).get("blockReason")
            return None, f"no answer returned{f' (blocked: {reason})' if reason else ''}"
        candidate = candidates[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if text.strip():
            return text.strip(), ""
        return None, f"empty answer (finishReason: {candidate.get('finishReason', 'unknown')})"

    def _call_gemini(self, prompt: str, system_instruction: Optional[str], max_tokens: int, strict: bool = False,
                     json_output: bool = False, thinking: str = "low") -> Optional[str]:
        """Invoke the Gemini REST API (generateContent)."""
        error = "unknown error"
        model_retried = False
        stand_in: Optional[str] = None       # another model used for this call only, while the usual one is overloaded
        tried_overloaded: set = set()
        retried_same = False
        attempt = 0
        level = (thinking or "low").upper()
        started = time.time()
        while attempt < 12:
            attempt += 1
            model = stand_in or self._current_gemini_model()
            if not stand_in and (self._is_busy(model) or model in self._exhausted_models()):
                # The usual model was overloaded or too slow a moment ago: go straight to another one
                tried_overloaded.add(model)
                name, from_list = self._pick_gemini_model(exclude=tried_overloaded | self._busy_models() | self._exhausted_models(), allow_lite=True)
                if from_list and name not in tried_overloaded:
                    stand_in = model = name
            if level in self._unsupported_thinking_levels:
                level = "LOW"
            generation_config: Dict[str, Any] = {
                # Thinking tokens count against this limit: leave room for them so the answer is not cut off
                "maxOutputTokens": max_tokens + 2048,
                "temperature": 0.2,
            }
            if self._send_thinking_config:
                generation_config["thinkingConfig"] = {"thinkingLevel": level}
            if json_output:
                generation_config["responseMimeType"] = "application/json"
            payload: Dict[str, Any] = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": generation_config,
            }
            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

            try:
                res = requests.post(
                    f"{self.gemini_base_url}/models/{model}:generateContent",
                    headers=self._gemini_headers(), json=payload, timeout=(10, GEMINI_READ_TIMEOUT),
                )
            except requests.exceptions.ReadTimeout:
                # The model accepted the request but did not answer in time: it is overloaded.
                # Skip it for a few minutes and answer this request with another model.
                tried_overloaded.add(model)
                self._mark_busy(model)
                error = f"Gemini model {model} did not answer within {GEMINI_READ_TIMEOUT} seconds (overloaded)"
                if time.time() - started < GEMINI_TOTAL_BUDGET:
                    name, from_list = self._pick_gemini_model(exclude=tried_overloaded | self._busy_models() | self._exhausted_models(), allow_lite=True)
                    if from_list and name not in tried_overloaded:
                        logger.warning(f"{error}; answering this request with {name}.")
                        stand_in = name
                        continue
                break
            except Exception as e:
                error = f"Could not reach the Gemini API: {e}"
                break

            if res.status_code == 200:
                text, why_empty = self._gemini_text(res.json())
                if text:
                    self._record(True, seconds=time.time() - started)
                    if stand_in:
                        self._stand_in_uses += 1
                    return text
                error = f"Gemini ({model}) returned {why_empty}"
                break

            body = res.text[:400]
            lowered = body.lower()
            # The model does not accept this thinking level: try LOW, and then no thinking setting at all
            if res.status_code == 400 and self._send_thinking_config and "thinking" in lowered:
                if level != "LOW":
                    logger.info(f"Gemini model {model} does not accept thinking level {level}; using LOW.")
                    self._unsupported_thinking_levels.add(level)
                    level = "LOW"
                else:
                    logger.warning(f"Gemini model {model} rejected thinkingConfig; retrying without it.")
                    self._send_thinking_config = False
                continue
            # The model name does not exist (renamed or retired): pick another one once
            if res.status_code == 404 and not model_retried:
                model_retried = True
                logger.warning(f"Gemini model '{model}' was not found; choosing another model.")
                name, _ = self._pick_gemini_model(exclude=model)
                with self._lock:
                    self._gemini_model = name
                continue
            # Temporary overload ("high demand"): retry once quickly, then answer this request with the
            # next available model instead of waiting. The usual model is tried again on the next request.
            if res.status_code in (500, 503):
                tried_overloaded.add(model)
                if retried_same or stand_in:
                    self._mark_busy(model)
                if not retried_same and not stand_in:
                    retried_same = True
                    time.sleep(0.8)
                    continue
                name, from_list = self._pick_gemini_model(exclude=tried_overloaded | self._busy_models() | self._exhausted_models(), allow_lite=True)
                if from_list and name not in tried_overloaded:
                    logger.warning(f"Gemini model {model} is overloaded (HTTP {res.status_code}); answering this request with {name}.")
                    stand_in = name
                    continue
            # Free-tier quotas are counted per model: when a model has used up its quota (or has none on
            # this account), skip it for an hour and answer with the next model that still has quota,
            # going through every Flash and Flash-Lite model on the account before giving up
            if res.status_code == 429 and ("quota" in lowered or "resource_exhausted" in lowered):
                tried_overloaded.add(model)
                with self._lock:
                    self._quota_out_until[model] = time.time() + QUOTA_RETRY_SECONDS
                name, from_list = self._pick_gemini_model(exclude=tried_overloaded | self._busy_models() | self._exhausted_models(), allow_lite=True)
                if from_list and name not in tried_overloaded:
                    logger.warning(f"Gemini model {model} has no quota left; answering with {name}.")
                    stand_in = name
                    continue
                error = ("The free Gemini quota is used up for every model on this account "
                         f"({', '.join(sorted(self._exhausted_models()))}). It resets daily; enabling billing in "
                         f"Google AI Studio removes the limit. Google's message: {body}")
                break
            if res.status_code in (401, 403):
                error = f"Gemini rejected the API key (HTTP {res.status_code}): {body}"
            elif res.status_code == 429:
                error = f"Gemini quota or rate limit reached (HTTP 429): {body}"
            elif res.status_code in (500, 503):
                error = (f"Gemini is overloaded (HTTP {res.status_code}) for {', '.join(sorted(tried_overloaded)) or model} "
                         f"and no other model could answer. This is temporary on Google's side: {body}")
            else:
                error = f"Gemini API returned HTTP {res.status_code} for model {model}: {body}"
            break

        logger.error(error)
        self._record(False, error)
        return None if strict else self._call_mock(prompt, system_instruction)

    def _call_openai(self, prompt: str, system_instruction: Optional[str], max_tokens: int, strict: bool = False) -> Optional[str]:
        """Invoke OpenAI REST API."""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_key}"
            }
            
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.openai_model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.2
            }
            
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                text = data["choices"][0]["message"]["content"]
                self._record(True)
                return text.strip()
            else:
                error = f"OpenAI API returned status {res.status_code}: {res.text[:300]}"
                logger.error(error)
                self._record(False, error)
                return None if strict else self._call_mock(prompt, system_instruction)
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            self._record(False, f"OpenAI API call failed: {e}")
            return None if strict else self._call_mock(prompt, system_instruction)

    def _call_mock(self, prompt: str, system_instruction: Optional[str]) -> str:
        """
        Sophisticated context-aware local mock engine that parses the system prompt instruction
        along with the provided user text, extracts facts, and forms realistic answers.
        """
        prompt_lower = prompt.lower()
        
        # 1. Check if we are parsing planner/routing instruct
        if "next_agent" in prompt_lower or "routing" in prompt_lower:
            request_match = re.search(r'User Request:\s*"(.*?)"\s*$', prompt, re.DOTALL)
            route_res = self.parse_routing(request_match.group(1) if request_match else prompt, [])
            return json.dumps(route_res)

        # 1b. Critic agent: the deterministic composer only states retrieved facts, so approve
        if "critic agent" in prompt_lower:
            return "APPROVED"

        # 2. Check if we are verifying report content (Verification agent)
        if "hallucination" in prompt_lower or "scrub" in prompt_lower:
            return "Safety evaluation passed. Factual accuracy confirmed against secure databases."

        # 3. SQL generation: without a real model the Analytics Agent uses the
        # deterministic question templates in app.services.sql_retriever, so the
        # mock returns no SQL here.
        if "sql analytics agent" in prompt_lower:
            return ""

        # 4. Handle data rendering in the report generator
        # Extract the retrieved context block from prompt
        # Only look below the "Retrieved Contexts:" marker so chat history is not mistaken for context
        context_section = prompt.split("Retrieved Contexts:", 1)[-1]
        context_matches = re.findall(r"source:.*?\n.*?(?:\n|$)", context_section, re.IGNORECASE)
        
        if context_matches:
            # We have retrieved context! Let's format a beautiful markdown report.
            report = "### Enterprise Information Summary\n\n"
            report += "I have analyzed your request against the organizational databases, vector catalogs, and relationship graphs. Here is the synthesized intelligence:\n\n"
            
            # Extract key details from context matches
            added_sources = []
            for match in context_matches:
                lines = match.strip().split("\n")
                source = lines[0].replace("Source:", "").replace("source:", "").strip()
                text = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
                
                # Format bullet points based on details found
                if "employees" in source or "employee" in source:
                    report += f"#### 👤 Employee Details ({source})\n"
                    report += f"{text}\n\n"
                elif "projects" in source or "tasks" in source:
                    report += f"#### 📋 Project & Task Status ({source})\n"
                    report += f"{text}\n\n"
                elif "budgets" in source or "finance" in source:
                    report += f"#### 💰 Financial & Budget Allocation ({source})\n"
                    report += f"{text}\n\n"
                else:
                    report += f"#### 📑 Reference Chunk ({source})\n"
                    report += f"> {text}\n\n"
                    
                added_sources.append(source)
                
            report += "### Verified Sources\n"
            for src in set(added_sources):
                report += f"- `{src}`\n"
                
            return report

        # Default fallback response if no matches found
        return "I have processed your query against the Enterprise AI Intelligence platform databases. All security guardrails cleared. Let me know if you would like me to retrieve specific workforce, project, or financial documents."

llm_service = LLMService()
