from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.pipeline_service import ingestion_pipeline
from app.schemas.schemas import SyncResponse
from app.middleware.rbac import RoleChecker, get_current_user
from app.models.models import Employee

router = APIRouter(prefix="/api/ingestion", tags=["Data Ingestion & AI Prep"])

# Ingestion is restricted to system administrators
admin_only = RoleChecker(allowed_roles=["Admin", "AI Administrator"])

@router.post("/qdrant", response_model=SyncResponse)
def trigger_vector_ingestion(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(admin_only)
):
    """
    Trigger the Vector Ingestion Pipeline:
    Reads text data from Postgres (documents, policies, emails, meetings, chats),
    chunks them, generates vector embeddings (all-MiniLM-L6-v2), and uploads to Qdrant.
    """
    try:
        stats = ingestion_pipeline.sync_to_qdrant(db)
        return SyncResponse(
            success=True,
            message="Vector database ingestion completed successfully.",
            details=stats
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector database ingestion failed: {e}"
        )

@router.post("/neo4j", response_model=SyncResponse)
def trigger_graph_ingestion(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(admin_only)
):
    """
    Trigger the Knowledge Graph Ingestion Pipeline:
    Syncs organizational structure, roles, projects, tasks, meetings and documents
    from Postgres into Neo4j graph nodes and relationship edges.
    """
    try:
        stats = ingestion_pipeline.sync_to_neo4j(db)
        return SyncResponse(
            success=True,
            message="Neo4j Knowledge Graph synchronization completed successfully.",
            details=stats
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Neo4j synchronization failed: {e}"
        )
