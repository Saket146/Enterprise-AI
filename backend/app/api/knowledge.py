from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.database.connection import get_db
from app.repositories.knowledge_repo import document_repo, policy_repo
from app.services.rag_service import rag_service, COLLECTIONS
from app.security.permissions import KNOWLEDGE_READER_ROLES, Perm, build_user_context, document_access, policy_access
from app.services.sql_retriever import postgres_retriever
from app.schemas.schemas import DocumentResponse, PolicyResponse
from app.middleware.rbac import get_current_user, log_audit_action, require
from app.models.models import DocumentAccessRequest, Employee
from app.agents.guardrails import AIGuardrails

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Explorer"])

# Who may do what in the Knowledge Explorer (see app/security/permissions.py):
#   Interns                       - nothing
#   every other role              - read all policies; see document titles
#   CEO, CTO, CFO, administrators - also read every document
#   anyone else                   - reads a document after an administrator approved their
#                                   access request for it (Operations Center)
can_list_knowledge = require(Perm.KNOWLEDGE_LIST)


def _document_states(db: Session, user: Employee, document_ids: List[int]) -> Dict[int, str]:
    """Per document: "open" (may read), "pending" (access requested) or "request" (may ask for access)."""
    context = build_user_context(user)
    if document_access(context) == "content":
        return {doc_id: "open" for doc_id in document_ids}
    states = {doc_id: "request" for doc_id in document_ids}
    if document_ids:
        rows = db.query(DocumentAccessRequest.document_id, DocumentAccessRequest.status).filter(
            DocumentAccessRequest.employee_id == user.employee_id,
            DocumentAccessRequest.document_id.in_(document_ids),
        ).all()
        for doc_id, state in rows:
            if state == "approved":
                states[doc_id] = "open"
            elif state == "pending" and states[doc_id] != "open":
                states[doc_id] = "pending"
    return states


@router.get("/access")
def get_knowledge_access(current_user: Employee = Depends(get_current_user)):
    """What the current user may see in the Knowledge Explorer."""
    context = build_user_context(current_user)
    documents = document_access(context)
    return {
        "can_list": documents != "none",
        "can_open_policies": policy_access(context) == "content",
        "can_open_all_documents": documents == "content",
        "can_request_documents": documents == "titles",
        "reader_roles": KNOWLEDGE_READER_ROLES,
    }


@router.get("/documents", response_model=List[DocumentResponse])
def get_documents(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(can_list_knowledge),
    search: Optional[str] = Query(None, description="Search document title, file name or type"),
    project_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    doc_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """
    List documents (titles and listing details only - never the text). Not available to Interns.
    Each row says whether the caller can open it, has asked for access, or can ask.
    """
    docs, _ = document_repo.search_documents(
        db,
        search_query=search,
        project_id=project_id,
        department_id=department_id,
        doc_type=doc_type,
        skip=skip,
        limit=limit
    )
    states = _document_states(db, current_user, [d.document_id for d in docs])
    listed = []
    for doc in docs:
        item = DocumentResponse.model_validate(doc)
        item.my_access = states.get(doc.document_id, "request")
        listed.append(item)
    return listed


@router.get("/documents/{document_id}")
def open_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(can_list_knowledge),
):
    """
    Open one document and read its text. Allowed for the CEO, CTO, CFO and system administrators,
    and for anyone whose access request for this document was approved.
    """
    doc = document_repo.get_by_id(db, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if not postgres_retriever.can_open_document(db, document_id, build_user_context(current_user)):
        log_audit_action(db, current_user.employee_id, "rbac_denied", "document", document_id, "api", "Open refused: no approved access")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You need approved access to open this document. Request access to it; a system administrator decides."
        )
    log_audit_action(db, current_user.employee_id, "document_opened", "document", document_id, "api", (doc.title or "")[:200])
    return {
        "document_id": doc.document_id,
        "title": doc.title,
        "document_type": doc.document_type,
        "file_name": doc.file_name,
        "project": doc.project.project_name if doc.project else None,
        "department": doc.department.department_name if doc.department else None,
        "author": f"{doc.creator.first_name} {doc.creator.last_name}" if doc.creator else None,
        "created_at": doc.created_at,
        "content": doc.content or "",
    }


