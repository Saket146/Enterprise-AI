import logging
import time
from typing import List, Dict, Any, Optional, Set
import numpy as np
from qdrant_client.http import models as qmodels

from app.database.connection import SessionLocal, get_qdrant_client, get_neo4j_driver
from app.observability import metrics
from app.security.permissions import Perm, can, document_access, policy_access
from app.services.pipeline_service import ingestion_pipeline
from app.services.sql_retriever import keywords, postgres_retriever

logger = logging.getLogger(__name__)

COLLECTIONS = ["documents", "policies", "emails", "meetings", "chats"]

# How long an unreachable store is skipped before it is tried again. A refused connection to
# localhost can take about 2 seconds on Windows, so retrying often would slow answers down.
OFFLINE_RETRY_SECONDS = 300

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate the cosine similarity between two vector lists."""
    arr1 = np.array(v1)
    arr2 = np.array(v2)
    norm1 = np.linalg.norm(arr1)
    norm2 = np.linalg.norm(arr2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(arr1, arr2) / (norm1 * norm2))

class RAGService:
    def __init__(self):
        self._qdrant_retry_at = 0.0
        self._neo4j_retry_at = 0.0
        self._known_collections: Set[str] = set()
        self._collections_checked_at = 0.0

    # ------------------------------------------------------------------
    # Availability (Qdrant and Neo4j are optional stores)
    # ------------------------------------------------------------------
    def _qdrant_collections(self) -> Set[str]:
        """Names of the collections that exist in Qdrant; empty set when Qdrant is unreachable."""
        now = time.time()
        if now < self._qdrant_retry_at:
            return set()
        if self._known_collections and now - self._collections_checked_at < 60:
            return self._known_collections
        try:
            res = get_qdrant_client().get_collections()
            self._known_collections = {c.name for c in res.collections}
            self._collections_checked_at = now
            return self._known_collections
        except Exception as e:
            self._qdrant_retry_at = now + OFFLINE_RETRY_SECONDS
            self._known_collections = set()
            metrics.increment("retrieval_failures")
            logger.warning(
                f"Qdrant is not reachable ({str(e).splitlines()[0][:120]}). Vector search is skipped for "
                f"{OFFLINE_RETRY_SECONDS}s; answers use PostgreSQL retrieval only."
            )
            return set()

    # ------------------------------------------------------------------
    # RBAC for vector search
    # ------------------------------------------------------------------
    def _access_conditions(self, collection_name: str, user_context: Optional[Dict[str, Any]]) -> Optional[list]:
        """
        Extra Qdrant filter conditions that restrict a collection to what the
        user may read.  Returns None when the user may not search it at all.

          policies            : every role except Intern
          documents           : CEO, CTO, CFO and administrators see all; other roles only the
                                documents they were granted access to (titles of the rest come
                                from the PostgreSQL retriever)
          emails              : only emails the user sent or received
          chats               : only the user's own AI chat sessions
          meetings            : only meetings of the user's projects
        Roles holding the matching permission see everything.
        """
        # Vector hits are passages of the text itself, so they need the right to read that text
        if collection_name == "policies":
            return [] if policy_access(user_context) == "content" else None
        if collection_name == "documents":
            access = document_access(user_context)
            if access == "content":
                return []
            if access == "none" or not user_context or user_context.get("employee_id") is None:
                return None
            db = SessionLocal()
            try:
                granted = sorted(postgres_retriever.granted_document_ids(db, user_context["employee_id"]))
            finally:
                db.close()
            if not granted:
                return None
            return [qmodels.FieldCondition(key="document_id", match=qmodels.MatchAny(any=granted))]
        if not user_context or user_context.get("employee_id") is None:
            return None

        emp_id = user_context["employee_id"]
        if collection_name == "emails":
            if can(user_context, Perm.PRIVATE_COMMS_ALL):
                return []
            return [qmodels.Filter(should=[
                qmodels.FieldCondition(key="sender_id", match=qmodels.MatchValue(value=emp_id)),
                qmodels.FieldCondition(key="receiver_id", match=qmodels.MatchValue(value=emp_id)),
            ])]
        if collection_name == "chats":
            if can(user_context, Perm.PRIVATE_COMMS_ALL):
                return []
            return [qmodels.FieldCondition(key="employee_id", match=qmodels.MatchValue(value=emp_id))]
        if collection_name == "meetings":
            if can(user_context, Perm.PROJECTS_READ_ALL):
                return []
            db = SessionLocal()
            try:
                project_ids = sorted(postgres_retriever.user_project_ids(db, emp_id))
            finally:
                db.close()
            if not project_ids:
                return None
            return [qmodels.FieldCondition(key="project_id", match=qmodels.MatchAny(any=project_ids))]
        return None

    def search_collection(
        self,
        query: str,
        collection_name: str = "documents",
        limit: int = 5,
        project_id: Optional[int] = None,
        department_id: Optional[int] = None,
        user_context: Optional[Dict[str, Any]] = None,
        include_graph: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid retrieval combining Qdrant semantic search + Neo4j relationship search,
        fuses the context, and reranks by similarity.  Results are restricted to what the
        user's job role may read.  Either store being offline only removes its share of
        the results - it never raises.
        """
        if collection_name not in COLLECTIONS:
            logger.warning(f"Rejected search on unknown collection '{collection_name}'.")
            return []

        access = self._access_conditions(collection_name, user_context)
        flat_contexts: List[Dict[str, Any]] = []
        query_vector: Optional[List[float]] = None

        # 1. Qdrant semantic search
        if access is not None and collection_name in self._qdrant_collections():
            try:
                query_vector = ingestion_pipeline.model.encode(query).tolist()

                must_conditions = list(access)
                if project_id is not None:
                    must_conditions.append(
                        qmodels.FieldCondition(key="project_id", match=qmodels.MatchValue(value=project_id))
                    )
                if department_id is not None:
                    must_conditions.append(
                        qmodels.FieldCondition(key="department_id", match=qmodels.MatchValue(value=department_id))
                    )
                qdrant_filter = qmodels.Filter(must=must_conditions) if must_conditions else None

                results = get_qdrant_client().query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    query_filter=qdrant_filter,
                    limit=limit,
                    with_payload=True
                ).points

                for hit in results:
                    payload = hit.payload or {}
                    title = payload.get("title") or payload.get("policy_name") or payload.get("subject") or "Untitled"
                    flat_contexts.append({
                        "id": hit.id,
                        "text": payload.get("text"),
                        "source": f"Qdrant: {collection_name} - '{title}'",
                        "metadata": {k: v for k, v in payload.items() if k != "text"},
                        "score": hit.score
                    })
            except Exception as e:
                metrics.increment("retrieval_failures")
                logger.error(f"Qdrant search failed on collection '{collection_name}': {e}")

        # 2. Optional Neo4j enrichment. A graph outage must not discard valid Qdrant results.
        neo4j_facts: List[Dict[str, Any]] = []
        if include_graph:
            try:
                neo4j_facts = self._query_neo4j(query, user_context)
            except Exception as e:
                logger.warning(f"Neo4j enrichment skipped: {e}")

        fused_contexts = flat_contexts + neo4j_facts
        if not fused_contexts:
            return []

        # 3. Rerank the fused context chunks
        return self._rerank_contexts(query_vector, fused_contexts, limit)

    def global_search(
        self,
        query: str,
        limit: int = 3,
        project_id: Optional[int] = None,
        department_id: Optional[int] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Perform semantic hybrid search across all enterprise collections and group results."""
        response = {}
        for idx, col in enumerate(COLLECTIONS):
            response[col] = self.search_collection(
                query=query,
                collection_name=col,
                limit=limit,
                project_id=project_id,
                department_id=department_id,
                user_context=user_context,
                include_graph=(idx == 0)  # graph facts once, not once per collection
            )
        return response

    def _query_neo4j(self, query: str, user_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query Neo4j knowledge graph using entity matching extracted from user prompt.
        Translates query into Cypher relationship lookups.
        """
        now = time.time()
        if now < self._neo4j_retry_at:
            return []

        search_tokens = keywords(query)[:3]  # Limit tokens to prevent massive queries
        if not search_tokens:
            return []

        can_see_projects = can(user_context, Perm.PROJECTS_READ_ALL)
        facts = []
        try:
            driver = get_neo4j_driver()
            with driver.session() as session:
                for token in search_tokens:
                    # Employee profile and manager reporting lines
                    emp_cypher = """
                    MATCH (e:Employee)
                    WHERE toLower(e.name) CONTAINS $token OR toLower(e.email) CONTAINS $token
                    OPTIONAL MATCH (mgr:Employee)-[:MANAGES]->(e)
                    OPTIONAL MATCH (e)-[:WORKS_IN]->(d:Department)
                    RETURN e.name as name, e.office as office, mgr.name as manager_name, d.name as dept_name
                    LIMIT 3
                    """
                    for r in session.run(emp_cypher, token=token):
                        manager_str = f"reporting to manager {r['manager_name']}" if r['manager_name'] else "with no listed manager"
                        dept_str = f"works in {r['dept_name']}" if r['dept_name'] else ""
                        facts.append({
                            "id": f"neo4j-emp-{token}-{r['name']}",
                            "text": f"Employee {r['name']} based in office {r['office'] or 'N/A'} {dept_str} {manager_str}.",
                            "source": "Neo4j Graph: Employee Reporting Hierarchy",
                            "metadata": {"entity": token, "type": "Employee"}
                        })

                    # Project details, manager and client - only for roles with project oversight
                    if can_see_projects:
                        proj_cypher = """
                        MATCH (p:Project)
                        WHERE toLower(p.name) CONTAINS $token OR toLower(p.code) CONTAINS $token
                        OPTIONAL MATCH (e:Employee)-[:MANAGES_PROJECT]->(p)
                        OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Client)
                        RETURN p.name as name, p.code as code, p.status as status, e.name as manager_name, c.name as client_name
                        LIMIT 3
                        """
                        for r in session.run(proj_cypher, token=token):
                            client_str = f"for client {r['client_name']}" if r['client_name'] else ""
                            mgr_str = f"managed by {r['manager_name']}" if r['manager_name'] else "unassigned PM"
                            facts.append({
                                "id": f"neo4j-proj-{token}-{r['code']}",
                                "text": f"Project {r['name']} [{r['code']}] is current state '{r['status']}'. Project is {mgr_str} {client_str}.",
                                "source": "Neo4j Graph: Project Registry",
                                "metadata": {"entity": token, "type": "Project"}
                            })

                    # Department profile
                    dept_cypher = """
                    MATCH (d:Department)
                    WHERE toLower(d.name) CONTAINS $token OR toLower(d.code) = $token
                    RETURN d.name as name, d.code as code, d.location as location
                    LIMIT 3
                    """
                    for r in session.run(dept_cypher, token=token):
                        facts.append({
                            "id": f"neo4j-dept-{token}-{r['code']}",
                            "text": f"Department {r['name']} ({r['code']}) located at office node {r['location'] or 'N/A'}.",
                            "source": "Neo4j Graph: Department Profile",
                            "metadata": {"entity": token, "type": "Department"}
                        })
        except Exception as e:
            self._neo4j_retry_at = now + OFFLINE_RETRY_SECONDS
            logger.warning(
                f"Neo4j is not reachable ({str(e).splitlines()[0][:120]}). Graph lookups are skipped for "
                f"{OFFLINE_RETRY_SECONDS}s."
            )
            return []

        # De-duplicate facts found through several tokens
        unique = {}
        for f in facts:
            unique.setdefault(f["text"], f)
        return list(unique.values())

    def _rerank_contexts(self, query_vector: Optional[List[float]], contexts: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """
        Calculates the semantic similarity vectors for all contexts (including Neo4j Cypher outputs)
        against the query vector to rerank and return top relevant context entries.
        """
        if not contexts:
            return []

        scored_contexts = []
        for ctx in contexts:
            # Check if it already has a score (from Qdrant), otherwise calculate it
            if "score" in ctx and ctx.get("score") is not None:
                score = ctx["score"]
            elif query_vector is None:
                score = 0.5  # No query embedding available (Qdrant offline): neutral score
            else:
                # Generate embedding for graph facts/unscored text chunk
                try:
                    chunk_vector = ingestion_pipeline.model.encode(ctx["text"]).tolist()
                    score = cosine_similarity(query_vector, chunk_vector)
                except Exception as ex:
                    logger.warning(f"Failed to generate similarity reranking vector: {ex}")
                    score = 0.5 # Default middle score if embedding fails

            ctx["score"] = round(score, 4)
            scored_contexts.append(ctx)

        # Sort descending by score
        scored_contexts.sort(key=lambda x: x["score"], reverse=True)
        return scored_contexts[:limit]

rag_service = RAGService()
