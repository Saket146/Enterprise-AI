from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.repositories.base import BaseRepository
from app.models.models import Document, Policy

class DocumentRepository(BaseRepository[Document]):
    def __init__(self):
        super().__init__(Document)

    def search_documents(
        self,
        db: Session,
        *,
        search_query: Optional[str] = None,
        project_id: Optional[int] = None,
        department_id: Optional[int] = None,
        doc_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Document], int]:
        """Search documents using database fields. Returns document list and total count."""
        query = db.query(Document)
        
        if project_id:
            query = query.filter(Document.project_id == project_id)
        if department_id:
            query = query.filter(Document.department_id == department_id)
        if doc_type:
            query = query.filter(Document.document_type == doc_type)
            
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                or_(
                    Document.title.ilike(search_pattern),
                    Document.file_name.ilike(search_pattern),
                    Document.document_type.ilike(search_pattern)
                )
            )
            
        total = query.count()
        results = query.order_by(Document.document_id).offset(skip).limit(limit).all()
        return results, total


class PolicyRepository(BaseRepository[Policy]):
    def __init__(self):
        super().__init__(Policy)

    def search_policies(
        self,
        db: Session,
        *,
        search_query: Optional[str] = None,
        department_id: Optional[int] = None,
        search_text: bool = True,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Policy], int]:
        """
        Search policies using database fields. Returns policy list and total count.
        With search_text=False only the policy name is searched, not the policy text.
        """
        query = db.query(Policy)
        
        if department_id:
            query = query.filter(Policy.department_id == department_id)
            
        if search_query:
            search_pattern = f"%{search_query}%"
            if search_text:
                query = query.filter(
                    or_(
                        Policy.policy_name.ilike(search_pattern),
                        Policy.description.ilike(search_pattern)
                    )
                )
            else:
                query = query.filter(Policy.policy_name.ilike(search_pattern))
            
        total = query.count()
        results = query.order_by(Policy.policy_name, Policy.policy_id).offset(skip).limit(limit).all()
        return results, total

document_repo = DocumentRepository()
policy_repo = PolicyRepository()