@router.get("/policies", response_model=List[PolicyResponse])
def get_policies(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(can_list_knowledge),
    search: Optional[str] = Query(None, description="Search policy name or text"),
    department_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """List policies (name, version, date, owner). Not available to Interns. The text comes from the open endpoint."""
    can_read = policy_access(build_user_context(current_user)) == "content"
    policies, _ = policy_repo.search_policies(
        db,
        search_query=search,
        department_id=department_id,
        # Roles that cannot open policies must not be able to probe their text through search
        search_text=can_read,
        skip=skip,
        limit=limit
    )
    listed = []
    for policy in policies:
        item = PolicyResponse.model_validate(policy)
        item.description = None   # the text is only returned by the "open" endpoint below
        listed.append(item)
    return listed


@router.get("/policies/{policy_id}")
def open_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(can_list_knowledge),
):
    """Open one policy and read its text. Every role except Intern."""
    if policy_access(build_user_context(current_user)) != "content":
        log_audit_action(db, current_user.employee_id, "rbac_denied", "policy", policy_id, "api", "Open refused: no policies:read_content")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role cannot open policies.")
    policy = policy_repo.get_by_id(db, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found.")
    log_audit_action(db, current_user.employee_id, "policy_opened", "policy", policy_id, "api", (policy.policy_name or "")[:200])
    return {
        "policy_id": policy.policy_id,
        "policy_name": policy.policy_name,
        "version": policy.version,
        "effective_date": policy.effective_date,
        "department": policy.department.department_name if policy.department else None,
        "content": policy.description or "",
    }

@router.get("/semantic-search")
def run_semantic_search(
    query: str = Query(..., description="The query text for AI semantic similarity search"),
    collection: str = Query("documents", description="Target collection: documents, policies, emails, meetings, chats, or 'global'"),
    limit: int = Query(5, ge=1, le=20),
    project_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    current_user: Employee = Depends(get_current_user)
):
    """
    Perform RAG vector semantic search matching text queries against embeddings stored in Qdrant.
    Results are limited to what the caller's role may read: emails and chats only return the
    caller's own, meetings only those of the caller's projects.
    """
    if collection != "global" and collection not in COLLECTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown collection. Use one of: global, {', '.join(COLLECTIONS)}."
        )

    is_safe, error_msg = AIGuardrails.check_input(query)
    if not is_safe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    user_context = build_user_context(current_user)
    if collection == "global":
        return rag_service.global_search(
            query=query,
            limit=limit,
            project_id=project_id,
            department_id=department_id,
            user_context=user_context
        )
    else:
        return rag_service.search_collection(
            query=query,
            collection_name=collection,
            limit=limit,
            project_id=project_id,
            department_id=department_id,
            user_context=user_context
        )




@router.get("/search")
def search_knowledge(
    query: str = Query(..., min_length=2, description="What to look for"),
    scope: str = Query("all", description="all, documents, policies, emails, meetings or chats"),
    limit: int = Query(8, ge=1, le=20),
    current_user: Employee = Depends(get_current_user)
):
    """
    Source search used by the AI Assistant's "Search sources" panel.

    Returns the passages the assistant would read for a question: keyword matches from the
    PostgreSQL policies and documents tables, plus semantic matches from Qdrant when it is
    running. Results are limited to what the caller's role may read, and personal data inside
    documents, policies and meeting notes is redacted.
    """
    scopes = ["documents", "policies", "emails", "meetings", "chats"]
    if scope != "all" and scope not in scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scope. Use one of: all, {', '.join(scopes)}."
        )

    is_safe, error_msg = AIGuardrails.check_input(query)
    if not is_safe:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    user_context = build_user_context(current_user)
    wanted = scopes if scope == "all" else [scope]
    type_names = {"documents": "Document", "policies": "Policy", "emails": "Email", "meetings": "Meeting", "chats": "Past chat"}
    results = []

    # 1. Keyword matches from the PostgreSQL tables
    domains = tuple(d for d in ("policies", "documents") if d in wanted)
    if domains:
        for hit in postgres_retriever.search(query, user_context, domains=domains, limit=limit):
            if hit.get("denied"):
                continue   # Interns: nothing is listed, not even titles
            results.append({
                "title": hit.get("title") or "Untitled",
                "type": type_names["policies" if hit.get("kind") == "policy" else "documents"],
                "restricted": bool(hit.get("restricted")),
                "text": hit.get("note") if hit.get("restricted") else AIGuardrails.filter_pii(hit.get("body") or hit.get("text") or ""),
                "details": [f"{label}: {value}" for label, value in (hit.get("fields") or [])],
                "score": round(float(hit.get("score") or 0), 2),
                "store": "PostgreSQL",
            })

    # 2. Semantic matches from Qdrant (skipped automatically when Qdrant is not running)
    vector_available = bool(rag_service._qdrant_collections())
    if vector_available:
        for collection in wanted:
            hits = rag_service.search_collection(
                query, collection_name=collection, limit=min(limit, 4),
                user_context=user_context, include_graph=False
            )
            for hit in hits:
                meta = hit.get("metadata") or {}
                text = hit.get("text") or ""
                if collection in ("documents", "policies", "meetings"):
                    text = AIGuardrails.filter_pii(text)
                results.append({
                    "title": meta.get("title") or meta.get("policy_name") or meta.get("subject") or "Untitled",
                    "type": type_names[collection],
                    "text": text,
                    "restricted": False,
                    "details": [],
                    "score": round(float(hit.get("score") or 0), 2),
                    "store": "Qdrant",
                })

    results.sort(key=lambda r: r["score"], reverse=True)
    return {
        "query": query,
        "scope": scope,
        "vector_search_available": vector_available,
        "knowledge_access": document_access(user_context),
        "results": results[:limit],
    }
