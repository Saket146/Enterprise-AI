import os
import re
import uuid
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from neo4j import GraphDatabase

from app.database.connection import get_qdrant_client, get_neo4j_driver
from app.models.models import (
    Employee, Department, Role, Project, ProjectMember,
    Task, Client, Contract, Document, Policy, Meeting,
    Email, ChatSession, WorkflowRun
)

logger = logging.getLogger(__name__)

# Recursive character chunker helper
def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """Split text into manageable chunks with overlap."""
    if not text:
        return []
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunks.append(" ".join(chunk_words))
        i += (chunk_size - chunk_overlap)
    return chunks


class IngestionPipelineService:
    def __init__(self):
        self._model = None

    @property
    def model(self):
        """Lazy load SentenceTransformer model to save memory during initialization."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def initialize_qdrant_collections(self, client: QdrantClient):
        """Ensure necessary Qdrant collections are initialized."""
        collections = ["documents", "policies", "emails", "meetings", "chats"]
        for col in collections:
            try:
                # Check if exists
                exists = False
                res = client.get_collections()
                for c in res.collections:
                    if c.name == col:
                        exists = True
                        break
                
                if not exists:
                    logger.info(f"Creating Qdrant collection: {col}")
                    client.create_collection(
                        collection_name=col,
                        vectors_config=qmodels.VectorParams(
                            size=384,  # all-MiniLM-L6-v2 outputs 384 dimensions
                            distance=qmodels.Distance.COSINE
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to initialize collection {col}: {e}")

    def _index_records(self, client: QdrantClient, collection: str, records: List[Dict[str, Any]], batch_size: int = 64) -> int:
        """
        Chunk, embed and upsert records into a Qdrant collection in batches.
        Each record is {"key": unique string, "content": text, "payload": metadata dict}.
        Point ids are derived from the key, so re-running the sync updates points instead of duplicating them.
        """
        pending_ids, pending_texts, pending_payloads = [], [], []
        indexed = 0

        def flush():
            nonlocal indexed
            if not pending_texts:
                return
            vectors = self.model.encode(pending_texts, batch_size=batch_size, show_progress_bar=False)
            client.upsert(
                collection_name=collection,
                points=[
                    qmodels.PointStruct(id=pid, vector=vec.tolist(), payload=payload)
                    for pid, vec, payload in zip(pending_ids, vectors, pending_payloads)
                ]
            )
            indexed += len(pending_texts)
            pending_ids.clear(); pending_texts.clear(); pending_payloads.clear()

        for rec in records:
            for idx, chunk in enumerate(chunk_text(rec["content"])):
                pending_ids.append(str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{rec['key']}-{idx}")))
                pending_texts.append(chunk)
                pending_payloads.append({"text": chunk, **rec["payload"]})
                if len(pending_texts) >= batch_size:
                    flush()
        flush()
        return indexed

    def sync_to_qdrant(self, db: Session) -> Dict[str, Any]:
        """Index postgres text fields into Qdrant collections."""
        client = get_qdrant_client()
        self.initialize_qdrant_collections(client)

        stats = {"documents": 0, "policies": 0, "emails": 0, "meetings": 0, "chats": 0}

        def ts(value):
            return value.isoformat() if value else None

        # 1. Sync Documents (text lives in the documents.content column)
        doc_records = []
        for d in db.query(Document).all():
            content = f"Document Title: {d.title}. Type: {d.document_type}. File: {d.file_name}."
            if d.content:
                content += "\n" + d.content
            doc_records.append({
                "key": f"doc-{d.document_id}",
                "content": content,
                "payload": {
                    "document_id": d.document_id,
                    "project_id": d.project_id,
                    "department_id": d.department_id,
                    "title": d.title,
                    "type": d.document_type,
                    "timestamp": ts(d.created_at),
                },
            })
        stats["documents"] = self._index_records(client, "documents", doc_records)

        # 2. Sync Policies
        policy_records = [{
            "key": f"pol-{p.policy_id}",
            "content": f"Policy: {p.policy_name} (Version: {p.version})\n{p.description or ''}",
            "payload": {
                "policy_id": p.policy_id,
                "department_id": p.department_id,
                "policy_name": p.policy_name,
                "version": p.version,
                "timestamp": ts(p.created_at),
            },
        } for p in db.query(Policy).all()]
        stats["policies"] = self._index_records(client, "policies", policy_records)

        # 3. Sync Emails (sender_id / receiver_id are what the RBAC filter in rag_service uses)
        email_records = [{
            "key": f"eml-{e.email_id}",
            "content": f"Email type: {e.email_type or 'General'}\nSubject: {e.subject}\nBody: {e.body or ''}",
            "payload": {
                "email_id": e.email_id,
                "sender_id": e.sender_id,
                "receiver_id": e.receiver_id,
                "project_id": e.project_id,
                "department_id": e.department_id,
                "subject": e.subject,
                "timestamp": ts(e.sent_at),
            },
        } for e in db.query(Email).all()]
        stats["emails"] = self._index_records(client, "emails", email_records)

        # 4. Sync Meetings (project_id is what the RBAC filter uses)
        meeting_records = [{
            "key": f"mtg-{m.meeting_id}",
            "content": (
                f"Meeting Title: {m.meeting_title} (Type: {m.meeting_type or 'General'})\n"
                f"Agenda: {m.agenda or ''}\nMinutes:\n{m.minutes or ''}\nDecisions: {m.decision_summary or ''}"
            ),
            "payload": {
                "meeting_id": m.meeting_id,
                "project_id": m.project_id,
                "department_id": m.department_id,
                "organizer_id": m.organizer_id,
                "title": m.meeting_title,
                "timestamp": ts(m.meeting_date),
            },
        } for m in db.query(Meeting).all()]
        stats["meetings"] = self._index_records(client, "meetings", meeting_records)

        # 5. Sync Chat Sessions (summary + workflow outputs; employee_id is what the RBAC filter uses)
        chat_records = []
        for c in db.query(ChatSession).all():
            workflows = db.query(WorkflowRun).filter(WorkflowRun.session_id == c.session_id).all()
            final_outputs = " ".join([w.final_output for w in workflows if w.final_output])
            content = f"Chat Session: {c.session_title} (Status: {c.status})"
            if c.conversation_summary:
                content += f"\nSummary: {c.conversation_summary}"
            if final_outputs:
                content += f"\nAgent Output:\n{final_outputs}"
            chat_records.append({
                "key": f"cht-{c.session_id}",
                "content": content,
                "payload": {
                    "session_id": c.session_id,
                    "employee_id": c.employee_id,
                    "project_id": c.project_id,
                    "title": c.session_title,
                    "timestamp": ts(c.started_at),
                },
            })
        stats["chats"] = self._index_records(client, "chats", chat_records)

        # Payload indexes keep the RBAC and metadata filters fast
        for collection, fields in {
            "documents": ["project_id", "department_id"],
            "policies": ["department_id"],
            "emails": ["sender_id", "receiver_id", "project_id", "department_id"],
            "meetings": ["project_id", "department_id"],
            "chats": ["employee_id", "session_id"],
        }.items():
            for field in fields:
                try:
                    client.create_payload_index(
                        collection_name=collection,
                        field_name=field,
                        field_schema=qmodels.PayloadSchemaType.INTEGER
                    )
                except Exception as e:
                    logger.debug(f"Payload index {collection}.{field} not created: {e}")

        return stats

    def sync_to_neo4j(self, db: Session) -> Dict[str, Any]:
        """Load relational database nodes and relations into Neo4j Knowledge Graph."""
        driver = get_neo4j_driver()
        stats = {"nodes": 0, "relationships": 0}
        
        with driver.session() as session:
            # 1. Clean existing database
            logger.info("Cleaning existing Neo4j data...")
            session.run("MATCH (n) DETACH DELETE n")

            # 2. Add Departments
            depts = db.query(Department).all()
            logger.info(f"Ingesting {len(depts)} Department nodes...")
            for d in depts:
                session.run(
                    "MERGE (dept:Department {id: $id}) "
                    "SET dept.name = $name, dept.code = $code, dept.location = $location",
                    id=d.department_id, name=d.department_name, code=d.department_code, location=d.location
                )
                stats["nodes"] += 1

            # 3. Add Roles
            roles = db.query(Role).all()
            logger.info(f"Ingesting {len(roles)} Role nodes...")
            for r in roles:
                session.run(
                    "MERGE (role:Role {id: $id}) "
                    "SET role.name = $name, role.level = $level",
                    id=r.role_id, name=r.role_name, level=r.role_level
                )
                stats["nodes"] += 1

            # 4. Add Employees and relationships (WORKS_IN, MANAGES, ASSIGNED_TO_ROLE)
            employees = db.query(Employee).all()
            logger.info(f"Ingesting {len(employees)} Employee nodes and structural relationships...")
            for emp in employees:
                session.run(
                    "MERGE (e:Employee {id: $id}) "
                    "SET e.name = $name, e.email = $email, e.office = $office",
                    id=emp.employee_id, name=f"{emp.first_name} {emp.last_name}", email=emp.email, office=emp.office_location
                )
                stats["nodes"] += 1

                # Relation: WORKS_IN -> Department
                if emp.department_id:
                    session.run(
                        "MATCH (e:Employee {id: $emp_id}) "
                        "MATCH (d:Department {id: $dept_id}) "
                        "MERGE (e)-[:WORKS_IN]->(d)",
                        emp_id=emp.employee_id, dept_id=emp.department_id
                    )
                    stats["relationships"] += 1
                
                # Relation: ASSIGNED_TO_ROLE -> Role
                if emp.role_id:
                    session.run(
                        "MATCH (e:Employee {id: $emp_id}) "
                        "MATCH (r:Role {id: $role_id}) "
                        "MERGE (e)-[:ASSIGNED_TO_ROLE]->(r)",
                        emp_id=emp.employee_id, role_id=emp.role_id
                    )
                    stats["relationships"] += 1

                # Relation: MANAGES -> Employee (Self manager-subordinate link)
                if emp.manager_id and emp.manager_id != emp.employee_id:
                    session.run(
                        "MATCH (mgr:Employee {id: $manager_id}) "
                        "MATCH (sub:Employee {id: $sub_id}) "
                        "MERGE (mgr)-[:MANAGES]->(sub)",
                        manager_id=emp.manager_id, sub_id=emp.employee_id
                    )
                    stats["relationships"] += 1

            # 5. Add Clients
            clients = db.query(Client).all()
            for c in clients:
                session.run(
                    "MERGE (cli:Client {id: $id}) "
                    "SET cli.name = $name, cli.industry = $industry",
                    id=c.client_id, name=c.client_name, industry=c.industry
                )
                stats["nodes"] += 1

            # 6. Add Projects and relationships (BELONGS_TO, ASSIGNED_TO)
            projects = db.query(Project).all()
            for p in projects:
                session.run(
                    "MERGE (proj:Project {id: $id}) "
                    "SET proj.name = $name, proj.code = $code, proj.status = $status",
                    id=p.project_id, name=p.project_name, code=p.project_code, status=p.status
                )
                stats["nodes"] += 1

                # Relation: Project BELONGS_TO Client
                if p.client_id:
                    session.run(
                        "MATCH (p:Project {id: $proj_id}) "
                        "MATCH (c:Client {id: $cli_id}) "
                        "MERGE (p)-[:BELONGS_TO]->(c)",
                        proj_id=p.project_id, cli_id=p.client_id
                    )
                    stats["relationships"] += 1
                
                # Relation: Project MANAGED_BY Employee
                if p.project_manager_id:
                    session.run(
                        "MATCH (e:Employee {id: $emp_id}) "
                        "MATCH (p:Project {id: $proj_id}) "
                        "MERGE (e)-[:MANAGES_PROJECT]->(p)",
                        emp_id=p.project_manager_id, proj_id=p.project_id
                    )
                    stats["relationships"] += 1

            # 7. Add Project memberships (ASSIGNED_TO)
            members = db.query(ProjectMember).all()
            for m in members:
                session.run(
                    "MATCH (e:Employee {id: $emp_id}) "
                    "MATCH (p:Project {id: $proj_id}) "
                    "MERGE (e)-[r:ASSIGNED_TO]->(p) "
                    "SET r.role = $role, r.allocation = $allocation",
                    emp_id=m.employee_id, proj_id=m.project_id, role=m.assigned_role, allocation=m.allocation_percentage
                )
                stats["relationships"] += 1

            # 8. Add Tasks and relationships (HAS_TASK, ASSIGNED_TO)
            tasks = db.query(Task).all()
            for t in tasks:
                session.run(
                    "MERGE (task:Task {id: $id}) "
                    "SET task.title = $title, task.status = $status, task.priority = $priority",
                    id=t.task_id, title=t.title, status=t.status, priority=t.priority
                )
                stats["nodes"] += 1

                # Relation: Project HAS_TASK Task
                session.run(
                    "MATCH (p:Project {id: $proj_id}) "
                    "MATCH (t:Task {id: $task_id}) "
                    "MERGE (p)-[:HAS_TASK]->(t)",
                    proj_id=t.project_id, task_id=t.task_id
                )
                stats["relationships"] += 1

                # Relation: Employee ASSIGNED_TO Task
                if t.assigned_to:
                    session.run(
                        "MATCH (e:Employee {id: $emp_id}) "
                        "MATCH (t:Task {id: $task_id}) "
                        "MERGE (e)-[:ASSIGNED_TO_TASK]->(t)",
                        emp_id=t.assigned_to, task_id=t.task_id
                    )
                    stats["relationships"] += 1

            # 9. Add Documents and relationships (HAS_DOCUMENT, CREATED_BY)
            docs = db.query(Document).all()
            for d in docs:
                session.run(
                    "MERGE (doc:Document {id: $id}) "
                    "SET doc.title = $title, doc.type = $type, doc.file = $file",
                    id=d.document_id, title=d.title, type=d.document_type, file=d.file_name
                )
                stats["nodes"] += 1

                # Relation: Project HAS_DOCUMENT Document
                if d.project_id:
                    session.run(
                        "MATCH (p:Project {id: $proj_id}) "
                        "MATCH (doc:Document {id: $doc_id}) "
                        "MERGE (p)-[:HAS_DOCUMENT]->(doc)",
                        proj_id=d.project_id, doc_id=d.document_id
                    )
                    stats["relationships"] += 1
                
                # Relation: Employee CREATED Document
                if d.created_by:
                    session.run(
                        "MATCH (e:Employee {id: $emp_id}) "
                        "MATCH (doc:Document {id: $doc_id}) "
                        "MERGE (e)-[:CREATED]->(doc)",
                        emp_id=d.created_by, doc_id=d.document_id
                    )
                    stats["relationships"] += 1

            # 10. Add Policies and relationships (OWNS)
            policies = db.query(Policy).all()
            for pol in policies:
                session.run(
                    "MERGE (p:Policy {id: $id}) "
                    "SET p.name = $name, p.version = $version",
                    id=pol.policy_id, name=pol.policy_name, version=pol.version
                )
                stats["nodes"] += 1

                # Relation: Department OWNS Policy
                if pol.department_id:
                    session.run(
                        "MATCH (d:Department {id: $dept_id}) "
                        "MATCH (p:Policy {id: $policy_id}) "
                        "MERGE (d)-[:OWNS]->(p)",
                        dept_id=pol.department_id, policy_id=pol.policy_id
                    )
                    stats["relationships"] += 1

            # 11. Add Meetings and relationships (HAS_MEETING, ORGANIZED_BY)
            meetings = db.query(Meeting).all()
            for m in meetings:
                session.run(
                    "MERGE (mtg:Meeting {id: $id}) "
                    "SET mtg.title = $title, mtg.date = $date, mtg.room = $room",
                    id=m.meeting_id, title=m.meeting_title, date=str(m.meeting_date), room=m.meeting_room
                )
                stats["nodes"] += 1

                # Relation: Project HAS_MEETING Meeting
                if m.project_id:
                    session.run(
                        "MATCH (p:Project {id: $proj_id}) "
                        "MATCH (mtg:Meeting {id: $mtg_id}) "
                        "MERGE (p)-[:HAS_MEETING]->(mtg)",
                        proj_id=m.project_id, mtg_id=m.meeting_id
                    )
                    stats["relationships"] += 1
                
                # Relation: Employee ORGANIZED Meeting
                if m.organizer_id:
                    session.run(
                        "MATCH (e:Employee {id: $emp_id}) "
                        "MATCH (mtg:Meeting {id: $mtg_id}) "
                        "MERGE (e)-[:ORGANIZED]->(mtg)",
                        emp_id=m.organizer_id, mtg_id=m.meeting_id
                    )
                    stats["relationships"] += 1

        # The driver is shared across the application (see database.connection) - do not close it.
        return stats

ingestion_pipeline = IngestionPipelineService()
