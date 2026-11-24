import json
import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Body, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.database.connection import get_db
from app.models.models import Email, Meeting, ChatSession, ChatMessage, WorkflowRun, AgentLog, Approval, Employee
from app.schemas.schemas import EmailResponse, MeetingResponse
from app.middleware.rbac import get_current_user, log_audit_action
from app.security.permissions import build_user_context
from app.observability import metrics
from app.agents.graph import agent_graph
from app.agents.guardrails import AIGuardrails
from app.agents.memory import short_term_memory, long_term_memory
from app.services.answer_composer import build_sources
from app.services.chat_titles import DEFAULT_TITLE, clean_title, generate_title, is_default_title

logger = logging.getLogger(__name__)

# Background workers for writing chat titles while the answer is being prepared
_title_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="chat-title")

router = APIRouter(prefix="/api/communications", tags=["Communication & AI Sessions"])

@router.get("/emails", response_model=List[EmailResponse])
def get_emails(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Retrieve emails sent or received by the current employee."""
    emails = db.query(Email).filter(
        (Email.sender_id == current_user.employee_id) |
        (Email.receiver_id == current_user.employee_id)
    ).order_by(Email.sent_at.desc()).offset(skip).limit(limit).all()
    return emails

@router.get("/meetings", response_model=List[MeetingResponse])
def get_meetings(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Retrieve meetings organized by the current employee or related to their projects."""
    # Find employee's assigned projects
    project_ids = [pm.project_id for pm in current_user.project_memberships]
    
    meetings = db.query(Meeting).filter(
        (Meeting.organizer_id == current_user.employee_id) |
        (Meeting.project_id.in_(project_ids))
    ).order_by(Meeting.meeting_date.desc()).offset(skip).limit(limit).all()
    return meetings

# ----------------------------------------------------------------------
# AI assistant chats
# ----------------------------------------------------------------------
class ChatCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)


class ChatRename(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ChatMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


def _own_session(db: Session, session_id: int, user: Employee) -> ChatSession:
    """A chat belongs to exactly one employee; nobody else can read, rename or delete it."""
    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.employee_id == user.employee_id
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found."
        )
    return session


def _steps(logs: List[AgentLog]) -> List[Dict[str, Any]]:
    return [{
        "agent": log.agent_name,
        "description": log.task_description,
        "result": log.output_data,
        "duration_ms": log.execution_time_ms,
        "confidence": float(log.confidence_score) if log.confidence_score is not None else None,
    } for log in sorted(logs, key=lambda l: l.agent_log_id)]


def _message_out(msg: ChatMessage, logs: Optional[List[AgentLog]] = None) -> Dict[str, Any]:
    try:
        sources = json.loads(msg.sources) if msg.sources else []
    except ValueError:
        sources = []
    return {
        "id": f"m{msg.message_id}",
        "role": msg.role,
        "content": msg.content,
        "sources": sources,
        "steps": _steps(logs or []) if msg.role == "assistant" else [],
        "created_at": msg.created_at,
    }


def _session_summary(session: ChatSession, last_activity: Optional[datetime] = None, message_count: Optional[int] = None) -> Dict[str, Any]:
    return {
        "session_id": session.session_id,
        "session_title": session.session_title or DEFAULT_TITLE,
        "status": session.status,
        "started_at": session.started_at,
        "last_activity_at": last_activity or session.started_at,
        "message_count": message_count if message_count is not None else (session.message_count or 0),
    }


def _session_messages(db: Session, session: ChatSession) -> List[Dict[str, Any]]:
    """Messages of a chat, oldest first. Chats from before message storage are rebuilt from their workflow runs."""
    workflows = db.query(WorkflowRun).filter(WorkflowRun.session_id == session.session_id).order_by(WorkflowRun.workflow_id).all()
    logs_by_workflow = {w.workflow_id: list(w.agent_logs) for w in workflows}
    stored = db.query(ChatMessage).filter(ChatMessage.session_id == session.session_id).order_by(ChatMessage.message_id).all()
    stored_workflow_ids = {m.workflow_id for m in stored}

    messages: List[Dict[str, Any]] = []
    for w in workflows:
        if w.workflow_id in stored_workflow_ids:
            continue
        question = (w.workflow_name or "").replace("Enterprise QA: ", "").replace("Chat: ", "")
        messages.append({"id": f"w{w.workflow_id}-q", "role": "user", "content": question, "sources": [], "steps": [], "created_at": w.started_at})
        messages.append({
            "id": f"w{w.workflow_id}-a", "role": "assistant", "content": w.final_output or "", "sources": [],
            "steps": _steps(logs_by_workflow.get(w.workflow_id, [])), "created_at": w.completed_at or w.started_at,
        })
    for m in stored:
        messages.append(_message_out(m, logs_by_workflow.get(m.workflow_id)))
    return messages


