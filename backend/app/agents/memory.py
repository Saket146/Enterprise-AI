import json
import logging
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.database.connection import get_redis_client, get_qdrant_client
from qdrant_client.http import models as qmodels

logger = logging.getLogger(__name__)

class RedisShortTermMemory:
    """
    Manages short-term conversation logs inside Redis to support quick agent memory retrieval.
    Includes in-memory local dict fallbacks to prevent crashes if Redis is offline.
    """
    RETRY_SECONDS = 300   # a refused connection can take ~2 s on Windows; do not retry on every message
    MAX_MESSAGES = 40  # keep the most recent turns only

    def __init__(self):
        self._fallback_store = {}
        self.redis = None
        self.online = False
        self._next_retry = 0.0
        self._connect()

    def _connect(self) -> bool:
        """(Re)connect to Redis. Called at startup and again later if Redis was offline."""
        try:
            self.redis = get_redis_client()
            self.redis.ping()
            if not self.online:
                logger.info("Redis short-term memory manager initialized online.")
            self.online = True
        except Exception as e:
            self.online = False
            self._next_retry = time.time() + self.RETRY_SECONDS
            logger.warning(f"Redis is offline. Activating local in-memory session store fallback. Error: {e}")
        return self.online

    def _ensure_online(self) -> bool:
        """Redis started after the API did? Pick it up without a restart."""
        if not self.online and time.time() >= self._next_retry:
            self._connect()
        return self.online

    def clear(self, session_id: int):
        """Forget a chat session (called when the chat is deleted)."""
        key = f"chat_session:{session_id}:history"
        self._fallback_store.pop(key, None)
        if self._ensure_online():
            try:
                self.redis.delete(key)
            except Exception as e:
                logger.error(f"Redis memory delete failed for session {session_id}: {e}")

    def get_history(self, session_id: int) -> List[Dict[str, Any]]:
        """Fetch short-term chat messages from Redis list, or local store if offline."""
        key = f"chat_session:{session_id}:history"
        if self._ensure_online():
            try:
                raw_msgs = self.redis.lrange(key, -self.MAX_MESSAGES, -1)
                return [json.loads(m) for m in raw_msgs]
            except Exception as e:
                logger.error(f"Redis memory read failed for session {session_id}, reading local fallback: {e}")
                self.online = False
                self._next_retry = time.time() + self.RETRY_SECONDS
                return self._fallback_store.get(key, [])
        else:
            return self._fallback_store.get(key, [])

    def add_message(self, session_id: int, role: str, content: str):
        """Append message to Redis history list and set expiration, or save locally if offline."""
        key = f"chat_session:{session_id}:history"
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        if self._ensure_online():
            try:
                self.redis.rpush(key, json.dumps(msg))
                self.redis.ltrim(key, -self.MAX_MESSAGES, -1)
                self.redis.expire(key, 604800) # Keep for 7 days
            except Exception as e:
                logger.error(f"Redis memory save failed for session {session_id}, saving locally: {e}")
                self.online = False
                self._next_retry = time.time() + self.RETRY_SECONDS
                if key not in self._fallback_store:
                    self._fallback_store[key] = []
                self._fallback_store[key].append(msg)
        else:
            if key not in self._fallback_store:
                self._fallback_store[key] = []
            self._fallback_store[key].append(msg)


class LongTermMemoryManager:
    """
    Manages long-term vector database caches inside Qdrant and relational database history.
    """
    def __init__(self):
        try:
            self.qdrant = get_qdrant_client()
            self.online = True
        except Exception as e:
            self.online = False
            logger.warning(f"Qdrant client offline. Skipping long-term vector memory indexes. Error: {e}")

    @staticmethod
    def _chats_collection_ready() -> bool:
        """True when Qdrant is reachable and the 'chats' collection exists (checked without loading the embedding model)."""
        try:
            from app.services.rag_service import rag_service
            return "chats" in rag_service._qdrant_collections()
        except Exception:
            return False

    def forget_session(self, session_id: int):
        """Remove everything remembered about a deleted chat from the Qdrant 'chats' collection."""
        if not self.online or not self._chats_collection_ready():
            return
        try:
            self.qdrant.delete(
                collection_name="chats",
                points_selector=qmodels.FilterSelector(filter=qmodels.Filter(must=[
                    qmodels.FieldCondition(key="session_id", match=qmodels.MatchValue(value=session_id))
                ]))
            )
        except Exception as e:
            logger.error(f"Failed to remove chat {session_id} from long-term memory: {e}")

    def index_decision(
        self,
        session_id: int,
        employee_id: int,
        topic: str,
        decision_details: str
    ):
        """
        Create vector embedding of a key action/decision and index it in the Qdrant chats collection.
        Allows future RAG flows to remember past decisions.
        """
        if not self.online or not self._chats_collection_ready():
            return
            
        try:
            from app.services.pipeline_service import ingestion_pipeline
            
            content = f"Decision Topic: {topic}\nDetails: {decision_details}"
            vector = ingestion_pipeline.model.encode(content).tolist()
            
            pt_id = str(uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"decision-{session_id}-{time.time_ns()}"
            ))
            self.qdrant.upsert(
                collection_name="chats",
                points=[
                    qmodels.PointStruct(
                        id=pt_id,
                        vector=vector,
                        payload={
                            "text": content,
                            "session_id": session_id,
                            "employee_id": employee_id,
                            "title": f"Decision: {topic}",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                ]
            )
            logger.info(f"Long-term memory indexed decision for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to save long-term decision memory: {e}")

    def auto_detect_and_index(self, session_id: int, employee_id: int, user_message: str, response: str):
        """
        Scans both user message and response for indicators of corporate decisions,
        and indexes them automatically into long-term memory if found.
        """
        # Look for keywords indicating decision making
        decision_keywords = ["decided to", "approve", "approved", "assign", "assigned", "allocated", "agreed to", "hired", "terminated"]
        user_lower = user_message.lower()
        resp_lower = response.lower()
        
        matches_user = any(kw in user_lower for kw in decision_keywords)
        matches_resp = any(kw in resp_lower for kw in decision_keywords)
        
        if matches_user and matches_resp:
            # We found a potential corporate decision.
            topic = "Action / Corporate Decision details"
            # Extract main sentence
            sentences = response.split(".")
            details = sentences[0] if sentences else response
            self.index_decision(session_id, employee_id, topic, details)

short_term_memory = RedisShortTermMemory()
long_term_memory = LongTermMemoryManager()
