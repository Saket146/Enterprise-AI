from typing import Generic, Type, TypeVar, List, Optional, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from app.database.connection import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """Generic repository providing basic CRUD operations for SQLAlchemy models."""
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get_by_id(self, db: Session, id: Any) -> Optional[ModelType]:
        """Fetch a single record by primary key."""
        pk_column = self.model.__table__.primary_key.columns.values()[0]
        return db.query(self.model).filter(pk_column == id).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Fetch multiple records with offset pagination and basic equality filtering."""
        query = db.query(self.model)
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.filter(getattr(self.model, field) == value)
        return query.offset(skip).limit(limit).all()

    def count(self, db: Session, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records matching optional filters."""
        query = db.query(self.model)
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.filter(getattr(self.model, field) == value)
        return query.count()

    def create(self, db: Session, *, obj_in: Dict[str, Any]) -> ModelType:
        """Insert a new record in the database."""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Dict[str, Any]
    ) -> ModelType:
        """Update fields of an existing record."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field) and value is not None:
                setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """Remove a record by primary key."""
        obj = self.get_by_id(db, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
