from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.database.connection import get_db
from app.repositories.knowledge_repo import document_repo, policy_repo
from app.services.rag_service import rag_service
from app.schemas.schemas import DocumentResponse, PolicyResponse
from app.middleware.rbac import get_current_user
from app.models.models import Employee

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Explorer"])

@router.get("/documents", response_model=List[DocumentResponse])
def get_documents(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
    search: Optional[str] = Query(None, description="Search document title, file name or type"),
    project_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    doc_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Retrieve list of documents with metadata filters."""
    docs, _ = document_repo.search_documents(
        db,
        search_query=search,
        project_id=project_id,
        department_id=department_id,
        doc_type=doc_type,
        skip=skip,
        limit=limit
    )
    return docs

@router.get("/policies", response_model=List[PolicyResponse])
def get_policies(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
    search: Optional[str] = Query(None, description="Search policy name or description content"),
    department_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Retrieve list of enterprise policies."""
    policies, _ = policy_repo.search_policies(
        db,
        search_query=search,
        department_id=department_id,
        skip=skip,
        limit=limit
    )
    return policies

@router.get("/semantic-search")
def run_semantic_search(
    query: str = Query(..., description="The query text for AI semantic similarity search"),
    collection: str = Query("documents", description="Target collection: documents, policies, emails, meetings, chats, or 'global'"),
    limit: int = Query(5, ge=1, le=20),
    project_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    current_user: Employee = Depends(get_current_user)
):
    """Perform RAG vector semantic search matching text queries against embeddings stored in Qdrant."""
    if collection == "global":
        return rag_service.global_search(
            query=query,
            limit=limit,
            project_id=project_id,
            department_id=department_id
        )
    else:
        return rag_service.search_collection(
            query=query,
            collection_name=collection,
            limit=limit,
            project_id=project_id,
            department_id=department_id
        )


