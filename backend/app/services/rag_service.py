import logging
import re
from typing import List, Dict, Any, Optional
import numpy as np
from qdrant_client.http import models as qmodels

from app.database.connection import get_qdrant_client, get_neo4j_driver
from app.services.pipeline_service import ingestion_pipeline

logger = logging.getLogger(__name__)

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
    def search_collection(
        self,
        query: str,
        collection_name: str = "documents",
        limit: int = 5,
        project_id: Optional[int] = None,
        department_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid retrieval combining Qdrant semantic search + Neo4j relationship search,
        fuses the context, and reranks by similarity.
        """
        try:
            client = get_qdrant_client()
            
            # 1. Embed query text
            query_vector = ingestion_pipeline.model.encode(query).tolist()
            
            # 2. Construct Qdrant filters
            must_conditions = []
            if project_id is not None:
                must_conditions.append(
                    qmodels.FieldCondition(
                        key="project_id",
                        match=qmodels.MatchValue(value=project_id)
                    )
                )
            if department_id is not None:
                must_conditions.append(
                    qmodels.FieldCondition(
                        key="department_id",
                        match=qmodels.MatchValue(value=department_id)
                    )
                )
                
            qdrant_filter = None
            if must_conditions:
                qdrant_filter = qmodels.Filter(must=must_conditions)
                
            # Perform vector semantic search
            results = client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=qdrant_filter,
                limit=limit
            )
            
            # Format semantic hits
            flat_contexts = []
            for hit in results:
                title = hit.payload.get("title") or hit.payload.get("policy_name") or hit.payload.get("subject") or "Untitled"
                source_label = f"Qdrant: {collection_name} - '{title}'"
                flat_contexts.append({
                    "id": hit.id,
                    "text": hit.payload.get("text"),
                    "source": source_label,
                    "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
                    "score": hit.score
                })
            
            # 3. Perform Neo4j Relationship Search to enrich context
            neo4j_facts = self._query_neo4j(query)
            
            # Fuse the contexts
            fused_contexts = flat_contexts + neo4j_facts
            
            # 4. Rerank the fused context chunks
            reranked = self._rerank_contexts(query_vector, fused_contexts, limit)
            return reranked
            
        except Exception as e:
            logger.error(f"Hybrid retrieval failed on collection '{collection_name}': {e}")
            return []

    def global_search(
        self,
        query: str,
        limit: int = 3,
        project_id: Optional[int] = None,
        department_id: Optional[int] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Perform semantic hybrid search across all enterprise collections and group results."""
        collections = ["documents", "policies", "emails", "meetings", "chats"]
        response = {}
        for col in collections:
            hits = self.search_collection(
                query=query,
                collection_name=col,
                limit=limit,
                project_id=project_id,
                department_id=department_id
            )
            response[col] = hits
        return response

    def _query_neo4j(self, query: str) -> List[Dict[str, Any]]:
        """
        Query Neo4j knowledge graph using entity matching extracted from user prompt.
        Translates query into Cypher relationship lookups.
        """
        facts = []
        driver = None
        try:
            driver = get_neo4j_driver()
        except Exception as e:
            logger.warning(f"Neo4j driver offline. Skipping Graph relation lookups. Error: {e}")
            return []

        # Find potential entity tokens (names or words starting with capital letters or number tokens)
        words = re.findall(r"\b[A-Za-z0-9-]+\b", query)
        search_tokens = [w for w in words if len(w) > 2 and w.lower() not in ["and", "the", "for", "are", "you", "who"]]
        
        if not search_tokens:
            return []

        with driver.session() as session:
            for token in search_tokens[:3]:  # Limit tokens to prevent massive queries
                # Check for Employee profile and manager reporting lines
                emp_cypher = """
                MATCH (e:Employee) 
                WHERE e.name CONTAINS $token OR e.email CONTAINS $token
                OPTIONAL MATCH (mgr:Employee)-[:MANAGES]->(e)
                OPTIONAL MATCH (e)-[:WORKS_IN]->(d:Department)
                RETURN e.name as name, e.email as email, e.office as office, mgr.name as manager_name, d.name as dept_name
                LIMIT 3
                """
                res = session.run(emp_cypher, token=token)
                for r in res:
                    manager_str = f"reporting to manager {r['manager_name']}" if r['manager_name'] else "with no listed manager"
                    dept_str = f"works in {r['dept_name']}" if r['dept_name'] else ""
                    fact_text = f"Employee {r['name']} ({r['email']}) based in office {r['office'] or 'N/A'}. {dept_str} {manager_str}."
                    facts.append({
                        "id": f"neo4j-emp-{token}",
                        "text": fact_text,
                        "source": "Neo4j Graph: Employee Reporting Hierarchy",
                        "metadata": {"entity": token, "type": "Employee"}
                    })

                # Check for Project details, manager and members
                proj_cypher = """
                MATCH (p:Project) 
                WHERE p.name CONTAINS $token OR p.code CONTAINS $token
                OPTIONAL MATCH (e:Employee)-[:MANAGES_PROJECT]->(p)
                OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Client)
                RETURN p.name as name, p.code as code, p.status as status, e.name as manager_name, c.name as client_name
                LIMIT 3
                """
                res = session.run(proj_cypher, token=token)
                for r in res:
                    client_str = f"for client {r['client_name']}" if r['client_name'] else ""
                    mgr_str = f"managed by {r['manager_name']}" if r['manager_name'] else "unassigned PM"
                    fact_text = f"Project {r['name']} [{r['code']}] is current state '{r['status']}'. Project is {mgr_str} {client_str}."
                    facts.append({
                        "id": f"neo4j-proj-{token}",
                        "text": fact_text,
                        "source": "Neo4j Graph: Project Registry",
                        "metadata": {"entity": token, "type": "Project"}
                    })

                # Check for Department budgets
                dept_cypher = """
                MATCH (d:Department)
                WHERE d.name CONTAINS $token OR d.code CONTAINS $token
                RETURN d.name as name, d.code as code, d.location as location
                LIMIT 3
                """
                res = session.run(dept_cypher, token=token)
                for r in res:
                    fact_text = f"Department {r['name']} ({r['code']}) located at office node {r['location'] or 'N/A'}."
                    facts.append({
                        "id": f"neo4j-dept-{token}",
                        "text": fact_text,
                        "source": "Neo4j Graph: Department Profile",
                        "metadata": {"entity": token, "type": "Department"}
                    })

        driver.close()
        return facts

    def _rerank_contexts(self, query_vector: List[float], contexts: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """
        Calculates the semantic similarity vectors for all contexts (including Neo4j Cypher outputs)
        against the query vector to rerank and return top relevant context entries.
        """
        if not contexts:
            return []

        # Rerank items using cosine similarity scores
        scored_contexts = []
        for ctx in contexts:
            # Check if it already has a score (from Qdrant), otherwise calculate it
            if "score" in ctx and ctx.get("score") is not None:
                score = ctx["score"]
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
