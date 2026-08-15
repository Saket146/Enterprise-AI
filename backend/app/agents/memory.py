import json
import logging
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
    def __init__(self):
        self._fallback_store = {}
        try:
            self.redis = get_redis_client()
            # Test connection
            self.redis.ping()
            self.online = True
            logger.info("Redis short-term memory manager initialized online.")
        except Exception as e:
            self.online = False
            logger.warning(f"Redis is offline. Activating local in-memory session store fallback. Error: {e}")

    def get_history(self, session_id: int) -> List[Dict[str, Any]]:
        """Fetch short-term chat messages from Redis list, or local store if offline."""
        key = f"chat_session:{session_id}:history"
        if self.online:
            try:
                raw_msgs = self.redis.lrange(key, 0, -1)
                return [json.loads(m) for m in raw_msgs]
            except Exception as e:
                logger.error(f"Redis memory read failed for session {session_id}, reading local fallback: {e}")
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
        if self.online:
            try:
                self.redis.rpush(key, json.dumps(msg))
                self.redis.expire(key, 604800) # Keep for 7 days
            except Exception as e:
                logger.error(f"Redis memory save failed for session {session_id}, saving locally: {e}")
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
        if not self.online:
            return
            
        try:
            from app.services.pipeline_service import ingestion_pipeline
            
            content = f"Decision Topic: {topic}\nDetails: {decision_details}"
            vector = ingestion_pipeline.model.encode(content).tolist()
            
            pt_id = f"dec-{session_id}-{int(datetime.utcnow().timestamp())}"
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