@router.get("/chats")
def get_chat_sessions(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """List the current user's AI assistant chats, most recently used first."""
    activity = db.query(
        ChatMessage.session_id.label("sid"),
        func.max(ChatMessage.created_at).label("last_at"),
        func.count(ChatMessage.message_id).label("n"),
    ).group_by(ChatMessage.session_id).subquery()

    rows = db.query(ChatSession, activity.c.last_at, activity.c.n).outerjoin(
        activity, activity.c.sid == ChatSession.session_id
    ).filter(
        ChatSession.employee_id == current_user.employee_id
    ).order_by(
        func.coalesce(activity.c.last_at, ChatSession.started_at).desc(), ChatSession.session_id.desc()
    ).offset(skip).limit(limit).all()
    return [_session_summary(s, last_at, n) for s, last_at, n in rows]


@router.get("/chats/{session_id}")
def get_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """One chat with all of its messages (question, answer, sources and the agent steps behind each answer)."""
    session = _own_session(db, session_id, current_user)
    messages = _session_messages(db, session)
    detail = _session_summary(session, messages[-1]["created_at"] if messages else None, len(messages))
    detail["messages"] = messages
    return detail


@router.post("/chats", status_code=status.HTTP_201_CREATED)
def create_chat_session(
    body: Optional[ChatCreate] = Body(default=None),
    title: Optional[str] = Query(None, description="Optional title. Leave empty: the chat is named automatically from the first question."),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Create a new chat. Without a title it is called 'New chat' until the first question names it."""
    requested = clean_title((body.title if body and body.title else title) or "")
    session = ChatSession(
        employee_id=current_user.employee_id,
        session_title=requested or DEFAULT_TITLE,
        session_type="assistant",
        message_count=0,
        status="active"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_summary(session, message_count=0)


@router.patch("/chats/{session_id}")
def rename_chat_session(
    session_id: int,
    body: ChatRename,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Rename a chat."""
    session = _own_session(db, session_id, current_user)
    new_title = clean_title(body.title)
    if not new_title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The title cannot be empty.")
    session.session_title = new_title
    db.commit()
    db.refresh(session)
    return _session_summary(session)


@router.delete("/chats/{session_id}")
def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Delete a chat with its messages, answers and agent traces. This cannot be undone."""
    session = _own_session(db, session_id, current_user)
    try:
        workflow_ids = [w for (w,) in db.query(WorkflowRun.workflow_id).filter(WorkflowRun.session_id == session_id)]
        db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete(synchronize_session=False)
        if workflow_ids:
            db.query(AgentLog).filter(AgentLog.workflow_id.in_(workflow_ids)).delete(synchronize_session=False)
            db.query(Approval).filter(Approval.workflow_id.in_(workflow_ids)).delete(synchronize_session=False)
            db.query(WorkflowRun).filter(WorkflowRun.workflow_id.in_(workflow_ids)).delete(synchronize_session=False)
        db.delete(session)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete chat {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="The chat could not be deleted.")

    # Also forget it in Redis (short-term memory) and Qdrant (long-term memory); both are best-effort.
    short_term_memory.clear(session_id)
    long_term_memory.forget_session(session_id)
    log_audit_action(db, current_user.employee_id, "chat_deleted", "chat_session", session_id, "api", "")
    return {"deleted": True, "session_id": session_id}


@router.post("/chats/{session_id}/message")
def send_chat_message(
    session_id: int,
    body: Optional[ChatMessageIn] = Body(default=None),
    message: Optional[str] = Query(None, description="Message text (the JSON body is preferred)"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Send a message to the AI assistant. Runs the input guardrails, loads the chat history,
    executes the multi-agent graph, stores question, answer, sources and agent traces,
    and names the chat automatically after its first question.
    """
    session = _own_session(db, session_id, current_user)

    message = ((body.message if body else None) or message or "").strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The message is empty.")

    # 1. Run Input Guardrails
    is_safe, error_msg = AIGuardrails.check_input(message)
    if not is_safe:
        # Blocked prompts are security events: count them and keep an audit record
        metrics.increment("security_intercepts")
        log_audit_action(
            db, current_user.employee_id, "blocked_prompt", "chat_session", session_id,
            "api", error_msg
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # The title of a new chat is written at the same time as the answer, not after it
    title_future = None
    if is_default_title(session.session_title) and not session.message_count \
            and db.query(ChatMessage.message_id).filter(ChatMessage.session_id == session_id).first() is None:
        title_future = _title_pool.submit(generate_title, message)

    # 2. Retrieve history and construct initial state
    history = short_term_memory.get_history(session_id)
    
    # The role comes from the database row loaded for this request (never from the client),
    # and every agent tool checks it against the job-role permission matrix.
    user_context = build_user_context(current_user)
    
    # Structure messages: history + new user prompt
    messages_payload = [{"role": m["role"], "content": m["content"]} for m in history]
    messages_payload.append({"role": "user", "content": message})
    
    initial_state = {
        "messages": messages_payload,
        "user_context": user_context,
        "retrieved_context": [],
        "agent_trace": []
    }
    
    # 3. Invoke compiled multi-agent state graph
    try:
        final_state = agent_graph.invoke(initial_state)
    except Exception as e:
        logger.error(f"AI Agent Graph execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The assistant could not finish this request. See the server log for details."
        )

    # Extract final text output
    assistant_msgs = [m for m in final_state.get("messages", []) if m.get("role") == "assistant"]
    final_answer = assistant_msgs[-1]["content"] if assistant_msgs else "I wasn't able to produce an answer for that."
    sources = build_sources(final_state.get("retrieved_context") or [])

    # 4. Save short-term memory
    short_term_memory.add_message(session_id, "user", message)
    short_term_memory.add_message(session_id, "assistant", final_answer)

    # 5. Persist Workflow Run
    traces = final_state.get("agent_trace") or []
    last_trace = traces[-1] if traces else {}
    final_score = last_trace.get("confidence_score", 0.95) if last_trace else 0.95
    
    workflow = WorkflowRun(
        session_id=session_id,
        workflow_name=f"Chat: {message[:120]}",
        status="completed",
        confidence_score=round(float(final_score), 2),
        final_output=final_answer,
        completed_at=datetime.utcnow()
    )
    db.add(workflow)
    db.flush()
    
    # 6. Save observability Agent Logs
    for trace in traces:
        log = AgentLog(
            workflow_id=workflow.workflow_id,
            agent_name=trace.get("agent", "UnknownAgent"),
            task_description=trace.get("task_description") or "Executed step",
            input_data=str(trace.get("input_data", ""))[:500],
            output_data=str(trace.get("output_data", ""))[:1500],
            execution_time_ms=trace.get("latency_ms", 100),
            confidence_score=round(float(trace.get("confidence_score", 0.90)), 2)
        )
        db.add(log)

    # 7. Store the conversation itself (full question, answer and sources)
    is_first_message = db.query(ChatMessage.message_id).filter(ChatMessage.session_id == session_id).first() is None \
        and db.query(WorkflowRun.workflow_id).filter(WorkflowRun.session_id == session_id, WorkflowRun.workflow_id != workflow.workflow_id).first() is None
    user_row = ChatMessage(session_id=session_id, workflow_id=workflow.workflow_id, role="user", content=message)
    answer_row = ChatMessage(
        session_id=session_id, workflow_id=workflow.workflow_id, role="assistant",
        content=final_answer, sources=json.dumps(sources)
    )
    db.add(user_row)
    db.flush()
    db.add(answer_row)

    # 8. Name the chat from its first question (a title the user chose is never overwritten)
    title_changed = False
    if is_first_message and is_default_title(session.session_title):
        try:
            session.session_title = title_future.result(timeout=30) if title_future else generate_title(message)
        except Exception as e:
            logger.warning(f"Chat title generation failed, using a title from the question: {e}")
            session.session_title = clean_title(message) or DEFAULT_TITLE
        title_changed = True
    session.message_count = (session.message_count or 0) + 2

    db.commit()
    db.refresh(workflow)
    db.refresh(user_row)
    db.refresh(answer_row)
    
    # 9. Check for decisions to index in long-term memory
    long_term_memory.auto_detect_and_index(session_id, current_user.employee_id, message, final_answer)

    logs = list(workflow.agent_logs)
    return {
        "session_id": session_id,
        "session_title": session.session_title,
        "title_changed": title_changed,
        "workflow_id": workflow.workflow_id,
        "confidence_score": float(workflow.confidence_score) if workflow.confidence_score is not None else None,
        "user_message": _message_out(user_row),
        "answer": _message_out(answer_row, logs),
        # Kept for older clients
        "final_output": final_answer,
        "agent_logs": [{
            "agent_log_id": l.agent_log_id, "agent_name": l.agent_name, "task_description": l.task_description,
            "output_data": l.output_data, "execution_time_ms": l.execution_time_ms,
            "confidence_score": float(l.confidence_score) if l.confidence_score is not None else None,
        } for l in logs],
    }
